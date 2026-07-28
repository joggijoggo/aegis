"""Aegis Framework - Instrument Registry Unit Tests.

Verifies the central domain repository behavior and compile-time type safety.
"""

import pytest

from core.models import InstrumentSpecification

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_instrument_registry_fetches_contract_specifications():
    """Verify that the registry routes correct specs and raises a Fail-Fast error.

    Ensures unregistered assets trigger an immediate domain exception.
    """
    from core.registry import InstrumentRegistry

    # 1. Setup frozen asset specification metadata mapping
    spec_eurusd = InstrumentSpecification(
        base_spread_ticks=0.6,
        lot_size=100000,
        lot_step=0.01,
        margin_requirement=0.05,
        min_lot=0.10,
        tick_size=0.0001,
        volatility_factor=0.1,
    )
    spec_fr40 = InstrumentSpecification(
        base_spread_ticks=1.0,
        lot_size=1000,
        lot_step=0.1,
        margin_requirement=0.05,
        min_lot=0.1,
        tick_size=1.0,
        volatility_factor=0.0,
    )

    configs = {
        "EURUSD": spec_eurusd,
        "FR40": spec_fr40,
    }

    # 2. Instantiate central repository node
    registry = InstrumentRegistry(specifications=configs)

    # 3. Assert successful structural retrieval
    assert registry.get_specification(symbol="EURUSD") is spec_eurusd
    assert registry.get_specification(symbol="FR40") is spec_fr40

    # 4. Assert Fail-Fast boundary constraint on untracked asset identification
    with pytest.raises(ValueError, match="is missing from central instrument registry"):
        registry.get_specification(symbol="UNKNOWN_ASSET")

    # 5. Assert type and structural emptiness guards safety
    with pytest.raises(ValueError, match="Must be a non-empty string"):
        registry.get_specification(symbol="")

    with pytest.raises(ValueError, match="Must be a non-empty string"):
        registry.get_specification(symbol="   ")

    with pytest.raises(ValueError, match="Must be a non-empty string"):
        registry.get_specification(symbol=None)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
