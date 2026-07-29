"""Aegis Framework - Strategy Interface.

Provides the interface for data evaluation and signal generation.
"""

from abc import (
    ABC,
    abstractmethod,
)

from core.exceptions import (
    InsufficientHistoryError,
    InvalidSignalError,
)
from core.models import (
    ExposureIntent,
    MarketContext,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class AbstractStrategy(ABC):
    """Interface for evaluating market data and generating exposure signals."""

# -----------------------------------------------------------------------------

    def __init__(self, warm_up_period: int = 0) -> None:
        """Initializes the strategy settings and internal state.

        Args:
            warm_up_period: Minimum historical depth required to start trading.
        """
        self._warm_up_period = warm_up_period

# -----------------------------------------------------------------------------

    @abstractmethod
    def _evaluate(
        self,
        market_context: MarketContext,
        historical_values: list[float],
    ) -> ExposureIntent:
        """Executes the strategy calculation logic."""
        pass

# -----------------------------------------------------------------------------

    def evaluate(
        self,
        market_context: MarketContext,
        historical_values: list[float],
    ) -> ExposureIntent:
        """Evaluates market data to determine exposure intentions.

        Args:
            market_context: Current market state.
            historical_values: Historical series data points.

        Returns:
            The target exposure intent.
        """
        if len(historical_values) < self._warm_up_period:
            raise InsufficientHistoryError(
                f"Insufficient historical data length {len(historical_values)} "
                f"for configured warm-up period {self._warm_up_period}."
            )

        intent = self._evaluate(market_context, historical_values)

        if intent.alpha_direction is not None and not (
            -1.0 <= intent.alpha_direction <= 1.0
        ):
            raise InvalidSignalError(
                f"Strategy output alpha_direction {intent.alpha_direction} "
                "violates contract boundaries [-1.0, 1.0]."
            )

        return intent

# -----------------------------------------------------------------------------

    @property
    def warm_up_period(self) -> int:
        """Gets the minimum historical depth required to start trading.

        Returns:
            The minimum required historical data length.
        """
        return self._warm_up_period

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
