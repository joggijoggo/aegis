"""Aegis Framework - Backtrader Market Feed Adapter.

Provides the market feed adapter that extracts and translates synchronized historical price data.
"""

from typing import Any

from broker_adapters.backtrader_bridge import BacktraderBridge
from core.models import MarketContext
from market_feeds.base_market_feed import BaseMarketFeed

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class BacktraderMarketFeed(BaseMarketFeed):
    """Market feed adapter implementing the core iteration interface for Backtrader data.

    Retrieves pricing updates through the central synchronization bridge and translates
    them into market context structures.
    """

# -----------------------------------------------------------------------------

    def __init__(self, bridge: BacktraderBridge) -> None:
        """Initializes the market feed adapter and hooks the synchronization reference.

        Args:
            bridge: The central synchronization bridge.
        """
        self._bridge = bridge

# -----------------------------------------------------------------------------

    def _translate_to_market_context(self, raw_data: Any) -> MarketContext:
        """Translates raw infrastructure price data into domain structures.

        Args:
            raw_data: The raw infrastructure data update instance.

        Returns:
            The translated market context snapshot.
        """
        pass

# -----------------------------------------------------------------------------

    def __next__(self) -> MarketContext:
        """Returns the next sequential market state context.

        Returns:
            The next market state context.

        Raises:
            StopIteration: Exhaustion of the data source.
        """
        if self._bridge.is_simulation_completed():
            raise StopIteration

        self._bridge.advance_time()
        raw_data = self._bridge.get_market_queue().get()

        return self._translate_to_market_context(raw_data)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
