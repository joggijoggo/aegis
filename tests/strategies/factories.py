"""Aegis Framework - Domain Model Testing Factories.

Provides standardized data structures construction helpers for isolated testing.
"""

from core.models import (
    MarketContext,
    MarketPricePoint,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def create_mock_market_context(
    prices: MarketPricePoint | None = None,
    volume: float | None = None,
) -> MarketContext:
    """Creates a standardized market context instance for testing."""
    return MarketContext(
        prices=prices or create_mock_price_point(),
        volume=volume,
    )

# -----------------------------------------------------------------------------

def create_mock_price_point(
    mid_price: float = 1.0850,
    bid: float = 1.0849,
    ask: float = 1.0851,
    current_atr: float = 0.0020,
) -> MarketPricePoint:
    """Creates a standardized market price snapshot instance for testing."""
    return MarketPricePoint(
        timestamp=None,
        mid_price=mid_price,
        bid=bid,
        ask=ask,
        current_atr=current_atr,
    )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
