"""Aegis Framework - Backtrader Hybrid Integration Tests.

Executes end-to-end integration tests over synchronized multi-threaded environments.
"""

from datetime import datetime
import threading
from unittest.mock import MagicMock

import backtrader as bt

from broker_adapters.backtrader_bridge import BacktraderBridge
from broker_adapters.backtrader_broker_adapter import BacktraderBrokerAdapter
from broker_adapters.backtrader_proxy_strategy import BacktraderProxyStrategy
from core.contract_registry import ContractRegistry
from core.execution_engine import AegisExecutionEngine
from core.position_sizer import PositionSizer
from market_feeds.backtrader_market_feed import BacktraderMarketFeed
from tests.testutils.mocks import FakeBot

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class PureMemoryDataFeed(bt.feed.DataBase):
    """Lightweight in-memory data feed avoiding any external pandas dependency."""

# -----------------------------------------------------------------------------

    def __init__(self) -> None:
        """Initializes the memory stream with sequential historical bar data."""
        super().__init__()
        self._records = [
            [datetime(2026, 8, 1, 12, 0), 1.1200, 1.1250, 1.1180, 1.1220, 5000.0, 0.0],
            [datetime(2026, 8, 1, 12, 1), 1.1220, 1.1260, 1.1210, 1.1240, 5500.0, 0.0],
            [datetime(2026, 8, 1, 12, 2), 1.1240, 1.1290, 1.1230, 1.1280, 6000.0, 0.0],
        ]
        self._iterator = iter(self._records)

# -----------------------------------------------------------------------------

    def _load(self) -> bool:
        """Loads the next sequential row into the Backtrader internal lines matrix."""
        try:
            row = next(self._iterator)

            # Use explicit [0] indexation to mutate the current line buffer slot properly
            self.lines.datetime[0] = bt.date2num(row[0])
            self.lines.open[0] = row[1]
            self.lines.high[0] = row[2]
            self.lines.low[0] = row[3]
            self.lines.close[0] = row[4]
            self.lines.volume[0] = row[5]
            self.lines.openinterest[0] = row[6]

            return True
        except StopIteration:
            return False

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_backtrader_integration_passive_flow() -> None:
    """Verifies end-to-end synchronization mechanics using a pure in-memory data feed."""
    cerebro = bt.Cerebro()
    bridge = BacktraderBridge()

    cerebro.addstrategy(BacktraderProxyStrategy, bridge=bridge)

    memory_feed = PureMemoryDataFeed()
    cerebro.adddata(memory_feed, name='EURUSD')

    passive_bot = FakeBot(warm_up=0)
    broker_adapter = BacktraderBrokerAdapter(bridge=bridge)
    contract_registry = MagicMock(spec=ContractRegistry)
    position_sizer = MagicMock(spec=PositionSizer)

    engine = AegisExecutionEngine(
        bot=passive_bot,
        broker_adapter=broker_adapter,
        contract_registry=contract_registry,
        position_sizer=position_sizer,
    )
    market_feed = BacktraderMarketFeed(bridge=bridge)

    def run_backtrader_infrastructure() -> None:
        """Runs the Cerebro historical engine inside the background thread."""
        cerebro.run()

    def run_engine_domain() -> None:
        """Runs the main Aegis processing loop inside the foreground thread."""
        engine.run_execution_cycle(symbol='EURUSD', market_feed=market_feed)

    # Enforce daemon status to ensure threads are killed immediately if pytest aborts
    infra_thread = threading.Thread(target=run_backtrader_infrastructure, daemon=True)
    domain_thread = threading.Thread(target=run_engine_domain, daemon=True)

    try:
        infra_thread.start()
        domain_thread.start()

        infra_thread.join(timeout=1.0)
        domain_thread.join(timeout=1.0)
    finally:
        # The bridge now natively guarantees internal thread release on shutdown
        bridge.stop_simulation()

    assert bridge.is_simulation_completed() is True
    assert not infra_thread.is_alive()
    assert not domain_thread.is_alive()

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
