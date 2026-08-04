"""Aegis Framework - Core Models Conformity Tests.

Verifies structural integrity, immutability behaviors, and strict Decimal type
adherence across all domain data transfer objects.
"""

from dataclasses import FrozenInstanceError
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from core.models import (
    AccountSnapshot,
    BrokerEvent,
    EventType,
    Order,
    OrderReceipt,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionSide,
    TimeInForce,
)
from tests.testutils import (
    create_position_factory,
    create_position_ledger_snapshot_factory,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_account_snapshot_immutability() -> None:
    """Verifies AccountSnapshot raises FrozenInstanceError upon modification."""
    snapshot = AccountSnapshot(
        currency='EURUSD',
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
        currency='EURUSD',
        balance=Decimal("10000.00"),
        equity=Decimal("10500.00"),
        available_margin=Decimal("8000.00"),
    )

    assert isinstance(snapshot.balance, Decimal)
    assert isinstance(snapshot.equity, Decimal)
    assert isinstance(snapshot.available_margin, Decimal)

# -----------------------------------------------------------------------------

def test_broker_event_immutability() -> None:
    """Verifies that the BrokerEvent dataclass enforces strict immutability."""
    event = BrokerEvent(event_type=EventType.MARKET_TICK, payload='test_payload')

    assert event.event_type == EventType.MARKET_TICK
    assert event.payload == 'test_payload'

    with pytest.raises(FrozenInstanceError):
        event.payload = 'mutated_payload'  # type: ignore

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
        timestamp=datetime(2026, 7, 30, 12, 0, tzinfo=ZoneInfo("UTC")),
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
    assert isinstance(order.timestamp, datetime)
    assert isinstance(order.symbol, str)
    assert isinstance(order.side, OrderSide)
    assert isinstance(order.order_type, OrderType)
    assert isinstance(order.time_in_force, TimeInForce)
    assert isinstance(order.quantity, Decimal)
    assert isinstance(order.price, Decimal)
    assert isinstance(order.stop_loss_price, Decimal)
    assert isinstance(order.take_profit_price, Decimal)

# -----------------------------------------------------------------------------

def test_position_ledger_snapshot__filters_records_by_symbol() -> None:
    """Verifies that get_positions_by_symbol successfully isolates target contracts."""
    # 1. Forge targeted positions using the factory
    pos_eurusd_1 = create_position_factory(symbol='EURUSD', ticket_id='TKT-1', side=PositionSide.LONG)
    pos_eurusd_2 = create_position_factory(symbol='EURUSD', ticket_id='TKT-2', side=PositionSide.SHORT)
    pos_gbpusd = create_position_factory(symbol='GBPUSD', ticket_id='TKT-3', side=PositionSide.LONG)

    # 2. Build the immutable ledger record dictionary
    records = {
        'TKT-1': pos_eurusd_1,
        'TKT-2': pos_eurusd_2,
        'TKT-3': pos_gbpusd,
    }
    ledger = create_position_ledger_snapshot_factory(records=records)

    # 3. Execute the domain query utility
    eurusd_positions = ledger.get_positions_by_symbol('EURUSD')
    gbpusd_positions = ledger.get_positions_by_symbol('GBPUSD')
    untraded_positions = ledger.get_positions_by_symbol('USDJPY')

    # 4. Strict assertions backing the non-destructive signal filtering
    assert len(eurusd_positions) == 2
    assert pos_eurusd_1 in eurusd_positions
    assert pos_eurusd_2 in eurusd_positions

    assert len(gbpusd_positions) == 1
    assert pos_gbpusd in gbpusd_positions

    assert len(untraded_positions) == 0

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
