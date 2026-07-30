"""Aegis Framework - Strategy Intentions Contract Unit Tests.

Validates that strategy instances return pure alpha destination signals.
"""

import pytest

from core.exceptions import (
    InsufficientHistoryError,
    InvalidSignalError,
)
from core.models import ExposureIntent
from tests.strategies.factories import create_mock_market_context
from tests.strategies.mocks import (
    MockAlphaStrategy,
    MockAnomalousStrategy,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_abstract_strategy_enforces_exposure_intent_return_contract() -> None:
    """Ensures strategy execution cycles return a structured intent DTO."""
    context = create_mock_market_context()
    historical_values = [1.0800] * 10

    strategy = MockAlphaStrategy(warm_up_period=5)
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
    context = create_mock_market_context()
    historical_values = [1.0800] * 3

    strategy = MockAlphaStrategy(warm_up_period=5)

    with pytest.raises(InsufficientHistoryError):
        strategy.evaluate(market_context=context, historical_values=historical_values)

# -----------------------------------------------------------------------------

def test_abstract_strategy_raises_invalid_signal_error() -> None:
    """Ensures mathematical signal drifts trigger immediate contract exceptions."""
    context = create_mock_market_context()
    historical_values = [1.0800] * 10

    strategy = MockAnomalousStrategy(warm_up_period=5)

    with pytest.raises(InvalidSignalError):
        strategy.evaluate(market_context=context, historical_values=historical_values)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
