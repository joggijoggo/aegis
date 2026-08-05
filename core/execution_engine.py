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
    UntrackedOrderException,
)
from core.models import (
    BrokerEvent,
    EventType,
    Order,
    OrderReceipt,
    OrderSide,
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
        """Processes an incoming order receipt.

        Args:
            receipt: The transaction lifecycle response from the broker venue book.

        Raises:
            UntrackedOrderException: When the receipt group identifier is unrecognized.
        """
        if receipt.group_id not in self._order_groups:
            raise UntrackedOrderException(
                f'Broker event mismatch: order group "{receipt.group_id}" is untracked.'
            )

        order_group = self._order_groups[receipt.group_id]
        order_group.notify_order_change(receipt)

        if order_group.is_terminal:
            del self._order_groups[receipt.group_id]

# -----------------------------------------------------------------------------

    def _handle_trade_notification(self, receipt: TradeReceipt) -> None:
        """Processes an incoming trade clearing receipt to update inventory states.

        Args:
            receipt: The incoming broker clearing receipt for the target execution group.

        Raises:
            UntrackedOrderException: When the receipt group identifier is unrecognized.
        """
        if receipt.group_id not in self._order_groups:
            raise UntrackedOrderException(
                f'Broker event mismatch: order group "{receipt.group_id}" is untracked.'
            )

        order_group = self._order_groups[receipt.group_id]
        order_group.notify_trade_change(receipt)

        if order_group.is_terminal:
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

        orders: list[Order] = [order]

        child_side = OrderSide.SELL if order.side == OrderSide.BUY else OrderSide.BUY
        child_base = replace(
            order,
            side=child_side,
            stop_loss_price=None,
            take_profit_price=None,
        )

        if order.stop_loss_price is not None:
            sl_order = replace(
                child_base,
                client_order_id=f'{order.client_order_id}-SL',
                order_type=OrderType.STOP,
                price=order.stop_loss_price,
            )
            orders.append(sl_order)

        if order.take_profit_price is not None:
            tp_order = replace(
                child_base,
                client_order_id=f'{order.client_order_id}-TP',
                order_type=OrderType.LIMIT,
                price=order.take_profit_price,
            )
            orders.append(tp_order)

        self._order_groups[order.client_order_id] = OrderGroup(
            parent_id=order.client_order_id,
            orders=orders,
        )

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
