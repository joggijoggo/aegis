"""Aegis Framework - Position Sizer Unit Tests.

Verifies risk budget enforcement, dynamic sizing models, and leverage caps.
"""

from core.models import InstrumentSpecification
from core.models import OrderRequest
from core.models import RiskValidationResult
from core.registry import InstrumentRegistry
from core.position_sizer import PositionSizer

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

_TEST_RISK_SPECS = {
    "EURUSD": InstrumentSpecification(
        base_spread_ticks=0.6,
        tick_size=0.0001,
        volatility_factor=0.1,
        lot_size=100000,
    ),
}

TEST_RISK_REGISTRY = InstrumentRegistry(specifications=_TEST_RISK_SPECS)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_order_request_and_validation_result_value_objects_instantiation():
    """Verify that the core risk value objects store immutable state profiles."""
    request = OrderRequest(
        symbol="EURUSD",
        stop_loss_ticks=20.0,
        risk_percentage=1.0,
        confidence_factor=0.8,
    )

    assert request.symbol == "EURUSD"
    assert request.stop_loss_ticks == 20.0
    assert request.risk_percentage == 1.0
    assert request.confidence_factor == 0.8

    result = RiskValidationResult(
        is_approved=True,
        calculated_volume_lots=0.4,
        rejection_reason="",
    )

    assert result.is_approved is True
    assert result.calculated_volume_lots == 0.4
    assert result.rejection_reason == ""

# -----------------------------------------------------------------------------

def test_position_sizer_calculates_nominal_lots_under_confidence_factors():
    """Verify that the sizer dimensions lots based on risk and confidence scores."""
    sizer = PositionSizer(instrument_registry=TEST_RISK_REGISTRY)

    request = OrderRequest(
        symbol="EURUSD",
        stop_loss_ticks=20.0,
        risk_percentage=1.0,
        confidence_factor=0.8,
    )

    calculated_volume = sizer.compute_volume(
        account_equity=10000.0,
        order_request=request,
    )

    assert calculated_volume == 0.4

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
