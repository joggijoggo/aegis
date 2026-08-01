"""Aegis Framework - Momentum Alpha Signal Unit Tests.

Validates trend tracking crossover direction logic accuracy and protection limits.
"""

import pytest

from core.exceptions import InsufficientHistoryError
from strategies.signals.momentum_signal import MomentumSignal

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_momentum_signal_detects_bearish_crossover() -> None:
    """Ensures downward dual moving average crossings generate bearish states."""
    signal = MomentumSignal(fast_period=2, slow_period=4)
    prices = [10.0, 11.0, 12.0, 13.0, 9.5]

    result = signal.calculate_alpha(prices=prices)

    assert result == -1.0

# -----------------------------------------------------------------------------

def test_momentum_signal_detects_bullish_crossover() -> None:
    """Ensures upward dual moving average crossings generate bullish states."""
    signal = MomentumSignal(fast_period=2, slow_period=4)
    prices = [10.0, 9.0, 8.0, 7.0, 11.0]

    result = signal.calculate_alpha(prices=prices)

    assert result == 1.0

# -----------------------------------------------------------------------------

def test_momentum_signal_raises_insufficient_history_error() -> None:
    """Ensures series length shortfalls trigger immediate specific exceptions."""
    signal = MomentumSignal(fast_period=2, slow_period=4)
    prices = [10.0, 11.0]

    with pytest.raises(InsufficientHistoryError):
        signal.calculate_alpha(prices=prices)

# -----------------------------------------------------------------------------

def test_momentum_signal_returns_neutral_when_trend_persists() -> None:
    """Ensures continuous market direction returns clear static flat states."""
    signal = MomentumSignal(fast_period=2, slow_period=4)
    prices = [10.0, 11.0, 12.0, 13.0, 14.0]

    result = signal.calculate_alpha(prices=prices)

    assert result == 0.0

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
