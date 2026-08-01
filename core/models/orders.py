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

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
