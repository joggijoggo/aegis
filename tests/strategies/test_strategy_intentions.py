"""Aegis Framework - Strategy Intentions Contract Unit Tests.

Validates that strategy instances return pure alpha destination signals.
"""

import pytest

from core.exceptions import (
    InsufficientHistoryError,
    InvalidSignalError,
)
from core.models import ExposureIntent
from tests.testutils import (
    FakeStrategy,
    create_market_context_factory,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_abstract_strategy_enforces_exposure_intent_return_contract() -> None:
    """Ensures strategy execution cycles return a structured intent DTO."""
    context = create_market_context_factory()
    historical_values = [1.0800] * 10

    strategy = FakeStrategy(warm_up_period=5)
    assert strategy.warm_up_period == 5

    intent = strategy.evaluate(
        market_context=context,
        historical_values=historical_values,
    )

    assert isinstance(intent, ExposureIntent)
    assert intent.alpha_direction == 1.0
    assert intent.stop_loss_ticks == 20.0

# -----------------------------------------------------------------------------

def test_abstract_strategy_raises_insufficient_history_error() -> None:
    """Ensures data feeding shortfalls trigger immediate specific exceptions."""
    context = create_market_context_factory()
    historical_values = [1.0800] * 3

    strategy = FakeStrategy(warm_up_period=5)

    with pytest.raises(InsufficientHistoryError):
        strategy.evaluate(market_context=context, historical_values=historical_values)

# -----------------------------------------------------------------------------

def test_abstract_strategy_raises_invalid_signal_error() -> None:
    """Ensures mathematical signal drifts trigger immediate contract exceptions."""
    context = create_market_context_factory()
    historical_values = [1.0800] * 10

    # On injecte dynamiquement l'intention corrompue dans l'unique FakeStrategy
    corrupted_intent = ExposureIntent(alpha_direction=1.5)
    strategy = FakeStrategy(exposure_intent=corrupted_intent, warm_up_period=5)

    with pytest.raises(InvalidSignalError):
        strategy.evaluate(market_context=context, historical_values=historical_values)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
