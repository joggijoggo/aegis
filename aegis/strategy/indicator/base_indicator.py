"""Aegis Framework - Technical Indicators Abstract Port Interface.

Enforces structural compile-time type validation across stateless data transformers.
"""

from abc import (
    ABC,
    abstractmethod,
)
import logging

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class AbstractIndicator(ABC):
    """Structural interface contract enforcing unified mathematical calculations."""

# -----------------------------------------------------------------------------

    @abstractmethod
    def calculate(self, values: list[float]) -> float:
        """Computes the passive technical metrics over available data vectors.

        Args:
            values: A sequential list of numerical data points.

        Returns:
            The unique transformed scalar value.
        """
        pass

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
