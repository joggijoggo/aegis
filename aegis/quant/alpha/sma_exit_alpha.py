"""Aegis Framework - Simple Moving Average Exit Alpha.

Evaluates market price interaction and crossovers against a simple moving average line.
"""

import logging

from aegis.core.base import BaseAlpha
from aegis.core.exception import InsufficientHistoryError
from aegis.core.model import MarketContext
from aegis.quant.indicator import SimpleMovingAverage

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class SmaExitAlpha(BaseAlpha):
    """Exit signal triggering upon price interaction crossovers with the SMA line."""

# -----------------------------------------------------------------------------

    def __init__(self, period: int) -> None:
        super().__init__()
        self._sma_indicator = SimpleMovingAverage(period=period)

# -----------------------------------------------------------------------------

    def evaluate(
        self,
        market_context: MarketContext,
        historical_values: list[float],
    ) -> float:
        """Evaluates the market to determine the crossover exit conviction.

        Args:
            market_context: The current market state.
            historical_values: Trailing price series.

        Returns:
            The calculated directional exit conviction strength.
        """
        try:
            sma_value = self._sma_indicator.calculate(historical_values)
            current_mid = market_context.prices.mid_price
            previous_mid = historical_values[-1]

            # Case 1: Bearish crossover (Cross Under) -> Slipped below the line
            if previous_mid >= sma_value and current_mid < sma_value:
                return 1.0

            # Case 2: Bullish crossover (Cross Over) -> Pierced above the line
            if previous_mid <= sma_value and current_mid > sma_value:
                return 1.0
        except InsufficientHistoryError: # pragma: no cover
            pass

        return 0.0

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
