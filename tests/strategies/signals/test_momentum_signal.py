"""Aegis Framework - Momentum Signal Pure Mathematics Unit Tests.

Validates stateless signal generation models using primitive vector spaces.
"""

from strategies.signals.momentum_signal import MomentumSignal

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_momentum_signal_evaluates_pure_bearish_crossover() -> None:
    """Ensures indicator outputs full negative conviction on bearish crossovers."""
    historical_closes = [10.0, 10.0, 10.0, 10.0, 5.0]

    indicator = MomentumSignal(fast_period=2, slow_period=4)
    conviction_alpha = indicator.calculate_alpha(prices=historical_closes)

    assert isinstance(conviction_alpha, float)
    assert conviction_alpha == -1.0

# -----------------------------------------------------------------------------

def test_momentum_signal_evaluates_pure_bullish_crossover() -> None:
    """Ensures indicator outputs full positive conviction on bullish crossovers."""
    historical_closes = [10.0, 10.0, 10.0, 10.0, 15.0]

    indicator = MomentumSignal(fast_period=2, slow_period=4)
    conviction_alpha = indicator.calculate_alpha(prices=historical_closes)

    assert isinstance(conviction_alpha, float)
    assert conviction_alpha == 1.0

# -----------------------------------------------------------------------------

def test_momentum_signal_returns_neutral_on_insufficient_history() -> None:
    """Ensures strategy handles warm-up gaps returning neutral conviction."""
    historical_closes = [10.0, 10.0]

    indicator = MomentumSignal(fast_period=2, slow_period=4)
    conviction_alpha = indicator.calculate_alpha(prices=historical_closes)

    assert conviction_alpha == 0.0

# -----------------------------------------------------------------------------

def test_momentum_signal_returns_neutral_on_parallel_trajectories() -> None:
    """Ensures strategy returns neutral score when no crossover event is detected."""
    historical_closes = [10.0, 10.0, 10.0, 10.0, 10.0]

    indicator = MomentumSignal(fast_period=2, slow_period=4)
    conviction_alpha = indicator.calculate_alpha(prices=historical_closes)

    assert conviction_alpha == 0.0

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
