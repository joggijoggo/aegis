"""Aegis Framework - Naive Trend Following Bot Unit Tests.

Verifies dual-alpha arbitration logic, prioritizing exit signals over entry
triggers, and validating final exposure intent structures.
"""

from unittest.mock import patch

from aegis.quant.bot.naive_trend_bot import NaiveTrendBot
from tests.testutil.factory import create_market_context_factory

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_bot_prioritizes_exit_signal_over_everything() -> None:
    """Verifies that an active exit alpha forces immediate zero exposure."""
    bot = NaiveTrendBot(sma_period=3)
    context = create_market_context_factory()
    historical_trail = [10.0, 10.0, 10.0]

    # Force the internal exit alpha to trigger and entry alpha to follow
    with patch.object(bot._exit_alpha, 'evaluate', return_value=1.0):
        with patch.object(bot._entry_alpha, 'evaluate', return_value=1.0):
            intent = bot.evaluate(context, historical_trail)

    assert intent.alpha_direction == 0.0

# -----------------------------------------------------------------------------

def test_bot_triggers_long_entry_intent_on_clean_signal() -> None:
    """Verifies long exposure allocation when entry triggers without hazard."""
    bot = NaiveTrendBot(sma_period=3)
    context = create_market_context_factory()
    historical_trail = [10.0, 10.0, 10.0]

    # Force clear passage for entry while safety remains peaceful
    with patch.object(bot._exit_alpha, 'evaluate', return_value=0.0):
        with patch.object(bot._entry_alpha, 'evaluate', return_value=1.0):
            intent = bot.evaluate(context, historical_trail)

    assert intent.alpha_direction == 1.0
    assert intent.stop_loss_ticks > 0
    assert intent.take_profit_ticks > 0 # FIXME: handle no TP

# -----------------------------------------------------------------------------

def test_bot_returns_none_intent_when_no_signals_are_active() -> None:
    """Verifies baseline state maintenance when market data drifts passively."""
    bot = NaiveTrendBot(sma_period=3)
    context = create_market_context_factory()
    historical_trail = [10.0, 10.0, 10.0]

    # Force both alpha paths to remain perfectly silent
    with patch.object(bot._exit_alpha, 'evaluate', return_value=0.0):
        with patch.object(bot._entry_alpha, 'evaluate', return_value=0.0):
            intent = bot.evaluate(context, historical_trail)

    assert intent.alpha_direction is None

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
