"""Aegis Framework - Shared Test Artifacts and Static Context.

Provides centralized data structures, mock profiles, and static configurations.
"""

from core.models import InstrumentSpecification
from core.registry import InstrumentRegistry

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

_TEST_SPECS = {
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

TEST_REGISTRY = InstrumentRegistry(specifications=_TEST_SPECS)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
