"""Aegis Framework - Technical Signals Interface.

Defines the unified operational contract for stateless conviction pipelines.
"""

from abc import (
    ABC,
    abstractmethod,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class AbstractSignal(ABC):
    """Structural interface contract enforcing unified mathematical alpha generation."""

# -----------------------------------------------------------------------------

    @abstractmethod
    def calculate_alpha(self, prices: list[float]) -> float:
        """Evaluates price vectors to determine structural technical setups.

        Args:
            prices: A sequential list of historical prices.

        Returns:
            The normalized direction intent scalar bounded strictly between
                -1.0 (maximum bearish) and 1.0 (maximum bullish).
        """
        pass

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
