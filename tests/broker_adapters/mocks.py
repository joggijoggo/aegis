"""Aegis Framework - Broker Adapters Testing Mocks.

Provides reusable broker gateway adapter mocks for decoupled unit testing.
"""

from decimal import Decimal

from broker_adapters.base_broker_adapter import BaseBrokerAdapter
from core.models import (
    AccountSnapshot,
    Order,
    OrderReceipt,
    OrderStatus,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class DummyBrokerAdapter(BaseBrokerAdapter):
    """Compliant broker execution gateway implementation for structural tests."""

    def get_account_snapshot(self) -> AccountSnapshot:
        """Extracts standard static structural ledger valuation records."""
        return AccountSnapshot(Decimal("10.0"), Decimal("10.0"), Decimal("10.0"))

    def submit_order(self, order: Order) -> OrderReceipt:
        """Routes transaction parameters records to verify gateway operations."""
        return OrderReceipt(None, "ORD-1", OrderStatus.PENDING)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
