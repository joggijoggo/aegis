"""Aegis Framework - Backtrader Strategy Bridge Integration Tests.

Verifies timeline synchronization, sliding history ingestion, and warm-up loops.
"""

from datetime import datetime
from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock

import backtrader as bt
import pandas as pd

from core.models import InstrumentSpecification
from core.models import MarketPricePoint
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
    # This import will raise a ModuleNotFoundError in Phase RED
    from brokers.backtrader_strategy_bridge import BacktraderStrategyBridge

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

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
