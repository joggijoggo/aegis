"""Aegis Framework - IG Live Broker Adapter Unit Tests.

Verifies production isolation constraints and environment safety locks.
"""

import pytest

from core.models import OrderType
from core.models import TransactionSide


# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_ig_live_adapter_enforces_production_lock():
    """Validates that IGLiveBrokerAdapter hard-locks all active outbound routes."""
    # Ce test va échouer immédiatement sur une ImportError à l'exécution
    from brokers.ig_live_adapter import IGLiveBrokerAdapter

    adapter = IGLiveBrokerAdapter(api_key="mock_key_xyz", environment="DEMO")

    with pytest.raises(NotImplementedError) as exc_info:
        adapter.place_order(
            symbol="EURUSD",
            side=TransactionSide.LONG,
            order_type=OrderType.MARKET,
            volume_lots=1.0
        )
    assert "Aegis Live-Safety Violation" in str(exc_info.value)

    with pytest.raises(NotImplementedError) as exc_info_portfolio:
        adapter.get_portfolio_snapshot()
    assert "Aegis Live-Safety Violation" in str(exc_info_portfolio.value)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
