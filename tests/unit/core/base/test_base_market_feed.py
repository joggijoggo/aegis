"""Aegis Framework - Base Market Feed Conformity Tests.

Verifies abstract iterator interface enforcement, instantiation restrictions,
and stream consumption protocols for financial data feeds.
"""

from datetime import datetime

import pytest

from aegis.core.base import BaseMarketFeed
from aegis.core.model import (
    MarketContext,
    MarketPricePoint,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_base_market_feed_abstract_enforcement() -> None:
    """Verifies BaseMarketFeed cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseMarketFeed()  # type: ignore

# -----------------------------------------------------------------------------

def test_base_market_feed_nominal_implementation() -> None:
    """Verifies a compliant subclass correctly yields MarketContext objects."""
    class DummyMarketFeed(BaseMarketFeed):

        def __next__(self) -> MarketContext:
            price_point = MarketPricePoint(
                timestamp=datetime(2026, 7, 30, 12, 0),
                mid_price=1.0850,
                bid=1.0849,
                ask=1.0851,
                current_atr=0.0015,
                is_night_tariff=False,
            )
            return MarketContext(
                prices=price_point,
                volume=1500.0,
            )

    feed = DummyMarketFeed()
    context = next(feed)
    assert isinstance(context, MarketContext)
    assert isinstance(context.prices, MarketPricePoint)
    assert isinstance(feed, BaseMarketFeed)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
