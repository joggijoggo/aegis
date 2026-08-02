"""Aegis Framework - Base Broker Adapter Conformity Tests.

Verifies abstract broker contract enforcement, instantiation restrictions, and
transaction routing protocols for external gateway adapters.
"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from broker_adapters.base_broker_adapter import BaseBrokerAdapter
from core.models import (
    AccountSnapshot,
    BrokerEvent,
    EventType,
    Order,
    OrderSide,
    OrderType,
    PositionLedger,
    TimeInForce,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_base_broker_adapter_abstract_enforcement() -> None:
    """Verifies BaseBrokerAdapter cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseBrokerAdapter()  # type: ignore

# -----------------------------------------------------------------------------

def test_base_broker_adapter_nominal_implementation() -> None:
    """Verifies a compliant subclass instantiates and executes contract rules."""
    class DummyBrokerAdapter(BaseBrokerAdapter):

        def get_account_snapshot(self) -> AccountSnapshot:
            return AccountSnapshot(
                currency='EURUSD',
                balance=Decimal('10000.00'),
                equity=Decimal('10000.00'),
                available_margin=Decimal('10000.00'),
            )

        def get_position_ledger(self) -> PositionLedger:
            raise NotImplementedError()

        def submit_order(self, order: Order) -> None:
            pass

        def has_pending_events(self) -> bool:
            return True

        def poll_event(self) -> BrokerEvent:
            return BrokerEvent(
                event_type=EventType.ORDER_NOTIFICATION,
                payload={'status': 'FILLED'},
            )

    adapter = DummyBrokerAdapter()
    snapshot = adapter.get_account_snapshot()

    order = Order(
        client_order_id='ORD-001',
        timestamp=datetime(2026, 7, 30, 12, 0, tzinfo=ZoneInfo('UTC')),
        symbol='EURUSD',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        quantity=Decimal('100000'),
    )

    adapter.submit_order(order)
    has_pending_events = adapter.has_pending_events()
    event = adapter.poll_event()

    assert isinstance(snapshot, AccountSnapshot)
    assert has_pending_events is True
    assert isinstance(event, BrokerEvent)
    assert isinstance(adapter, BaseBrokerAdapter)


# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
