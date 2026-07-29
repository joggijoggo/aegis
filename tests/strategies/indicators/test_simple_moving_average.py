"""Aegis Framework - Simple Moving Average Indicator Unit Tests.

Validates stateless mathematical data transformers using primitive series.
"""

import pytest

from strategies.indicators.simple_moving_average import SimpleMovingAverage

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_simple_moving_average_computes_exact_rolling_average() -> None:
    """Ensures moving average outputs precise mathematical expectations."""
    prices = [1.0800, 1.0810, 1.0820, 1.0830]

    indicator = SimpleMovingAverage(period=3)
    sma_value = indicator.calculate(values=prices)

    assert isinstance(sma_value, float)
    assert round(sma_value, 4) == 1.0820

# -----------------------------------------------------------------------------

def test_simple_moving_average_raises_value_error_on_short_series() -> None:
    """Ensures calculation fails safely with explicit exception on raw short series."""
    prices = [1.0800, 1.0810]

    indicator = SimpleMovingAverage(period=3)

    with pytest.raises(ValueError, match="Historical values length is shorter"):
        indicator.calculate(values=prices)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
