"""Aegis Framework - Backtrader End-to-End Integration Tests.

Validates full loop execution from data ingestion to absolute order settlement.
"""

from datetime import datetime
from datetime import timedelta
from typing import Any

import backtrader as bt
import pandas as pd
import pytest

from brokers.backtrader_adapter import BacktraderBrokerAdapter
from brokers.backtrader_strategy_bridge import BacktraderStrategyBridge
from core.models import OrderStatus
from core.models import OrderType
from core.models import TransactionSide
from core.models import MarketPricePoint
from strategies.base_strategy import AbstractStrategy
from tests.test_constants import TEST_REGISTRY

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class IntegrationMeanReversionBot(AbstractStrategy):
    """Production grade R&D evaluation bot triggering real OCO bracket loops."""

    def __init__(self, broker_bridge: Any = None, warm_up_bars: int = 15):
        """Initializes strategic decision variables and thresholds parameters."""
        super().__init__(
            broker_bridge=broker_bridge,
            warm_up_bars=warm_up_bars,
        )
        self.trade_executed = False

# -----------------------------------------------------------------------------

    def _on_bar_close(
        self,
        asset: str,
        price_snapshot: MarketPricePoint,
        historical_closes: list[float]
    ) -> None:
        """Evaluates thresholds to trigger real absolute execution entries."""
        current_close = historical_closes[-1]

        if len(historical_closes) == 20 and not self.trade_executed:
            self.place_bracket_order(
                symbol=asset,
                side=TransactionSide.LONG,
                order_type=OrderType.MARKET,
                volume_lots=1.0,
                current_price=current_close,
                stop_loss_ticks=20.0,
                take_profit_ticks=40.0,
            )
            self.trade_executed = True

# -----------------------------------------------------------------------------

def test_backtrader_cerebro_loop_e2e_execution():
    """Validates that a bot executes an entire backtest cycle through Cerebro."""
    timestamps = [datetime(2026, 3, 25, 12, 0) + timedelta(minutes=i) for i in range(30)]
    data = {
        "open": [1.1000] * 30,
        "high": [1.1050] * 25 + [1.1150] * 5,
        "low": [1.0950] * 30,
        "close": [1.1000] * 19 + [1.1000] + [1.1000] * 5 + [1.1100] * 5,
        "volume": [1000] * 30,
        "atr": [0.0010] * 30,
    }
    df = pd.DataFrame(data, index=timestamps)

    class PandasDataWithATR(bt.feeds.PandasData):
        lines = ('atr',)
        params = (('atr', -1),)

    data_feed = PandasDataWithATR(dataname=df, name="EURUSD")

    cerebro = bt.Cerebro()
    cerebro.adddata(data_feed)
    cerebro.broker.setcash(10000000.0)

    production_broker = BacktraderBrokerAdapter(
        instrument_registry=TEST_REGISTRY,
    )

    bot = IntegrationMeanReversionBot(
        broker_bridge=production_broker,
        warm_up_bars=15,
    )

    cerebro.addstrategy(
        BacktraderStrategyBridge,
        aegis_bot=bot,
        instrument_registry=TEST_REGISTRY,
    )

    cerebro.run()

    assert bot.is_warmed_up is True
    assert bot.trade_executed is True

    assert len(bot.order_events) > 0
    completed_orders = [e for e in bot.order_events if e.status == OrderStatus.COMPLETED]
    assert len(completed_orders) >= 1

    first_execution = completed_orders[0]
    assert first_execution.symbol == "EURUSD"
    assert first_execution.side == TransactionSide.LONG
    assert first_execution.executed_size == 100000

    with pytest.raises(ValueError, match="is missing from central instrument registry"):
        production_broker.get_instrument_specification("UNKNOWN")

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
