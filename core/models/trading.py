"""Aegis Framework - Trading Operational Models.

Handles and tracks transactional execution lifecycle records.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from core.models import (
    EventType,
    OrderGroupState,
    OrderSide,
    OrderState,
    OrderType,
    TimeInForce,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

@dataclass(frozen=True)
class ExposureIntent:
    """Immutable data record capturing passive execution desires.

    Attributes:
        alpha_direction: The continuous trend conviction scalar bounded strictly
            between -1.0 and 1.0. A value of 0.0 explicitly enforces a flat position
            and triggers a portfolio liquidation. A value of None indicates no active
            opinion, instructing the engine to maintain ongoing exposures.
        stop_loss_ticks: The protective exit distance measured in ticks.
        take_profit_ticks: The target take-profit distance measured in ticks.
    """
    alpha_direction: float | None = None
    stop_loss_ticks: float = 0.0
    take_profit_ticks: float = 0.0

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class Order:
    """Broker execution request.

    Attributes:
        client_order_id: Unique internal tracking identifier.
        timestamp: Creation time.
        symbol: Target financial asset.
        side: Execution direction (BUY or SELL).
        order_type: Order routing type (e.g., MARKET or LIMIT).
        time_in_force: Execution expiration policy (e.g., DAY or IOC).
        quantity: Order volume expressed in absolute asset units.
        price: Target execution price or None for MARKET orders.
        stop_loss_price: (Optional) Absolute exit price for loss protection.
        take_profit_price: (Optional) Absolute exit price for profit capture.
    """
    client_order_id: str
    timestamp: datetime
    symbol: str
    side: OrderSide
    order_type: OrderType
    time_in_force: TimeInForce
    quantity: Decimal
    price: Decimal | None = None
    stop_loss_price: Decimal | None = None
    take_profit_price: Decimal | None = None

# -----------------------------------------------------------------------------

@dataclass
class OrderGroup:
    """Tracking container maintaining volatile execution context records.

    Attributes:
        clearing_closed: Boolean flag confirming asset ledger inventory is flat.
        group_id: Unique internal tracking identifier for the parent group.
        order_states: Live lifecycle tracking state mapping for each order ID.
        orders: Immutable technical specification records for each order ID.
        state: Aggregated execution lifecycle state of the entire bracket.
    """
    clearing_closed: bool
    group_id: str
    order_states: dict[str, OrderState]
    orders: dict[str, Order]
    state: OrderGroupState

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class OrderReceipt:
    """Broker execution response details.

    Attributes:
        average_execution_price: Volume-weighted execution price or None.
        broker_order_id: Unique broker tracking identifier or None.
        client_order_id: Unique internal tracking identifier for the specific order.
        executed_quantity: Explicit volume executed during the current infrastructure tick.
        group_id: Unique internal tracking identifier for the parent execution group.
        reject_reason: Broker rejection cause description or None.
        state: Order execution lifecycle state.
    """
    average_execution_price: Decimal | None
    broker_order_id: str | None
    client_order_id: str
    executed_quantity: Decimal
    group_id: str
    reject_reason: str | None
    state: OrderState

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class TradeReceipt:
    """Broker transaction clearing details mapping financial performance.

    Attributes:
        broker_trade_id: Unique broker tracking identifier.
        commission: Transaction friction fees charged by the broker.
        group_id: Unique internal tracking identifier for the parent group.
        is_open: Boolean flag indicating if the position remains active.
        realized_pnl: Financial net result extracted from the closed exposure.
        symbol: Financial asset ticker code identifier.
    """
    broker_trade_id: str
    commission: Decimal
    group_id: str
    is_open: bool
    realized_pnl: Decimal
    symbol: str

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class BrokerEvent:
    """Immutable record capturing broker notifications.

    Attributes:
        event_type: Infrastructure event classification category.
        payload: Strongly-typed domain data record payload.
    """
    event_type: EventType
    payload: OrderReceipt | TradeReceipt

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class RegimeConfidenceVector:
    """Stores statistical confidence metrics computed by math classifiers.

    Attributes:
        mean_reversion: Probability weight assigned to cyclic behaviors.
        trending: Probability weight assigned to directional patterns.
        noise: Probability weight assigned to non-exploitable random dynamics.
    """
    mean_reversion: float
    trending: float
    noise: float

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
