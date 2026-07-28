"""Aegis Framework - Backtrader Strategy Bridge Integration Tests.

Verifies timeline synchronization, sliding history ingestion, and warm-up loops.
"""

from datetime import datetime
from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock

import backtrader as bt
import pandas as pd

from brokers.backtrader_strategy_bridge import BacktraderStrategyBridge
from core.models import InstrumentSpecification
from core.models import MarketPricePoint
from core.models import OrderStatus
from core.models import TransactionSide
from strategies.base_strategy import AbstractStrategy

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class MockAegisBot(AbstractStrategy):
    """Minimal evaluation bot to verify bridge data feeding parameters."""

    def __init__(self, broker_bridge: Any = None, warm_up_bars: int = 10):
        """Initializes structural tracking indicators for data validation loops."""
        super().__init__(
            broker_bridge=broker_bridge,
            warm_up_bars=warm_up_bars,
        )
        self.bars_count = 0
        self.last_received_price = 0.0

# -----------------------------------------------------------------------------

    def _on_bar_close(
        self,
        asset: str,
        price_snapshot: MarketPricePoint,
        historical_closes: list[float]
    ) -> None:
        """Captures historical inputs stream parameters for assertions."""
        self.bars_count += 1
        self.last_received_price = price_snapshot.mid_price

# -----------------------------------------------------------------------------

def test_backtrader_bridge_feeds_warm_up_and_triggers_strategy():
    """Validates that the bridge converts Backtrader bars to Aegis structures."""
    # 1. Create a 15-bar continuous pandas dataframe feed to simulate history
    timestamps = [datetime(2026, 3, 25, 12, 0) + timedelta(minutes=i) for i in range(15)]
    data = {
        "open": [1.1000] * 15,
        "high": [1.1010] * 15,
        "low": [1.0990] * 15,
        "close": [1.1000 + (i * 0.0001) for i in range(15)],
        "volume": [1000] * 15,
    }
    df = pd.DataFrame(data, index=timestamps)
    data_feed = bt.feeds.PandasData(dataname=df)

    # 2. Instantiate Cerebro engine and mount the architectural components
    cerebro = bt.Cerebro()
    cerebro.adddata(data_feed)

    # 3. Instantiate a fake broker carrying our asset specs configuration
    mock_initial_broker = MagicMock()
    registry = {"EURUSD": InstrumentSpecification(pip_size=0.0001, lot_size=100000)}
    mock_initial_broker._instrument_specs = registry

    # 4. Instantiate our target Aegis bot enforcing a 10-bar warm-up boundary
    bot = MockAegisBot(broker_bridge=mock_initial_broker, warm_up_bars=10)

    # 5. Inject the bridge strategy linking Cerebro to our target bot
    cerebro.addstrategy(BacktraderStrategyBridge, aegis_bot=bot)
    cerebro.run()

    # 6. Assert lifecycle status validations parameters
    # Total bars: 15. Warm-up requirement: 10.
    # The strategy must be bypassed for the first 9 bars, executing exactly 6 times.
    assert bot.is_warmed_up is True
    assert bot.bars_count == 6

    # Verify accurate mathematical mapping of terminal baseline price
    # Bar 15 close index value: 1.1000 + (14 * 0.0001) = 1.1014
    assert round(bot.last_received_price, 4) == 1.1014

# -----------------------------------------------------------------------------

def test_backtrader_bridge_captures_order_lifecycle():
    """Validates that the bridge intercepts and routes asynchrone order states."""
    timestamps = [datetime(2026, 3, 25, 12, 0) + timedelta(minutes=i) for i in range(2)]
    data = {
        "open": [1.1000] * 2,
        "high": [1.1010] * 2,
        "low": [1.0990] * 2,
        "close": [1.1000] * 2,
        "volume": [1000] * 2,
    }
    df = pd.DataFrame(data, index=timestamps)
    data_feed = bt.feeds.PandasData(dataname=df)

    cerebro = bt.Cerebro()
    cerebro.adddata(data_feed)

    mock_initial_broker = MagicMock()
    registry = {"EURUSD": InstrumentSpecification(pip_size=0.0001, lot_size=100000)}
    mock_initial_broker._instrument_specs = registry

    bot = MockAegisBot(broker_bridge=mock_initial_broker, warm_up_bars=1)

    cerebro.addstrategy(BacktraderStrategyBridge, aegis_bot=bot)
    strategies = cerebro.run()
    active_bridge = strategies[0]

    # 1. Simulate the completion of a long bracket buy order (LONG)
    mock_order_completed = MagicMock()
    mock_order_completed.ref = 42
    mock_order_completed.status = bt.Order.Completed
    mock_order_completed.isbuy.return_value = True
    mock_order_completed.executed.price = 1.1025
    mock_order_completed.executed.size = 100000

    active_bridge.notify_order(mock_order_completed)
    assert len(bot.order_events) == 1
    first_event = bot.order_events[0]
    assert first_event.order_id == 42
    assert first_event.status == OrderStatus.COMPLETED
    assert first_event.side == TransactionSide.LONG
    assert first_event.executed_price == 1.1025
    assert first_event.executed_size == 100000

    # 2. Simulate the rejection of a short bracket sell order (SHORT)
    mock_order_rejected = MagicMock()
    mock_order_rejected.ref = 43
    mock_order_rejected.status = bt.Order.Rejected
    mock_order_rejected.isbuy.return_value = False
    mock_order_rejected.executed.size = 0

    active_bridge.notify_order(mock_order_rejected)
    assert len(bot.order_events) == 2
    second_event = bot.order_events[1]
    assert second_event.order_id == 43
    assert second_event.status == OrderStatus.REJECTED
    assert second_event.side == TransactionSide.SHORT

    # 3. Simulate a transient order status (Submitted) which must be ignored
    mock_order_transient = MagicMock()
    mock_order_transient.status = bt.Order.Submitted

    active_bridge.notify_order(mock_order_transient)
    assert len(bot.order_events) == 2

# -----------------------------------------------------------------------------

def test_backtrader_bridge_captures_trade_closure():
    """Validates that the bridge intercepts closed positions performance metrics."""
    timestamps = [datetime(2026, 3, 25, 12, 0) + timedelta(minutes=i) for i in range(2)]
    data = {
        "open": [1.1000] * 2,
        "high": [1.1010] * 2,
        "low": [1.0990] * 2,
        "close": [1.1000] * 2,
        "volume": [1000] * 2,
    }
    df = pd.DataFrame(data, index=timestamps)
    data_feed = bt.feeds.PandasData(dataname=df)

    cerebro = bt.Cerebro()
    cerebro.adddata(data_feed)

    mock_initial_broker = MagicMock()
    registry = {"EURUSD": InstrumentSpecification(pip_size=0.0001, lot_size=100000)}
    mock_initial_broker._instrument_specs = registry

    bot = MockAegisBot(broker_bridge=mock_initial_broker, warm_up_bars=1)

    cerebro.addstrategy(BacktraderStrategyBridge, aegis_bot=bot)
    strategies = cerebro.run()
    active_bridge = strategies[0]

    # 1. Simulate a closed trade event matching core specifications parameters
    mock_trade = MagicMock()
    mock_trade.isclosed = True
    mock_trade.pnlnotcomm = 150.0
    mock_trade.pnl = 145.0
    mock_trade.commission = 5.0
    mock_trade.barlen = 4

    t_entry = datetime(2026, 3, 25, 12, 0)
    t_exit = datetime(2026, 3, 25, 12, 4)
    mock_trade.dtopen = bt.date2num(t_entry)
    mock_trade.dtclose = bt.date2num(t_exit)

    active_bridge.notify_trade(mock_trade)

    # Assertions checking that the custom structure is properly populated
    assert len(bot.position_close_events) == 1
    close_event = bot.position_close_events[0]
    assert close_event.symbol == "EURUSD"
    assert close_event.side == TransactionSide.LONG
    assert close_event.pnl_gross == 150.0
    assert close_event.pnl_net == 145.0
    assert close_event.commission == 5.0
    assert close_event.bars_duration == 4
    assert close_event.entry_timestamp == t_entry
    assert close_event.exit_timestamp == t_exit

    # 2. Simulate a transient open trade event which must be ignored
    mock_trade_open = MagicMock()
    mock_trade_open.isclosed = False

    active_bridge.notify_trade(mock_trade_open)
    assert len(bot.position_close_events) == 1

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
