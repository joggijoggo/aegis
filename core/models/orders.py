"""Aegis Framework - Transactional Execution Specifications.

Defines immutable multi-asset trade requests, receipt confirmations, and historical
order update records.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from core.models import (
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

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

# LEGACY
@dataclass(frozen=True)
class OrderEvent:
    """Captures absolute transactional metadata generated during order updates.

    Attributes:
        broker_reference: The unique tracking identifier returned by the broker.
        symbol: The targeted financial instrument ticker.
        status: The exact state inside the execution lifecycle.
        side: The directional positioning constraint of the order.
        executed_price: The financial settlement price recorded by the broker.
        executed_size: The absolute amount of lots fulfilled by the execution.
        timestamp: The definitive execution time of the transaction.
    """
    broker_reference: str
    symbol: str
    status: OrderStatus
    side: OrderSide
    executed_price: float
    executed_size: float
    timestamp: datetime

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class OrderReceipt:
    """Broker execution response details.

    Attributes:
        broker_order_id: (Optional) Unique broker tracking identifier.
        client_order_id: Unique internal tracking identifier.
        status: Order execution lifecycle state.
        average_execution_price: (Optional) Volume-weighted execution price.
        reject_reason: (Optional) Broker rejection cause description.
    """
    broker_order_id: str | None
    client_order_id: str
    status: OrderStatus
    average_execution_price: Decimal | None = None
    reject_reason: str | None = None

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class OrderRequest:
    """Immutable data container representing a strategy trade intention.

    Attributes:
        symbol: The targeted financial asset identifier.
        stop_loss_ticks: The structural protection distance measured in ticks.
        risk_percentage: The maximum fraction of account equity risked on the trade.
        confidence_factor: A fractional scaling coefficient that can only reduce size.
    """
    symbol: str
    stop_loss_ticks: float
    risk_percentage: float
    confidence_factor: float

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
