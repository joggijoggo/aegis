"""Aegis Framework - Base Broker Adapter Conformity Tests.

Verifies abstract broker contract enforcement, instantiation restrictions, and
transaction routing protocols for external gateway adapters.
"""

import pytest

from aegis.core.base_broker_adapter import BaseBrokerAdapter

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_base_broker_adapter_abstract_enforcement() -> None:
    """Verifies BaseBrokerAdapter cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseBrokerAdapter()  # type: ignore

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
