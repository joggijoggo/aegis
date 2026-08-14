"""Aegis Framework - Three Green Bars Alpha Unit Tests.

Verifies sequential candle evaluation, historical depth boundary limits,
and mathematical initiation trigger vectors for momentum buying conviction.
"""

from aegis.quant.alpha import ThreeGreenBarsAlpha
from tests.testutil.factory import create_market_context_factory

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_alpha_triggers_on_three_consecutive_green_bars() -> None:
    """Verifies entry activation when the last three candles close upward."""
    alpha = ThreeGreenBarsAlpha()
    context = create_market_context_factory()

    # Establish a perfect sequential bullish trend: 1.1000 -> 1.1200 -> 1.1500
    historical_trail = [1.1000, 1.1200, 1.1500]
    result = alpha.evaluate(context, historical_trail)

    assert result == 1.0

# -----------------------------------------------------------------------------

def test_alpha_returns_zero_on_invalid_or_flat_sequence() -> None:
    """Verifies neutralization when trend pauses or turns downward."""
    alpha = ThreeGreenBarsAlpha()
    context = create_market_context_factory()

    # Scenario A: Bullish trend breaks on the very last candle (1.1500 -> 1.1300)
    assert alpha.evaluate(context, [1.1000, 1.1500, 1.1300]) == 0.0

    # Scenario B: Market stalls resulting in a flat closing sequence (1.1200 -> 1.1200)
    assert alpha.evaluate(context, [1.1000, 1.1200, 1.1200]) == 0.0

# -----------------------------------------------------------------------------

def test_alpha_returns_zero_when_history_is_insufficient() -> None:
    """Verifies protection threshold when backlog has fewer than three entries."""
    alpha = ThreeGreenBarsAlpha()
    context = create_market_context_factory()

    # Check boundary protection limits with only two data points available
    assert alpha.evaluate(context, [1.1000, 1.1200]) == 0.0

    # Check boundary protection limits with a completely empty price vector
    assert alpha.evaluate(context, []) == 0.0

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
