"""Aegis Framework - Backtrader Market Feed Adapter.

Provides the market feed adapter that extracts and translates synchronized historical price data.
"""

from typing import Any

from broker_adapters.backtrader_bridge import BacktraderBridge
from core.models import (
    MarketContext,
    MarketPricePoint,
)
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

        # Intercept the infrastructure shutdown signal to gracefully halt
        # the execution loop before hitting the translation layer.
        if raw_data is None:
            raise StopIteration

        return self._translate_to_market_context(raw_data)

# -----------------------------------------------------------------------------

    def _translate_to_market_context(self, raw_data: Any) -> MarketContext:
        """Translates raw infrastructure price data into domain structures.

        Args:
            raw_data: The raw infrastructure data update instance.

        Returns:
            The translated market context snapshot.
        """
        current_time = raw_data.datetime.datetime(0)
        mid = float(raw_data.close[0])
        bid = mid # TODO: implement friction?
        ask = mid # TODO: implement friction?

        # Microstructural estimation of local volatility and spreads
        current_atr = 0.0 # TODO: compute or delete?
        is_night_tariff = False # TODO: implement friction?

        price_point = MarketPricePoint(
            timestamp=current_time,
            mid_price=mid,
            bid=bid,
            ask=ask,
            current_atr=current_atr,
            is_night_tariff=is_night_tariff,
        )

        return MarketContext(
            prices=price_point,
            volume=float(raw_data.volume[0]),
        )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
