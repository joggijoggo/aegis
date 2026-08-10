"""Aegis Framework - Core Models Conformity Tests.

Verifies structural integrity, immutability behaviors, and strict Decimal type
adherence across all domain data transfer objects.
"""

from dataclasses import FrozenInstanceError
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from aegis.core.model import (
    AccountSnapshot,
    BrokerEvent,
    EventType,
    ExposureIntent,
    Order,
    OrderReceipt,
    OrderSide,
    OrderState,
    OrderType,
    PositionSide,
    TimeInForce,
)
from tests.testutil import (
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

def test_order_receipt_immutability() -> None:
    """Verifies OrderReceipt raises FrozenInstanceError upon modification."""
    receipt = OrderReceipt(
        average_execution_price=None,
        broker_order_id='BRK-999',
        client_order_id='ORD-123',
        executed_quantity=Decimal('1.0'),
        group_id='AEGIS-TEST-ID',
        reject_reason=None,
        state=OrderState.PENDING,
    )

    with pytest.raises(FrozenInstanceError):
        receipt.state = OrderState.FILLED  # type: ignore

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

# -----------------------------------------------------------------------------

def test_order_side_reverse() -> None:
    """Verifies OrderSide reverse successfully returns the opposite side."""
    assert OrderSide.BUY.reverse() == OrderSide.SELL
    assert OrderSide.SELL.reverse() == OrderSide.BUY

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_exposure_intent_none_signals_flat_state() -> None:
    """Verify that a None alpha direction evaluates strictly as flat."""
    intent = ExposureIntent(alpha_direction=None)

    assert intent.is_flat()
    assert not intent.is_entry()
    assert not intent.is_exit()

# -----------------------------------------------------------------------------

def test_exposure_intent_non_zero_signals_active_entry() -> None:
    """Verify that any non-zero conviction scalar signals a market entry intent."""
    intent_buy = ExposureIntent(alpha_direction=0.8)
    intent_sell = ExposureIntent(alpha_direction=-0.5)

    assert not intent_buy.is_flat()
    assert intent_buy.is_entry()
    assert not intent_buy.is_exit()

    assert not intent_sell.is_flat()
    assert intent_sell.is_entry()
    assert not intent_sell.is_exit()

# -----------------------------------------------------------------------------

def test_exposure_intent_zero_signals_explicit_liquidation_exit() -> None:
    """Verify that a zero alpha direction evaluates strictly as a market exit."""
    intent = ExposureIntent(alpha_direction=0.0)

    assert not intent.is_flat()
    assert not intent.is_entry()
    assert intent.is_exit()

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
