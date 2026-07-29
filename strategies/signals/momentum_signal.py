"""Aegis Framework - Momentum Signal Specification.

Evaluates dual moving average crossovers to output a normalized direction conviction.
"""

from strategies.indicators.simple_moving_average import SimpleMovingAverage
from strategies.signals.base_signal import AbstractSignal

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class MomentumSignal(AbstractSignal):
    """Generates normalized direction intentions using dual moving average crossovers."""

# -----------------------------------------------------------------------------

    def __init__(self, fast_period: int = 2, slow_period: int = 4):
        """Initializes the alpha signal configuring underlying tracking windows.

        Args:
            fast_period: The window length for the reactive fast trend proxy.
            slow_period: The window length for the baseline slow trend proxy.
        """
        self.fast_ma = SimpleMovingAverage(period=fast_period)
        self.slow_ma = SimpleMovingAverage(period=slow_period)

# -----------------------------------------------------------------------------

    def calculate_alpha(self, prices: list[float]) -> float:
        """Evaluates price vectors to determine structural trend crossovers.

        Args:
            prices: A sequential list of historical prices.

        Returns:
            The normalized direction intent scalar bounded strictly between
                -1.0 (maximum bearish) and 1.0 (maximum bullish).
        """
        if len(prices) < (self.slow_ma.period + 1):
            return 0.0

        fast_current = self.fast_ma.calculate(values=prices)
        slow_current = self.slow_ma.calculate(values=prices)

        historical_slice = prices[:-1]
        fast_previous = self.fast_ma.calculate(values=historical_slice)
        slow_previous = self.slow_ma.calculate(values=historical_slice)

        if fast_previous <= slow_previous and fast_current > slow_current:
            return 1.0

        if fast_previous >= slow_previous and fast_current < slow_current:
            return -1.0

        return 0.0

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
