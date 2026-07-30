"""Aegis Framework - Base Broker Adapter Conformity Tests.

Verifies abstract broker contract enforcement, instantiation restrictions, and
transaction routing protocols for external gateway adapters.
"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

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
from broker_adapters.base_broker_adapter import BaseBrokerAdapter

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
                balance=Decimal("10000.00"),
                equity=Decimal("10000.00"),
                available_margin=Decimal("10000.00"),
            )

        def submit_order(self, order: Order) -> OrderReceipt:
            return OrderReceipt(
                broker_order_id="BRK-123",
                client_order_id=order.client_order_id,
                status=OrderStatus.FILLED,
                average_execution_price=Decimal("1.0850"),
                reject_reason=None,
            )

    adapter = DummyBrokerAdapter()
    snapshot = adapter.get_account_snapshot()

    order = Order(
        client_order_id="ORD-001",
        timestamp=datetime(2026, 7, 30, 12, 0, tzinfo=ZoneInfo("UTC")),
        symbol="EURUSD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        quantity=Decimal("100000"),
    )
    receipt = adapter.submit_order(order)

    assert isinstance(snapshot, AccountSnapshot)
    assert isinstance(receipt, OrderReceipt)
    assert isinstance(adapter, BaseBrokerAdapter)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
