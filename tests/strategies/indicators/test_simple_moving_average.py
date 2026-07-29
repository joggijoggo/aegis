"""Aegis Framework - Simple Moving Average Indicator Unit Tests.

Validates rolling arithmetic mean calculation accuracy and boundary safety limits.
"""

import pytest

from core.exceptions import InsufficientHistoryError
from strategies.indicators.simple_moving_average import SimpleMovingAverage

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_simple_moving_average_calculates_correct_arithmetic_mean() -> None:
    """Ensures calculated output matches exact mathematical expectations."""
    indicator = SimpleMovingAverage(period=3)
    values = [10.0, 20.0, 30.0, 40.0]

    result = indicator.calculate(values=values)

    assert result == 30.0

# -----------------------------------------------------------------------------

def test_simple_moving_average_raises_insufficient_history_error() -> None:
    """Ensures series length shortfalls trigger immediate specific exceptions."""
    indicator = SimpleMovingAverage(period=3)
    values = [10.0, 20.0]

    with pytest.raises(InsufficientHistoryError):
        indicator.calculate(values=values)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
