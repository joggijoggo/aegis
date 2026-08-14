"""Aegis Framework - Naive Trend Following Bot.

Orchestrates sequential trade initiation and structural exit decisions using
momentum and rolling moving average calculations.
"""

import logging

from aegis.core.base import BaseBot
from aegis.core.model import (
    ExposureIntent,
    MarketContext,
)
from aegis.quant.alpha import (
    SmaExitAlpha,
    ThreeGreenBarsAlpha,
)

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class NaiveTrendBot(BaseBot):
    """Trading robot combining momentum entry with moving average exit signals."""

# -----------------------------------------------------------------------------

    def __init__(self, sma_period: int) -> None:
        """Initializes the robot parameters.

        Args:
            sma_period: The calculation period for the exit baseline.
        """
        super().__init__()

        self._sma_period = sma_period

        self._entry_alpha = ThreeGreenBarsAlpha()
        self._exit_alpha = SmaExitAlpha(period=sma_period)

# -----------------------------------------------------------------------------

    def evaluate(
        self,
        market_context: MarketContext,
        historical_values: list[float],
    ) -> ExposureIntent:
        """Evaluates the market to determine the exposure intent.

        Args:
            market_context: The current market state.
            historical_values: Trailing price series.

        Returns:
            The calculated market exposure intent.
        """
        exit_signal = self._exit_alpha.evaluate(
            market_context,
            historical_values,
        )

        if exit_signal >= 1.0:
            return ExposureIntent(alpha_direction=0.0)

        entry_signal = self._entry_alpha.evaluate(
            market_context,
            historical_values,
        )

        if entry_signal >= 1.0:
            take_profit_ticks = 400
            stop_loss_ticks = 200 # FIXME: use atr

            return ExposureIntent(
                alpha_direction=1.0,
                stop_loss_ticks=stop_loss_ticks,
                take_profit_ticks=take_profit_ticks,
            )

        return ExposureIntent(alpha_direction=None)

# -----------------------------------------------------------------------------

    @property
    def warm_up_period(self):
        return max([ # pragma: no cover
            self._sma_period, # Indicator pre-requisite
            2, # Exit alpha needs at least 2 historical bars
            3, # Entry alpha needs at least 3 historical bars
        ])

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
