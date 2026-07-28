"""Aegis Framework - Risk Manager Unit Tests.

Verifies capital preservation via margin checks and maximum drawdown fuses.
"""

from core.models import OrderRequest
from tests.test_constants import TEST_REGISTRY
from core.risk_manager import RiskManager

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_risk_manager_approves_compliant_allocation_metrics():
    """Verify that the risk manager passes orders within safety limits."""
    manager = RiskManager(
        instrument_registry=TEST_REGISTRY,
        max_drawdown_limit=10.0,
    )

    request = OrderRequest(
        symbol="EURUSD",
        stop_loss_ticks=20.0,
        risk_percentage=1.0,
        confidence_factor=0.8,
    )

    result = manager.assess_order_risk(
        account_equity=10000.0,
        volume_lots=0.4,
        current_price=1.1000,
        available_liquidity=5000.0,
        current_portfolio_drawdown=2.0,
        order_request=request,
    )

    assert result.is_approved is True
    assert result.calculated_volume_lots == 0.4
    assert result.rejection_reason == ""

# -----------------------------------------------------------------------------

def test_risk_manager_blocks_orders_violating_margin_requirements():
    """Verify that the risk manager rejects trades exceeding available liquidity."""
    manager = RiskManager(
        instrument_registry=TEST_REGISTRY,
        max_drawdown_limit=10.0,
    )

    request = OrderRequest(
        symbol="EURUSD",
        stop_loss_ticks=20.0,
        risk_percentage=1.0,
        confidence_factor=0.8,
    )

    result = manager.assess_order_risk(
        account_equity=10000.0,
        volume_lots=15.0,
        current_price=1.1000,
        available_liquidity=100.0,
        current_portfolio_drawdown=0.0,
        order_request=request,
    )

    assert result.is_approved is False
    assert result.calculated_volume_lots == 0.0
    assert "insufficient margin liquidity" in result.rejection_reason.lower()

# -----------------------------------------------------------------------------

def test_risk_manager_triggers_fuse_when_max_drawdown_limit_is_breached():
    """Verify that the risk manager cuts execution when equity degradation peaks."""
    manager = RiskManager(
        instrument_registry=TEST_REGISTRY,
        max_drawdown_limit=10.0,
    )

    request = OrderRequest(
        symbol="EURUSD",
        stop_loss_ticks=20.0,
        risk_percentage=1.0,
        confidence_factor=0.8,
    )

    result = manager.assess_order_risk(
        account_equity=10000.0,
        volume_lots=0.4,
        current_price=1.1000,
        available_liquidity=5000.0,
        current_portfolio_drawdown=12.5,
        order_request=request,
    )

    assert result.is_approved is False
    assert result.calculated_volume_lots == 0.0
    assert "maximum drawdown limit breached" in result.rejection_reason.lower()

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
