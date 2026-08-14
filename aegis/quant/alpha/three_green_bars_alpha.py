"""Aegis Framework - Three Green Bars Alpha Signal.

Extracts short-term buying conviction from three consecutive positive market candles.
"""

import logging

from aegis.core.base import BaseAlpha
from aegis.core.model import MarketContext

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class ThreeGreenBarsAlpha(BaseAlpha):
    """Bullish continuation model triggering upon three successive upward candles."""

# -----------------------------------------------------------------------------

    def evaluate(
        self,
        market_context: MarketContext,
        historical_values: list[float],
    ) -> float:
        """Evaluates the market to determine the entry momentum conviction.

        Args:
            market_context: The current market state.
            historical_values: Trailing price series.

        Returns:
            A value of 1.0 upon validation, otherwise 0.0.
        """
        if len(historical_values) < 3:
            return 0.0

        close_t1 = historical_values[-1]
        close_t2 = historical_values[-2]
        close_t3 = historical_values[-3]

        if close_t1 > close_t2 and close_t2 > close_t3:
            return 1.0

        return 0.0

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
