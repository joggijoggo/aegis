"""Aegis Framework - Backtrader Proxy Strategy Component Tests.

Validates interception hooks and event forwarding capabilities of the proxy strategy.
"""

from unittest.mock import MagicMock

import backtrader as bt
import pytest

from broker_adapters.backtrader_proxy_strategy import BacktraderProxyStrategy
from core.models.enums import EventType

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_backtrader_proxy_strategy_lifecycle_hooks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that startup and teardown hooks communicate with the bridge."""
    mock_bridge = MagicMock()

    # Safely mock the parent __init__ to eliminate any Backtrader internal side effects
    monkeypatch.setattr(bt.Strategy, '__init__', lambda *a, **kw: None)

    # Bypass MetaStrategy instantiation constraints for unit verification
    strategy = BacktraderProxyStrategy.__new__(BacktraderProxyStrategy)

    # Mock the internal parameter namespace structure of Backtrader
    mock_params = MagicMock()
    mock_params.bridge = mock_bridge
    strategy.p = mock_params

    # Explicitly invoke the constructor to secure 100% test coverage
    BacktraderProxyStrategy.__init__(strategy)
    assert strategy._bridge is mock_bridge

    strategy.start()
    mock_bridge.bind_strategy.assert_called_once_with(strategy)

    strategy.stop()
    mock_bridge.stop_simulation.assert_called_once()

# -----------------------------------------------------------------------------

def test_backtrader_proxy_strategy_market_interception() -> None:
    """Verifies that next data updates are routed as market ticks."""
    mock_bridge = MagicMock()
    strategy = BacktraderProxyStrategy.__new__(BacktraderProxyStrategy)
    strategy._bridge = mock_bridge
    strategy.data = 'fake_ohlcv_stream'

    strategy.next()
    mock_bridge.submit_event.assert_called_once_with(
        EventType.MARKET_TICK,
        'fake_ohlcv_stream',
    )

# -----------------------------------------------------------------------------

def test_backtrader_proxy_strategy_notification_routing() -> None:
    """Verifies that order and trade hooks forward updates to the bridge."""
    mock_bridge = MagicMock()
    strategy = BacktraderProxyStrategy.__new__(BacktraderProxyStrategy)
    strategy._bridge = mock_bridge

    mock_order = MagicMock(spec=bt.Order)
    strategy.notify_order(mock_order)
    mock_bridge.submit_event.assert_any_call(
        EventType.ORDER_NOTIFICATION,
        mock_order,
    )

    mock_trade = MagicMock(spec=bt.Trade)
    strategy.notify_trade(mock_trade)
    mock_bridge.submit_event.assert_any_call(
        EventType.TRADE_NOTIFICATION,
        mock_trade,
    )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
