"""Aegis Framework - IG Markets Live Production Adapter Unit Tests.

Validates institutional safety gates, parameters formatting, and lock constraints.
"""

import pytest

from brokers.ig_live_adapter import IGLiveBrokerAdapter
from core.models import OrderType
from core.models import TransactionSide

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_ig_live_adapter_enforces_production_lock():
    """Validates that IGLiveBrokerAdapter hard-locks all active outbound routes."""
    adapter = IGLiveBrokerAdapter(api_key="mock_key_xyz", environment="DEMO")

    with pytest.raises(NotImplementedError) as exc_info:
        adapter.place_order(
            symbol="EURUSD",
            side=TransactionSide.LONG,
            order_type=OrderType.MARKET,
            volume_lots=1.0,
            stop_loss_price=1.0980,
            take_profit_price=1.1040
        )

    assert "Live API routing interfaces are locked" in str(exc_info.value)


# -----------------------------------------------------------------------------

def test_ig_live_adapter_raises_permission_error_on_production_environment():
    """Validates that the adapter triggers immediate lockout on live environment."""
    with pytest.raises(PermissionError) as exc_info:
        IGLiveBrokerAdapter(api_key="live_key_123", environment="PRODUCTION")

    assert "production lockout is active" in str(exc_info.value)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
