"""Aegis Framework - Trading Bot Foundations.

Defines the core behavioral interface for implementation of systematic trading
algorithms and execution decision-making logic.
"""

from abc import (
    ABC,
    abstractmethod,
)
import logging

from aegis.core.model import (
    ExposureIntent,
    MarketContext,
)

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class BaseBot(ABC):
    """Interface for trading bots."""

# -----------------------------------------------------------------------------

    @abstractmethod
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
        pass

# -----------------------------------------------------------------------------

    @property
    @abstractmethod
    def warm_up_period(self) -> int:
        """Gets the minimum historical data length required for evaluation.

        Returns:
            The minimum number of historical elements required.
        """
        pass

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
