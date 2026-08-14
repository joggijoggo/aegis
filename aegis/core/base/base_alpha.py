"""Aegis Framework - Base Alpha Model Contract.

Defines the quantitative blueprint for extracting directional market convictions.
"""

from abc import (
    ABC,
    abstractmethod,
)

from aegis.core.model import MarketContext

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class BaseAlpha(ABC):
    """Abstract directional quantitative model."""

# -----------------------------------------------------------------------------

    @abstractmethod
    def evaluate(
        self,
        market_context: MarketContext,
        historical_values: list[float],
    ) -> float:
        """Evaluates the market to determine the directional conviction.

        Args:
            market_context: The current market state.
            historical_values: Trailing price series.

        Returns:
            The calculated directional conviction strength.
        """

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
