"""Aegis Framework - Abstract Broker Bridge Unit Tests.

Verifies the constraint contracts of the core broker port interfaces.
"""

import pytest


# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_abstract_broker_bridge_cannot_be_instantiated():
    """Validates that AbstractBrokerBridge enforces abstract class contracts."""
    from brokers.base_broker import AbstractBrokerBridge

    with pytest.raises(TypeError):
        AbstractBrokerBridge()  # type: ignore

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
