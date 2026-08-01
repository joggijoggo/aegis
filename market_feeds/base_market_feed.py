"""Aegis Framework - Market Feed Foundations.

Defines the core behavioral interface for ingestion of streaming financial
market data updates.
"""

from abc import abstractmethod
from collections.abc import Iterator

from core.models import MarketContext

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class BaseMarketFeed(Iterator[MarketContext]):
    """Interface for financial market feeds."""

# -----------------------------------------------------------------------------

    @abstractmethod
    def __next__(self) -> MarketContext:
        """Gets the next market data update.

        Returns:
            The next market state context.

        Raises:
            MarketTimeoutError: Feed timeout expiration.
            StopIteration: Exhaustion of the data source.
        """
        pass

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
