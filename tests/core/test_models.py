"""Aegis Framework - Core Models Conformity Tests.

Verifies structural integrity, immutability behaviors, and strict Decimal type
adherence across all domain data transfer objects.
"""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from core.models import (
    AccountSnapshot,
    Order,
    OrderReceipt,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_account_snapshot_immutability() -> None:
    """Verifies AccountSnapshot raises FrozenInstanceError upon modification."""
    snapshot = AccountSnapshot(
        balance=Decimal("10000.00"),
        equity=Decimal("10500.00"),
        available_margin=Decimal("8000.00"),
    )

    with pytest.raises(FrozenInstanceError):
        snapshot.balance = Decimal("11000.00")  # type: ignore

# -----------------------------------------------------------------------------

def test_account_snapshot_types() -> None:
    """Verifies AccountSnapshot strictly enforces Decimal instances."""
    snapshot = AccountSnapshot(
        balance=Decimal("10000.00"),
        equity=Decimal("10500.00"),
        available_margin=Decimal("8000.00"),
    )

    assert isinstance(snapshot.balance, Decimal)
    assert isinstance(snapshot.equity, Decimal)
    assert isinstance(snapshot.available_margin, Decimal)

# -----------------------------------------------------------------------------

def test_order_default_parameters() -> None:
    """Verifies Order optional fields resolve to None by default."""
    order = Order(
        client_order_id="ORD-123",
        timestamp=1719734400000,
        symbol="EURUSD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.IOC,
        quantity=Decimal("100000"),
    )

    assert order.price is None
    assert order.stop_loss_price is None
    assert order.take_profit_price is None

# -----------------------------------------------------------------------------

def test_order_immutability() -> None:
    """Verifies Order raises FrozenInstanceError upon modification."""
    order = Order(
        client_order_id="ORD-123",
        timestamp=1719734400000,
        symbol="EURUSD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.IOC,
        quantity=Decimal("100000"),
    )

    with pytest.raises(FrozenInstanceError):
        order.quantity = Decimal("200000")  # type: ignore

# -----------------------------------------------------------------------------

def test_order_receipt_default_parameters() -> None:
    """Verifies OrderReceipt optional fields resolve to None by default."""
    receipt = OrderReceipt(
        broker_order_id=None,
        client_order_id="ORD-123",
        status=OrderStatus.REJECTED,
    )

    assert receipt.average_execution_price is None
    assert receipt.reject_reason is None

# -----------------------------------------------------------------------------

def test_order_receipt_immutability() -> None:
    """Verifies OrderReceipt raises FrozenInstanceError upon modification."""
    receipt = OrderReceipt(
        broker_order_id="BRK-999",
        client_order_id="ORD-123",
        status=OrderStatus.PENDING,
    )

    with pytest.raises(FrozenInstanceError):
        receipt.status = OrderStatus.FILLED  # type: ignore

# -----------------------------------------------------------------------------

def test_order_receipt_types_on_filled() -> None:
    """Verifies OrderReceipt fields for a successful market execution."""
    receipt = OrderReceipt(
        broker_order_id="BRK-999",
        client_order_id="ORD-123",
        status=OrderStatus.FILLED,
        average_execution_price=Decimal("1.0850"),
        reject_reason=None,
    )

    assert isinstance(receipt.broker_order_id, str)
    assert isinstance(receipt.client_order_id, str)
    assert isinstance(receipt.status, OrderStatus)
    assert isinstance(receipt.average_execution_price, Decimal)
    assert receipt.reject_reason is None

# -----------------------------------------------------------------------------

def test_order_receipt_types_on_rejected() -> None:
    """Verifies OrderReceipt fields for an instant broker rejection."""
    receipt = OrderReceipt(
        broker_order_id=None,
        client_order_id="ORD-123",
        status=OrderStatus.REJECTED,
        average_execution_price=None,
        reject_reason="Insufficient Margin",
    )

    assert receipt.broker_order_id is None
    assert isinstance(receipt.client_order_id, str)
    assert isinstance(receipt.status, OrderStatus)
    assert receipt.average_execution_price is None
    assert isinstance(receipt.reject_reason, str)

# -----------------------------------------------------------------------------

def test_order_types_with_limit_bounds() -> None:
    """Verifies Order fields and protection prices use strict domain types."""
    order = Order(
        client_order_id="ORD-123",
        timestamp=1719734400000,
        symbol="EURUSD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.DAY,
        quantity=Decimal("100000"),
        price=Decimal("1.0850"),
        stop_loss_price=Decimal("1.0800"),
        take_profit_price=Decimal("1.0950"),
    )

    assert isinstance(order.client_order_id, str)
    assert isinstance(order.timestamp, int)
    assert isinstance(order.symbol, str)
    assert isinstance(order.side, OrderSide)
    assert isinstance(order.order_type, OrderType)
    assert isinstance(order.time_in_force, TimeInForce)
    assert isinstance(order.quantity, Decimal)
    assert isinstance(order.price, Decimal)
    assert isinstance(order.stop_loss_price, Decimal)
    assert isinstance(order.take_profit_price, Decimal)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
