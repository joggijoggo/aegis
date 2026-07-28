"""Aegis Framework - Risk Manager Unit Tests.

Verifies capital preservation via margin checks and maximum drawdown fuses.
"""

from core.models import InstrumentSpecification
from core.models import OrderRequest
from core.registry import InstrumentRegistry
from core.risk_manager import RiskManager
from tests.test_constants import TEST_REGISTRY

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_risk_manager_approves_compliant_allocation_metrics():
    """Verify that the risk manager passes orders within safety limits."""
    manager = RiskManager(instrument_registry=TEST_REGISTRY, max_drawdown_limit=10.0)
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
    manager = RiskManager(instrument_registry=TEST_REGISTRY, max_drawdown_limit=10.0)
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

def test_risk_manager_prevents_ieee754_multiplication_accumulation_anomalies():
    """Verify that the risk manager neutralizes float rounding micro-residues.

    With raw floats, calculating the required margin for 1.3 lots of EURUSD
    at price 1.1543 with a 5% (0.05) margin requirement generates a binary
    noise (7502.950000000001). A comparison against exact available liquidity
    causes a false rejection, which only precise decimal matching prevents.
    """
    local_specs = {
        "EURUSD": InstrumentSpecification(
            base_spread_ticks=0.6,
            lot_size=100000,
            lot_step=0.01,
            margin_requirement=0.05,
            min_lot=0.10,
            tick_size=0.0001,
            volatility_factor=0.1,
        ),
    }
    local_registry = InstrumentRegistry(specifications=local_specs)

    manager = RiskManager(instrument_registry=local_registry, max_drawdown_limit=10.0)
    request = OrderRequest(
        symbol="EURUSD",
        stop_loss_ticks=20.0,
        risk_percentage=1.0,
        confidence_factor=1.0,
    )

    result = manager.assess_order_risk(
        account_equity=10000.0,
        volume_lots=1.3,
        current_price=1.1543,
        available_liquidity=7502.95,
        current_portfolio_drawdown=0.0,
        order_request=request,
    )

    assert result.is_approved is True
    assert result.calculated_volume_lots == 1.3
    assert result.rejection_reason == ""

# -----------------------------------------------------------------------------

def test_risk_manager_triggers_fuse_when_max_drawdown_limit_is_breached():
    """Verify that the risk manager cuts execution when equity degradation peaks."""
    manager = RiskManager(instrument_registry=TEST_REGISTRY, max_drawdown_limit=10.0)
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
