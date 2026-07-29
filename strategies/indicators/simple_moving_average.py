"""Aegis Framework - Simple Moving Average Technical Indicator.

Calculates the arithmetic rolling average over an isolated mathematical vector space.
"""

from strategies.indicators.base_indicator import AbstractIndicator

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class SimpleMovingAverage(AbstractIndicator):
    """Passively computes the simple moving average from an raw data values."""

# -----------------------------------------------------------------------------

    def __init__(self, period: int = 14):
        """Initializes the indicator configuration anchoring the window size.

        Args:
            period: The discrete number of historical intervals required for the
                rolling calculation window.
        """
        self.period = period

# -----------------------------------------------------------------------------

    def calculate(self, values: list[float]) -> float:
        """Computes the arithmetic average over the last available window space.

        Args:
            values: A sequential list of numerical data points.

        Returns:
            The unique transformed scalar value.

        Raises:
            ValueError: If the available data values length is shorter than the
                configured period window.
        """
        if len(values) < self.period:
            raise ValueError(
                "Historical values length is shorter than the indicator period."
            )

        return sum(values[-self.period:]) / self.period

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
