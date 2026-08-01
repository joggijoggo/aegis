"""Aegis Framework - Backtrader Market Feed Component Tests.

Validates the iteration lifecycles and nominal termination guards of the feed adapter.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from broker_adapters.backtrader_bridge import BacktraderBridge
from core.models import (
    MarketContext,
    MarketPricePoint,
)
from market_feeds.backtrader_market_feed import BacktraderMarketFeed

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_backtrader_market_feed_nominal_iteration() -> None:
    """Verifies that next extracts raw records and triggers translation."""
    mock_bridge = MagicMock(spec=BacktraderBridge)
    mock_bridge.is_simulation_completed.return_value = False

    mock_market_queue = MagicMock()
    mock_market_queue.get.return_value = 'raw_tick_payload'
    mock_bridge.get_market_queue.return_value = mock_market_queue

    feed = BacktraderMarketFeed(bridge=mock_bridge)
    mock_context = MagicMock(spec=MarketContext)

    feed._translate_to_market_context = MagicMock(return_value=mock_context)
    context = next(feed)

    assert context is mock_context
    mock_bridge.advance_time.assert_called_once()
    feed._translate_to_market_context.assert_called_once_with('raw_tick_payload')

# -----------------------------------------------------------------------------

def test_backtrader_market_feed_poison_pill_deadlock_reproduction() -> None:
    """Verifies that a None sentinel in the market queue immediately halts iteration before translation."""
    mock_bridge = MagicMock(spec=BacktraderBridge)
    mock_bridge.is_simulation_completed.return_value = False

    mock_market_queue = MagicMock()
    mock_market_queue.get.return_value = None  # Inject the triggering poison pill
    mock_bridge.get_market_queue.return_value = mock_market_queue

    feed = BacktraderMarketFeed(bridge=mock_bridge)

    # Spy on the internal translator to ensure the guard blocks execution completely
    feed._translate_to_market_context = MagicMock()

    # Executing the un-guarded production code right now MUST FAIL this test
    # either by reaching the real code or raising StopIteration prematurely.
    with pytest.raises(StopIteration):
        _ = next(feed)

    mock_bridge.advance_time.assert_called_once()
    feed._translate_to_market_context.assert_not_called()

# -----------------------------------------------------------------------------

def test_backtrader_market_feed_termination_guard() -> None:
    """Verifies that next raises StopIteration immediately upon simulation end."""
    mock_bridge = MagicMock(spec=BacktraderBridge)
    mock_bridge.is_simulation_completed.return_value = True

    feed = BacktraderMarketFeed(bridge=mock_bridge)

    with pytest.raises(StopIteration):
        _ = next(feed)

    mock_bridge.advance_time.assert_not_called()

# -----------------------------------------------------------------------------

def test_backtrader_market_feed_translation_logic() -> None:
    """Verifies the mathematical extraction and parsing of Backtrader fields."""
    mock_bridge = MagicMock(spec=BacktraderBridge)
    feed = BacktraderMarketFeed(bridge=mock_bridge)

    fake_time = datetime(2026, 8, 1, 12, 0)
    mock_raw_data = MagicMock()
    mock_raw_data.datetime.datetime.return_value = fake_time
    mock_raw_data.close = [1.1200]
    mock_raw_data.volume = [5000.0]

    context = feed._translate_to_market_context(mock_raw_data)

    assert isinstance(context, MarketContext)
    assert isinstance(context.prices, MarketPricePoint)
    assert context.prices.timestamp == fake_time
    assert context.prices.mid_price == 1.1200
    assert context.prices.bid == 1.1200
    assert context.prices.ask == 1.1200
    assert context.prices.current_atr == 0.0
    assert context.prices.is_night_tariff is False
    assert context.volume == 5000.0

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
