"""Aegis Framework - Position Sizer Unit Tests.

Verifies risk budget enforcement, dynamic sizing models, and leverage caps.
"""

from core.models import OrderRequest
from core.models import RiskValidationResult
from tests.test_constants import TEST_REGISTRY
from core.position_sizer import PositionSizer

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
    sizer = PositionSizer(instrument_registry=TEST_REGISTRY)
    request = OrderRequest(
        symbol="EURUSD",
        stop_loss_ticks=20.0,
        risk_percentage=1.0,
        confidence_factor=0.8,
    )

    result = sizer.compute_volume(
        account_equity=10000.0,
        order_request=request,
    )

    assert result.is_approved is True
    assert result.calculated_volume_lots == 0.4
    assert result.rejection_reason == ""

# -----------------------------------------------------------------------------

def test_position_sizer_applies_strict_floor_truncation_based_on_lot_step():
    """Verify that the sizer strictly truncates lots down to lot_step granularity."""
    sizer = PositionSizer(instrument_registry=TEST_REGISTRY)
    request = OrderRequest(
        symbol="EURUSD",
        stop_loss_ticks=20.0,
        risk_percentage=1.0,
        confidence_factor=0.95,
    )

    result = sizer.compute_volume(
        account_equity=10000.0,
        order_request=request,
    )

    assert result.is_approved is True
    assert result.calculated_volume_lots == 0.47

# -----------------------------------------------------------------------------

def test_position_sizer_rejects_orders_below_minimum_contract_size():
    """Verify that the sizer flags a rejection when computed volume is below min_lot."""
    sizer = PositionSizer(instrument_registry=TEST_REGISTRY)
    request = OrderRequest(
        symbol="EURUSD",
        stop_loss_ticks=20.0,
        risk_percentage=1.0,
        confidence_factor=0.05,
    )

    result = sizer.compute_volume(
        account_equity=10000.0,
        order_request=request,
    )

    assert result.is_approved is False
    assert result.calculated_volume_lots == 0.0
    assert "below minimum contract size" in result.rejection_reason.lower()

# -----------------------------------------------------------------------------

def test_position_sizer_rejects_exaggerated_confidence_coefficients():
    """Verify that the sizer blocks confidence values amplifying nominal risk."""
    sizer = PositionSizer(instrument_registry=TEST_REGISTRY)
    request = OrderRequest(
        symbol="EURUSD",
        stop_loss_ticks=20.0,
        risk_percentage=1.0,
        confidence_factor=1.5,
    )

    result = sizer.compute_volume(
        account_equity=10000.0,
        order_request=request,
    )

    assert result.is_approved is False
    assert "cannot amplify maximum risk" in result.rejection_reason.lower()

# -----------------------------------------------------------------------------

def test_position_sizer_rejects_invalid_or_negative_stop_loss_distances():
    """Verify that the sizer blocks negative stop loss ticks intervals."""
    sizer = PositionSizer(instrument_registry=TEST_REGISTRY)
    request = OrderRequest(
        symbol="EURUSD",
        stop_loss_ticks=-10.0,
        risk_percentage=1.0,
        confidence_factor=0.8,
    )

    result = sizer.compute_volume(
        account_equity=10000.0,
        order_request=request,
    )

    assert result.is_approved is False
    assert "invalid risk or stop loss" in result.rejection_reason.lower()

# -----------------------------------------------------------------------------

def test_position_sizer_rejects_negative_risk_parameters_inputs():
    """Verify that the sizer blocks negative risk percentage configurations."""
    sizer = PositionSizer(instrument_registry=TEST_REGISTRY)
    request = OrderRequest(
        symbol="EURUSD",
        stop_loss_ticks=20.0,
        risk_percentage=-1.0,
        confidence_factor=0.8,
    )

    result = sizer.compute_volume(
        account_equity=10000.0,
        order_request=request,
    )

    assert result.is_approved is False
    assert "risk parameters cannot be negative" in result.rejection_reason.lower()

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
