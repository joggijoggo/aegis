"""Aegis Framework - Core Base Alpha Contract Tests.

Verifies abstract base interface enforcement, instantiation restrictions, and
subclass implementation requirements for quantitative alpha models.
"""

import pytest

from aegis.core.base import BaseAlpha
from tests.testutil import (
    FakeAlpha,
    create_market_context_factory,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_base_alpha_cannot_be_instantiated_directly() -> None:
    """Verifies that the abstract class raises TypeError upon direct init."""
    with pytest.raises(TypeError):
        BaseAlpha()  # type: ignore[abstract]

# -----------------------------------------------------------------------------

def test_compliant_subclass_can_be_instantiated_and_evaluated() -> None:
    """Verifies that a subclass with valid signatures runs seamlessly."""
    alpha = FakeAlpha()
    context = create_market_context_factory()

    result = alpha.evaluate(market_context=context, historical_values=[1.1200])

    assert result == 1.0

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
