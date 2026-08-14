"""Aegis Framework - SMA Exit Alpha Unit Tests.

Verifies bidirectional price crossover interaction mechanics against a
rolling simple moving average baseline using mid-market valuation metrics.
"""

from aegis.core.model import MarketPricePoint
from aegis.quant.alpha import SmaExitAlpha
from tests.testutil.factory import create_market_context_factory

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_alpha_triggers_on_bearish_crossover() -> None:
    """Verifies liquidation vector when price breaks downward through the SMA."""
    alpha = SmaExitAlpha(period=3)

    # Pre-calculated SMA-3 over these historical values equals 10.0
    # The last element (10.5) represents previous_mid at t-1 (above the SMA)
    historical_trail = [9.5, 10.0, 10.5]

    # Simulate current mid-price at t dropping below the SMA line (9.5 < 10.0)
    prices = MarketPricePoint(
        timestamp=None,
        mid_price=9.5,
        bid=9.4,
        ask=9.6,
        current_atr=0.2,
    )

    context = create_market_context_factory(prices=prices)

    result = alpha.evaluate(context, historical_trail)
    assert result == 1.0

# -----------------------------------------------------------------------------

def test_alpha_triggers_on_bullish_crossover() -> None:
    """Verifies liquidation vector when price breaks upward through the SMA."""
    alpha = SmaExitAlpha(period=3)

    # Pre-calculated SMA-3 over these historical values equals 10.0
    # The last element (9.5) represents previous_mid at t-1 (below the SMA)
    historical_trail = [10.5, 10.0, 9.5]

    # Simulate current mid-price at t piercing above the SMA line (10.5 > 10.0)
    prices = MarketPricePoint(
        timestamp=None,
        mid_price=10.5,
        bid=10.4,
        ask=10.6,
        current_atr=0.2,
    )

    context = create_market_context_factory(prices=prices)

    result = alpha.evaluate(context, historical_trail)
    assert result == 1.0

# -----------------------------------------------------------------------------

def test_alpha_returns_zero_when_no_crossover_occurs() -> None:
    """Verifies neutralization when price drifts without piercing the baseline."""
    alpha = SmaExitAlpha(period=3)

    # Pre-calculated SMA-3 over these historical values equals exactly 10.0
    # The last element (11.0) represents previous_mid at t-1 (strictly above the SMA)
    historical_trail = [9.0, 10.0, 11.0]

    # Simulate current mid-price at t remaining safely above the SMA line (11.2 > 10.0)
    prices = MarketPricePoint(
        timestamp=None, # type: ignore[arg-type]
        mid_price=11.2,
        bid=11.1,
        ask=11.3,
        current_atr=0.2,
    )

    context = create_market_context_factory(prices=prices)

    result = alpha.evaluate(context, historical_trail)
    assert result == 0.0

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
