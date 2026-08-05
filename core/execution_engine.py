"""Aegis Framework - Execution Engine.

Orchestrates execution cycles by consuming market feeds, driving strategy bot
evaluations, and routing risk-sized orders to the broker gateway.
"""

from dataclasses import replace
from decimal import Decimal

from bots.base_bot import BaseBot
from broker_adapters.base_broker_adapter import BaseBrokerAdapter
from core.caching import HistoricalBuffer
from core.contract_registry import ContractRegistry
from core.exceptions import (
    DuplicateOrderGroupError,
    UnsupportedBrokerEventError,
)
from core.models import (
    BrokerEvent,
    EventType,
    Order,
    OrderGroupState,
    OrderReceipt,
    OrderSide,
    OrderState,
    OrderType,
    TradeReceipt,
)
from core.order_group import OrderGroup
from core.position_sizer import PositionSizer
from market_feeds.base_market_feed import BaseMarketFeed

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class AegisExecutionEngine:
    """Core orchestrator synchronizing market data ingestion and trading logic."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        bot: BaseBot,
        broker_adapter: BaseBrokerAdapter,
        contract_registry: ContractRegistry,
        position_sizer: PositionSizer,
    ):
        """Initializes the execution engine.

        Args:
            bot: Trading strategy instance executing evaluation logic.
            broker_adapter: Infrastructure bridge mapping orders to the venue.
            contract_registry: Repository storing contract specifications.
            position_sizer: Component generating risk-sized execution orders.
        """
        self._bot = bot
        self._broker_adapter = broker_adapter
        self._order_groups: dict[str, OrderGroup] = {}
        self._contract_registry = contract_registry
        self._position_sizer = position_sizer
        self._risk_percent = Decimal('0.01')
        self._buffers: dict[str, HistoricalBuffer] = {}

# -----------------------------------------------------------------------------

    def _handle_order_notification(self, receipt: OrderReceipt) -> None:
        """Processes an incoming order receipt using an explicit transition matrix.

        Args:
            receipt: The transaction lifecycle response containing the execution state.

        Raises:
            NotImplementedError: If partially filled or expired states are encountered.
            AssertionError: If the internal transition matrix structure is incomplete.
        """
        # Enforce strict preventive circuit breaker for unhandled edge states
        if receipt.state in {OrderState.PARTIALLY_FILLED, OrderState.EXPIRED}:
            raise NotImplementedError(
                f'Order state {receipt.state} is not supported in the current framework.'
            )

        # FIXME: Replace this passive guard with an untracked order exception layout
        if receipt.group_id not in self._order_groups:
            return

        order_group = self._order_groups[receipt.group_id]

        # FIXME: Raise an untracked order exception if the specific ID is missing
        if receipt.client_order_id not in order_group.orders:
            return

        # Update the precise atomic state tracking for this specific order
        order_group.order_states[receipt.client_order_id] = receipt.state

        # Define the absolute Parent Transition Matrix: Actuel x Ordre -> Cible
        # Layout: {CurrentGroupState: {IncomingOrderState: TargetGroupState}}
        parent_matrix = {
            OrderGroupState.PENDING: {
                # Nominal state where the parent entrance order sits in the venue book
                OrderState.PENDING: OrderGroupState.PENDING,
                # Nominal entrance execution opening the trade exposure
                OrderState.FILLED: OrderGroupState.ACTIVE,
                # Parent order cancelled before matching; aborting the cycle cleanly
                OrderState.CANCELED: OrderGroupState.REJECTING,
                # Parent order rejected due to margin or venue rules; aborting cycle
                OrderState.REJECTED: OrderGroupState.REJECTING,
            },
            OrderGroupState.ACTIVE: {
                # Severe rupture: parent order goes back to pending while group is active
                OrderState.PENDING: OrderGroupState.CORRUPTED,
                # Severe rupture: duplicate entry execution received for an active trade
                OrderState.FILLED: OrderGroupState.CORRUPTED,
                # Severe rupture: parent order cancelled post matching; data mismatch
                OrderState.CANCELED: OrderGroupState.CORRUPTED,
                # Severe rupture: parent order rejected post matching; data mismatch
                OrderState.REJECTED: OrderGroupState.CORRUPTED,
            },
            OrderGroupState.CLOSING: {
                # Severe rupture: parent order goes back to pending while trade is closing
                OrderState.PENDING: OrderGroupState.CORRUPTED,
                # Severe rupture: duplicate entry fill received during unwinding phase
                OrderState.FILLED: OrderGroupState.CORRUPTED,
                # Severe rupture: parent order cancelled during unwinding phase
                OrderState.CANCELED: OrderGroupState.CORRUPTED,
                # Severe rupture: parent order rejected during unwinding phase
                OrderState.REJECTED: OrderGroupState.CORRUPTED,
            },
            OrderGroupState.REJECTING: {
                # Severe rupture: failed parent signals an impossible pending state late
                OrderState.PENDING: OrderGroupState.CORRUPTED,
                # Severe rupture: parent fills late while children are being purged
                OrderState.FILLED: OrderGroupState.CORRUPTED,
                # Severe rupture: redundant cancel received for an already failing parent
                OrderState.CANCELED: OrderGroupState.CORRUPTED,
                # Severe rupture: redundant reject received for an already failing parent
                OrderState.REJECTED: OrderGroupState.CORRUPTED,
            },
            OrderGroupState.CANCELED: {
                # Deadlock state: cancelled groups reject late infrastructure packets
                OrderState.PENDING: OrderGroupState.CORRUPTED,
                OrderState.FILLED: OrderGroupState.CORRUPTED,
                OrderState.CANCELED: OrderGroupState.CORRUPTED,
                OrderState.REJECTED: OrderGroupState.CORRUPTED,
            },
            OrderGroupState.COMPLETED: {
                # Deadlock state: completed groups reject late infrastructure packets
                OrderState.PENDING: OrderGroupState.CORRUPTED,
                OrderState.FILLED: OrderGroupState.CORRUPTED,
                OrderState.CANCELED: OrderGroupState.CORRUPTED,
                OrderState.REJECTED: OrderGroupState.CORRUPTED,
            },
            OrderGroupState.REJECTED: {
                # Deadlock state: rejected groups reject late infrastructure packets
                OrderState.PENDING: OrderGroupState.CORRUPTED,
                OrderState.FILLED: OrderGroupState.CORRUPTED,
                OrderState.CANCELED: OrderGroupState.CORRUPTED,
                OrderState.REJECTED: OrderGroupState.CORRUPTED,
            },
            OrderGroupState.CORRUPTED: {
                # Deadlock state: once corrupted, the group blocks all modifications
                OrderState.PENDING: OrderGroupState.CORRUPTED,
                OrderState.FILLED: OrderGroupState.CORRUPTED,
                OrderState.CANCELED: OrderGroupState.CORRUPTED,
                OrderState.REJECTED: OrderGroupState.CORRUPTED,
            },
        }

        # Define the absolute Child Transition Matrix: Actuel x Ordre -> Cible
        child_matrix = {
            OrderGroupState.PENDING: {
                # Nominal state where protection orders sit waiting in the book
                OrderState.PENDING: OrderGroupState.PENDING,
                # Rupture: protection fills before parent entry executed; upside down
                OrderState.FILLED: OrderGroupState.CORRUPTED,
                # Severe rupture: protection cancelled before parent entry is executed
                OrderState.CANCELED: OrderGroupState.CORRUPTED,
                # Severe rupture: protection rejected before parent entry is executed
                OrderState.REJECTED: OrderGroupState.CORRUPTED,
            },
            OrderGroupState.ACTIVE: {
                # Nominal invariant where active protections monitor exposure
                OrderState.PENDING: OrderGroupState.ACTIVE,
                # Nominal protection hit; position unwinding initiated under closing
                OrderState.FILLED: OrderGroupState.CLOSING,
                # Severe rupture: live protection cancelled; exposure left naked
                OrderState.CANCELED: OrderGroupState.CORRUPTED,
                # Severe rupture: live protection rejected by broker; exposure naked
                OrderState.REJECTED: OrderGroupState.CORRUPTED,
            },
            OrderGroupState.CLOSING: {
                # Severe rupture: brother protection remains pending during closing
                OrderState.PENDING: OrderGroupState.CORRUPTED,
                # Severe rupture: brother protection fills during closing; double execution
                OrderState.FILLED: OrderGroupState.CORRUPTED,
                # Nominal sequence: brother protection cancelled successfully post unwind
                OrderState.CANCELED: OrderGroupState.CLOSING,
                # Severe rupture: broker rejects the protection cancellation during closing
                OrderState.REJECTED: OrderGroupState.CORRUPTED,
            },
            OrderGroupState.REJECTING: {
                # Severe rupture: child signals a pending state after parent failure
                OrderState.PENDING: OrderGroupState.CORRUPTED,
                # Severe rupture: child protection fills while parent entry failed
                OrderState.FILLED: OrderGroupState.CORRUPTED,
                # Nominal sequence: child cancelled following the parent failure
                OrderState.CANCELED: OrderGroupState.REJECTING,
                # Severe rupture: broker rejects the child cancellation post parent failure
                OrderState.REJECTED: OrderGroupState.CORRUPTED,
            },
            OrderGroupState.CANCELED: {
                # Deadlock state: cancelled groups reject late infrastructure packets
                OrderState.PENDING: OrderGroupState.CORRUPTED,
                OrderState.FILLED: OrderGroupState.CORRUPTED,
                OrderState.CANCELED: OrderGroupState.CORRUPTED,
                OrderState.REJECTED: OrderGroupState.CORRUPTED,
            },
            OrderGroupState.COMPLETED: {
                # Deadlock state: completed groups reject late infrastructure packets
                OrderState.PENDING: OrderGroupState.CORRUPTED,
                OrderState.FILLED: OrderGroupState.CORRUPTED,
                OrderState.CANCELED: OrderGroupState.CORRUPTED,
                OrderState.REJECTED: OrderGroupState.CORRUPTED,
            },
            OrderGroupState.REJECTED: {
                # Deadlock state: rejected groups reject late infrastructure packets
                OrderState.PENDING: OrderGroupState.CORRUPTED,
                OrderState.FILLED: OrderGroupState.CORRUPTED,
                OrderState.CANCELED: OrderGroupState.CORRUPTED,
                OrderState.REJECTED: OrderGroupState.CORRUPTED,
            },
            OrderGroupState.CORRUPTED: {
                # Deadlock state: once corrupted, the group blocks all modifications
                OrderState.PENDING: OrderGroupState.CORRUPTED,
                OrderState.FILLED: OrderGroupState.CORRUPTED,
                OrderState.CANCELED: OrderGroupState.CORRUPTED,
                OrderState.REJECTED: OrderGroupState.CORRUPTED,
            },
        }

        # Defensive runtime safeguard: validate full matrix coverage against ourselves
        monitored_order_states = {
            state for state in OrderState
            if state not in {OrderState.PARTIALLY_FILLED, OrderState.EXPIRED}
        }
        for matrix_layout in (parent_matrix, child_matrix):
            for group_state in OrderGroupState:
                assert group_state in matrix_layout, (
                    f'Defensive Error: {group_state} missing from matrix definitions.'
                )
                for order_state in monitored_order_states:
                    assert order_state in matrix_layout[group_state], (
                        f'Defensive Error: Mapping for ({group_state}, {order_state}) '
                        f'is missing from transition layout.'
                    )

        # Interrogate the correct matrix mapping based on the order role sémantique
        is_parent = receipt.client_order_id == order_group.group_id
        target_matrix = parent_matrix if is_parent else child_matrix

        # Execute the deterministic state transition mutation step
        order_group.state = target_matrix[order_group.state][receipt.state]

        # Evaluate automated RAM eviction triggers for complete opening failures
        if order_group.state == OrderGroupState.REJECTING:
            all_children_terminal = True
            for ord_id, order_state in order_group.order_states.items():
                if ord_id != order_group.group_id and not order_state.is_terminal:
                    all_children_terminal = False
                    break
            if all_children_terminal:
                order_group.state = OrderGroupState.REJECTED
                del self._order_groups[receipt.group_id]

        # Evaluate automated RAM eviction triggers for asynchronous closing races
        if order_group.state == OrderGroupState.CLOSING and order_group.clearing_closed:
            all_orders_terminal = True
            for order_state in order_group.order_states.values():
                if not order_state.is_terminal:
                    all_orders_terminal = False
                    break
            if all_orders_terminal:
                order_group.state = OrderGroupState.COMPLETED
                del self._order_groups[receipt.group_id]

# -----------------------------------------------------------------------------

    def _handle_trade_notification(self, receipt: TradeReceipt) -> None:
        """Processes an incoming trade clearing receipt and reconciles inventory states.

        Args:
            receipt: The transaction clearing response mapping portfolio performance.
        """
        # FIXME: Replace this passive guard with an untracked trade exception layout
        if receipt.group_id not in self._order_groups:
            return

        order_group = self._order_groups[receipt.group_id]

        # Sync the volatile accounting ledger state based on the infrastructure signal
        if receipt.is_open:
            order_group.clearing_closed = False
        else:
            order_group.clearing_closed = True

            # Scan the atomic order states to determine if an unwind was authorized
            any_child_filled = False
            for ord_id, order_state in order_group.order_states.items():
                if ord_id != order_group.group_id and order_state == OrderState.FILLED:
                    any_child_filled = True
                    break

            # Handle asymmetric scenarios based on atomic execution tracking evidence
            if not any_child_filled and order_group.state == OrderGroupState.ACTIVE:
                # Severe rupture: position closed externally with no child order matching
                order_group.state = OrderGroupState.CORRUPTED

            elif order_group.state == OrderGroupState.CLOSING or any_child_filled:
                # Nominal sequence: evaluate memory eviction if all orders are terminal
                all_orders_terminal = True
                for order_state in order_group.order_states.values():
                    if not order_state.is_terminal:
                        all_orders_terminal = False
                        break
                if all_orders_terminal:
                    order_group.state = OrderGroupState.COMPLETED
                    del self._order_groups[receipt.group_id]

# -----------------------------------------------------------------------------

    def _process_broker_event(self, broker_event: BrokerEvent) -> None:
        """Processes an unread asynchronous broker event notification by routing payloads.

        Args:
            broker_event: The notification wrapper containing routing flags and transactional data.

        Raises:
            UnsupportedBrokerEventError: If the event classification category cannot be handled.
        """
        if broker_event.event_type == EventType.ORDER_NOTIFICATION:
            self._handle_order_notification(broker_event.payload)
        elif broker_event.event_type == EventType.TRADE_NOTIFICATION:
            self._handle_trade_notification(broker_event.payload)
        else:
            raise UnsupportedBrokerEventError(
                f"Received unhandled or corrupted event type: {broker_event.event_type}"
            )

# -----------------------------------------------------------------------------

    def _register_order_group(self, order: Order) -> None:
        """Instantiates and registers a new tracking group before broker submission.

        Args:
            order: The parent execution order request containing bracket parameters.

        Raises:
            DuplicateOrderGroupError: If the group identifier already exists in memory.
        """
        if order.client_order_id in self._order_groups:
            raise DuplicateOrderGroupError(
                f'Collision detected: group {order.client_order_id} already exists'
            )

        # Populate the structural tracking dictionary starting with the parent order
        group_orders: dict[str, Order] = {order.client_order_id: order}

        # Derive a clean, reusable common baseline for all child protective brackets
        child_side = OrderSide.SELL if order.side == OrderSide.BUY else OrderSide.BUY
        child_base = replace(
            order,
            side=child_side,
            stop_loss_price=None,
            take_profit_price=None,
        )

        # Apply specific overrides for the Stop-Loss protection frame if present
        if order.stop_loss_price is not None:
            sl_id = f'{order.client_order_id}-SL'
            group_orders[sl_id] = replace(
                child_base,
                client_order_id=sl_id,
                order_type=OrderType.STOP,
                price=order.stop_loss_price,
            )

        # Apply specific overrides for the Take-Profit protection frame if present
        if order.take_profit_price is not None:
            tp_id = f'{order.client_order_id}-TP'
            group_orders[tp_id] = replace(
                child_base,
                client_order_id=tp_id,
                order_type=OrderType.LIMIT,
                price=order.take_profit_price,
            )

        # Initialize the atomic state mapping with all orders in PENDING state
        order_states = {ord_id: OrderState.PENDING for ord_id in group_orders}

        # Open and commit the unified tracking ledger entry in volatile memory
        order_group = OrderGroup(
            clearing_closed=False,
            group_id=order.client_order_id,
            order_states=order_states,
            orders=group_orders,
            state=OrderGroupState.PENDING,
        )

        self._order_groups[order.client_order_id] = order_group

# -----------------------------------------------------------------------------

    def run_execution_cycle(
        self,
        symbol: str,
        market_feed: BaseMarketFeed,
    ) -> None:
        """Runs a complete execution cycle over the provided market feed.

        Args:
            symbol: Target financial instrument identifier.
            market_feed: Input market data source.
        """
        if symbol not in self._buffers:
            capacity = self._bot.warm_up_period
            self._buffers[symbol] = HistoricalBuffer(max_size=capacity)

        buffer = self._buffers[symbol]

        try:
            while True:
                # print(f'\n{"-"*50} NEW CYCLE {"-"*50}')

                # Flush and process asynchronous broker updates before market evaluation
                while self._broker_adapter.has_pending_events():
                    broker_event = self._broker_adapter.poll_event()
                    # print(broker_event)
                    self._process_broker_event(broker_event)

                market_context = next(market_feed)
                buffer.append(value=market_context.prices.mid_price)

                broker_snapshot = self._broker_adapter.get_broker_snapshot()

                exposure_intent = self._bot.evaluate(
                    market_context=market_context,
                    historical_values=buffer.to_list(),
                )

                if exposure_intent.alpha_direction is None:
                    continue

                if exposure_intent.alpha_direction == 0.0:
                    raise NotImplementedError('Close position')

                contract_specification = (
                    self._contract_registry.get_specification(symbol)
                )

                order = self._position_sizer.create_order(
                    exposure_intent=exposure_intent,
                    risk_percent=self._risk_percent,
                    contract_specification=contract_specification,
                    account_snapshot=broker_snapshot.account,
                    market_context=market_context,
                )

                # Record the tracking container prior to infrastructure transmission.
                self._register_order_group(order)

                self._broker_adapter.submit_order(order)
        except StopIteration:
            pass

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
