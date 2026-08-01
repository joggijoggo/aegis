"""Aegis Framework - Backtrader Market Feed Component Tests.

Validates the iteration lifecycles and nominal termination guards of the feed adapter.
"""

from unittest.mock import MagicMock

import pytest

from broker_adapters.backtrader_bridge import BacktraderBridge
from core.models import MarketContext
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

    # Mock the internal translation stub for this sub-milestone
    feed._translate_to_market_context = MagicMock(return_value=mock_context)

    context = next(feed)

    assert context is mock_context
    mock_bridge.advance_time.assert_called_once()
    feed._translate_to_market_context.assert_called_once_with('raw_tick_payload')

# -----------------------------------------------------------------------------

def test_backtrader_market_feed_termination_guard() -> None:
    """Verifies that next raises StopIteration immediately upon simulation end."""
    mock_bridge = MagicMock(spec=BacktraderBridge)
    mock_bridge.is_simulation_completed.return_value = True

    feed = BacktraderMarketFeed(bridge=mock_bridge)

    with pytest.raises(StopIteration):
        _ = next(feed)

    mock_bridge.advance_time.assert_not_called()

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
