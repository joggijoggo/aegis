"""Aegis Framework - Simple Moving Average Indicator.

Provides the mathematical calculation for rolling simple moving averages.
"""

from core.exceptions import InsufficientHistoryError
from strategies.indicators.base_indicator import AbstractIndicator

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class SimpleMovingAverage(AbstractIndicator):
    """Calculates the arithmetic mean of a rolling price window length."""

# -----------------------------------------------------------------------------

    def __init__(self, period: int):
        """Initializes the indicator configuration window.

        Args:
            period: The number of historical values required for the calculation.
        """
        self.period = period

# -----------------------------------------------------------------------------

    def calculate(self, values: list[float]) -> float:
        """Calculates the simple moving average value from the input series.

        Args:
            values: List of historical values to evaluate.

        Returns:
            The calculated arithmetic mean value.
        """
        if len(values) < self.period:
            raise InsufficientHistoryError(
                f"Insufficient data length {len(values)} "
                f"for indicator period {self.period}."
            )

        return sum(values[-self.period:]) / self.period

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
