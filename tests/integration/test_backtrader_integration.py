"""Aegis Framework - Backtrader Hybrid Integration Tests.

Executes end-to-end integration tests over synchronized multi-threaded environments.
"""

from datetime import datetime
from decimal import Decimal
import threading
from unittest.mock import MagicMock

import backtrader as bt

from bots.base_bot import BaseBot
from broker_adapters.backtrader_bridge import BacktraderBridge
from broker_adapters.backtrader_broker_adapter import BacktraderBrokerAdapter
from broker_adapters.backtrader_proxy_strategy import BacktraderProxyStrategy
from core.contract_registry import ContractRegistry
from core.currency_converter import CurrencyConverter
from core.execution_engine import AegisExecutionEngine
from core.models import (
    ExposureIntent,
    MarketContext,
)
from core.position_sizer import PositionSizer
from market_feeds.backtrader_market_feed import BacktraderMarketFeed
from tests.testutils import create_contract_specification_factory
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

class ActiveStatefulFakeBot(BaseBot):
    """Stateful fake bot emitting a single long signal then turning passive."""

    def __init__(self, warm_up: int = 0) -> None:
        """Initializes the tracking state flag and warm-up requirements."""
        self._signal_emitted = False
        self._warm_up_period = warm_up

    def evaluate(self, market_context: MarketContext, historical_values: list[float]) -> ExposureIntent:
        """Emits an entry signal on the first tick, then switches to passive holding."""
        if not self._signal_emitted:
            self._signal_emitted = True
            return ExposureIntent(alpha_direction=1.0, stop_loss_ticks=10.0, take_profit_ticks=20.0)

        # Maintain passive holding state for the rest of the simulation stream
        return ExposureIntent(alpha_direction=None, stop_loss_ticks=0.0, take_profit_ticks=0.0)

    @property
    def warm_up_period(self) -> int:
        """Gets the minimum data length boundary required for strategy evaluation."""
        return self._warm_up_period

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_backtrader_integration_active_flow() -> None:
    """Verifies end-to-end active transaction processing in a multi-threaded closed loop."""
    cerebro = bt.Cerebro()
    bridge = BacktraderBridge()

    # Bind the proxy strategy infrastructure to the synchronized bridge
    cerebro.addstrategy(BacktraderProxyStrategy, bridge=bridge)

    # Use our pandas-free memory feed to supply market ticks
    memory_feed = PureMemoryDataFeed()
    cerebro.adddata(memory_feed, name='EURUSD')

    # Instantiate our stateful bot to prevent order spamming
    active_bot = ActiveStatefulFakeBot(warm_up=0)
    broker_adapter = BacktraderBrokerAdapter(bridge=bridge)

    # Enforce EURUSD specification tracking inside the registry
    contract_spec = create_contract_specification_factory(symbol='EURUSD')
    contract_registry = ContractRegistry(specifications={'EURUSD': contract_spec})

    # Setup a working currency converter locked to parity
    currency_converter = CurrencyConverter()
    currency_converter.update_rate(pair='EURUSD', rate=Decimal('1.00'))
    currency_converter.update_rate(pair='USDEUR', rate=Decimal('1.00'))

    # Instantiate the real position sizer configured natively with the execution policy
    # demanded by the Backtrader microstructure boundary layer, preventing patching debt.
    position_sizer = PositionSizer(currency_converter=currency_converter)

    # Instantiate the complete orchestration layer
    engine = AegisExecutionEngine(
        bot=active_bot,
        broker_adapter=broker_adapter,
        contract_registry=contract_registry,
        position_sizer=position_sizer,
    )
    market_feed = BacktraderMarketFeed(bridge=bridge)

    def run_backtrader_infrastructure() -> None:
        """Runs the Cerebro historical execution loop inside the background thread."""
        cerebro.run()

    def run_engine_domain() -> None:
        """Runs the main Aegis domain execution loop inside the foreground thread."""
        try:
            engine.run_execution_cycle(symbol='EURUSD', market_feed=market_feed)
        except Exception:
            # Prevent deadlocks by unblocking the synchronization bridges on early failure
            bridge.stop_simulation()
            raise

    # Enforce background daemon states to protect the environment against test freezes
    infra_thread = threading.Thread(target=run_backtrader_infrastructure, daemon=True)
    domain_thread = threading.Thread(target=run_engine_domain, daemon=True)

    try:
        infra_thread.start()
        domain_thread.start()

        # Allow sufficient temporal tolerance for threads to execute and exit safely
        infra_thread.join(timeout=2.0)
        domain_thread.join(timeout=2.0)
    finally:
        # Final safety clear to unlock threads
        bridge.stop_simulation()

    # Assert accurate state alignment upon successful loop exit
    assert bridge.is_simulation_completed() is True
    assert not infra_thread.is_alive()
    assert not domain_thread.is_alive()

# -----------------------------------------------------------------------------

def test_backtrader_integration_passive_flow() -> None:
    """Verifies end-to-end synchronization mechanics using a pure in-memory data feed."""
    cerebro = bt.Cerebro()
    bridge = BacktraderBridge()

    cerebro.addstrategy(BacktraderProxyStrategy, bridge=bridge)

    memory_feed = PureMemoryDataFeed()
    cerebro.adddata(memory_feed, name='EURUSD')

    # Allocate the passive bot with an explicit flat intent and a valid warm-up period
    flat_intent = ExposureIntent(alpha_direction=None, stop_loss_ticks=0.0, take_profit_ticks=0.0)
    passive_bot = FakeBot(exposure_intent=flat_intent, warm_up=0)
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
