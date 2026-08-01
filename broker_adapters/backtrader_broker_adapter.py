"""Aegis Framework - Backtrader Broker Adapter.

Provides the infrastructure adapter to interface with the Backtrader broker component.
"""

from decimal import Decimal
from typing import Any

import backtrader as bt

from broker_adapters.backtrader_bridge import BacktraderBridge
from broker_adapters.base_broker_adapter import BaseBrokerAdapter
from core.exceptions import AegisError
from core.models import (
    AccountSnapshot,
    BrokerEvent,
    EventType,
    Order,
    OrderSide,
    OrderType,
    TimeInForce,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class AssetSymbolNotFoundError(AegisError):
    """The requested financial asset symbol is not loaded in the Cerebro environment."""

# -----------------------------------------------------------------------------

class InvalidOrderQuantityError(AegisError):
    """Execution order volume is zero or negative at the adapter boundary."""

# -----------------------------------------------------------------------------

class InvalidProtectionPriceError(AegisError):
    """The provided stop loss or take profit price trigger is negative or zero."""

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class BacktraderBrokerAdapter(BaseBrokerAdapter):
    """Broker adapter implementing the core transactional interface for Backtrader.

    Manages order routing and account synchronization through the central bridge.
    """

# -----------------------------------------------------------------------------

    def __init__(self, bridge: BacktraderBridge) -> None:
        """Initializes the broker adapter and hooks the synchronization reference.

        Args:
            bridge: The central synchronization bridge.
        """
        self._bridge = bridge
        self._broker_queue = bridge.get_broker_queue()

# -----------------------------------------------------------------------------

    def _resolve_data_feed(self, symbol: str) -> bt.feed.DataBase:
        """Finds and returns the explicit Backtrader data feed instance for a given symbol.

        Args:
            symbol: Target financial asset identifier.

        Returns:
            The matched infrastructure data feed instance.

        Raises:
            AssetSymbolNotFoundError: The requested financial symbol is not loaded in Cerebro.
        """
        for data in self._bridge.strategy.datas:
            if data._name == symbol:
                return data

        raise AssetSymbolNotFoundError(
            f"Requested asset symbol '{symbol}' is not available "
            "within the active Cerebro infrastructure environment."
        )

# -----------------------------------------------------------------------------

    def _route_transaction(self, order: Order, data: bt.feed.DataBase, size: float) -> None:
        """Routes explicit execution streams with dynamic parent-child link tracking.

        Args:
            order: The generic domain order specification.
            data: The target infrastructure data feed instance.
            size: The validated float volume.

        Raises:
            BridgeUnboundError: The strategy instance is not bound.
        """
        strategy = self._bridge.strategy
        sl_price = float(order.stop_loss_price) if order.stop_loss_price is not None else None
        tp_price = float(order.take_profit_price) if order.take_profit_price is not None else None

        # Hard enforcement: protect the platform against executing unprotected trades silently
        if sl_price is not None and sl_price <= 0.0:
            raise InvalidProtectionPriceError(
                f"Invalid Stop Loss price: {sl_price}. Protection bounds must be strictly positive."
            )
        if tp_price is not None and tp_price <= 0.0:
            raise InvalidProtectionPriceError(
                f"Invalid Take Profit price: {tp_price}. Protection bounds must be strictly positive."
            )

        if order.side == OrderSide.BUY:
            entry_op = strategy.buy
            child_op = strategy.sell
        else:
            entry_op = strategy.sell
            child_op = strategy.buy

        has_sl = sl_price is not None
        has_tp = tp_price is not None
        has_children = has_sl or has_tp

        parent = entry_op(
            data=data,
            size=size,
            exectype=bt.Order.Market,
            valid=None,
            transmit=not has_children,
            client_order_id=order.client_order_id,
        )

        if has_sl:
            transmit_sl = not has_tp
            child_op(
                data=data,
                size=size,
                exectype=bt.Order.Stop,
                price=sl_price,
                valid=None,
                parent=parent,
                transmit=transmit_sl,
                client_order_id=f"{order.client_order_id}-SL",
            )

        if has_tp:
            child_op(
                data=data,
                size=size,
                exectype=bt.Order.Limit,
                price=tp_price,
                valid=None,
                parent=parent,
                transmit=True,
                client_order_id=f"{order.client_order_id}-TP",
            )

# -----------------------------------------------------------------------------

    def _translate_to_broker_event(self, event_type: EventType, raw_data: Any) -> BrokerEvent:
        """Translates raw infrastructure notifications into core domain events.

        Args:
            event_type: The core classification used to route the update.
            raw_data: The raw infrastructure notification instance.

        Returns:
            The translated broker event record.
        """
        # Microstructural translation wrapper placeholder
        return BrokerEvent(
            event_type=event_type,
            payload=raw_data,
        )

# -----------------------------------------------------------------------------

    def get_account_snapshot(self) -> AccountSnapshot:
        """Returns the current financial state of the account.

        Returns:
            The account metrics snapshot.
        """
        strategy = self._bridge.strategy

        raw_balance = float(strategy.broker.get_cash())
        raw_equity = float(strategy.broker.get_value())

        raw_available_margin = raw_equity # TODO: subtract locked margin for open positions

        return AccountSnapshot(
            currency='USD',  # TODO: extract dynamically from environment
            balance=Decimal(str(raw_balance)),
            equity=Decimal(str(raw_equity)),
            available_margin=Decimal(str(raw_available_margin)),
        )

# -----------------------------------------------------------------------------

    def has_pending_events(self) -> bool:
        """Indicates whether unread broker events are available."""
        return not self._broker_queue.empty()

# -----------------------------------------------------------------------------

    def poll_event(self) -> BrokerEvent:
        """Returns the next pending broker event.

        Returns:
            The retrieved broker event.
        """
        event_type, raw_data = self._broker_queue.get()
        return self._translate_to_broker_event(event_type, raw_data)

# -----------------------------------------------------------------------------

    def submit_order(self, order: Order) -> None:
        """Submits an execution request to the Backtrader platform.

        Args:
            order: The execution order request containing trade specifications.

        Raises:
            AssetSymbolNotFoundError: The requested financial symbol is not loaded in Cerebro.
            BridgeUnboundError: The strategy instance is not bound.
            InvalidOrderQuantityError: The execution volume is non-positive.
        """
        raw_quantity = float(order.quantity)
        if raw_quantity <= 0.0:
            raise InvalidOrderQuantityError(
                f"Invalid order quantity processed by the adapter: {raw_quantity}. "
                "Execution volume must be strictly positive."
            )

        if order.order_type != OrderType.MARKET:
            raise NotImplementedError('Only MARKET orders are supported.')

        if order.time_in_force != TimeInForce.GTC:
            raise NotImplementedError(
                f"TimeInForce policy '{order.time_in_force}' is not supported due "
                "to microstructure timezone alignment constraints. Use GTC."
            )

        target_data = self._resolve_data_feed(order.symbol)
        self._route_transaction(order, target_data, raw_quantity)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
