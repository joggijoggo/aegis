"""Aegis Framework - Multi-Threaded Backtrader Test Harness and Memory Feeds.

Provides standardized encapsulation orchestration to drive synchronized execution loops,
completely abstracting core infrastructure instantiation boilerplate.
"""

import threading
from typing import Any, Callable, List, Optional

import backtrader as bt

from broker_adapters.backtrader_bridge import BacktraderBridge
from broker_adapters.backtrader_broker_adapter import BacktraderBrokerAdapter
from broker_adapters.backtrader_proxy_strategy import BacktraderProxyStrategy
from bots.base_bot import BaseBot
from core.contract_registry import ContractRegistry
from core.execution_engine import AegisExecutionEngine
from core.position_sizer import PositionSizer
from market_feeds.backtrader_market_feed import BacktraderMarketFeed
from tests.testutils.factories import (
    create_contract_specification_factory,
    create_position_sizer_factory,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class MemoryDataFeed(bt.feed.DataBase):
    """Static in-memory data feed custom-built from historical pricing matrices."""

# -----------------------------------------------------------------------------

    def __init__(self, records: List[List[Any]]) -> None:
        """Initializes the memory stream with a private historical record cache.

        Args:
            records: Matrix containing sequential OHLCV rows to stream.
        """
        super().__init__()
        self._records = records
        self._iterator = iter(self._records)

# -----------------------------------------------------------------------------

    def _load(self) -> bool:
        """Loads the next sequential row into the Backtrader internal lines matrix.

        Returns:
            True if a row was successfully parsed and loaded, False upon exhaustion.
        """
        try:
            row = next(self._iterator)

            # Law 2 Adaptation: Extract the single datetime object at index 0 for ordinal translation
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

class BacktraderTestHarness:
    """Orchestrates multi-threaded lifecycle loops and fully automates architecture setup."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        bot: BaseBot,
        records: List[List[Any]],
        symbol: str = "EURUSD",
        initial_cash: float = 10000.0,
        commission_scheme: Optional[bt.CommissionInfo] = None,
        position_sizer: Optional[PositionSizer] = None,
    ) -> None:
        """Initializes and completely automates the unified infrastructure boilerplate.

        Args:
            bot: The quantitative trading bot instance undergoing validation.
            records: Matrix containing sequential OHLCV rows to stream.
            symbol: Target financial instrument market identifier.
            initial_cash: Starting baseline cash valuation layer.
            commission_scheme: Optional dynamic leverage or margin specification profile.
            position_sizer: Optional pre-configured risk allocation engine override.
        """
        self.bridge: BacktraderBridge = BacktraderBridge()
        self.cerebro: bt.Cerebro = bt.Cerebro()
        self.symbol: str = symbol

        # 1. Automate Inbound Memory Feed Generation and Infrastructure Registration
        self.data_feed: MemoryDataFeed = MemoryDataFeed(records=records)
        self.cerebro.adddata(self.data_feed, name=self.symbol)
        self.cerebro.broker.setcash(initial_cash)

        if commission_scheme is not None:
            self.cerebro.broker.addcommissioninfo(commission_scheme, name=self.symbol)

        # 2. Automate Lifecycle Capture Interception Binding
        self.cerebro.addstrategy(BacktraderProxyStrategy, bridge=self.bridge)

        # 3. Automate Outbound Adapter Layer Initialization
        self.broker_adapter: BacktraderBrokerAdapter = BacktraderBrokerAdapter(bridge=self.bridge)
        self.market_feed: BacktraderMarketFeed = BacktraderMarketFeed(bridge=self.bridge)

        # 4. Automate ContractRegistry Isolated Pre-Population via testing factories
        contract_spec = create_contract_specification_factory(symbol=self.symbol)
        self.contract_registry: ContractRegistry = ContractRegistry(
            specifications={self.symbol: contract_spec}
        )

        # 5. Automate PositionSizer Resolution using core aligned testing factories
        if position_sizer is None:
            self.position_sizer = create_position_sizer_factory()
        else:
            self.position_sizer = position_sizer

        # 6. Automate Central Execution Engine Orchestration Assembly
        self.engine: AegisExecutionEngine = AegisExecutionEngine(
            bot=bot,
            broker_adapter=self.broker_adapter,
            contract_registry=self.contract_registry,
            position_sizer=self.position_sizer,
        )

        # Pre-bind structural background daemon thread handles
        self._domain_thread: Optional[threading.Thread] = None
        self._infra_thread: Optional[threading.Thread] = None
        self._timeout_tolerance: float = 2.0

# -----------------------------------------------------------------------------

    def _assert_graceful_shutdown(self) -> None:
        """Asserts that both parallel thread processing lines terminated cleanly."""
        assert self.bridge.is_simulation_completed() is True
        if self._infra_thread is not None:
            assert not self._infra_thread.is_alive()
        if self._domain_thread is not None:
            assert not self._domain_thread.is_alive()

# -----------------------------------------------------------------------------

    def _create_domain_worker(self) -> Callable[[], None]:
        """Generates a thread-safe execution closure for the foreground domain loop.

        Returns:
            A zero-argument callable worker targeting execution engine cycles.
        """
        def domain_worker() -> None:
            try:
                self.engine.run_execution_cycle(symbol=self.symbol, market_feed=self.market_feed)
            except Exception:
                self.bridge.stop_simulation()
                raise
        return domain_worker

# -----------------------------------------------------------------------------

    def _create_infra_worker(self) -> Callable[[], None]:
        """Generates an execution closure for the background simulation engine.

        Returns:
            A zero-argument callable worker targeting Cerebro replays.
        """
        def infra_worker() -> None:
            try:
                self.cerebro.run()
            except Exception:
                self.bridge.stop_simulation()
                raise
        return infra_worker

# -----------------------------------------------------------------------------

    def execute_synchronized_run(self, timeout: float | None = None) -> None:
        """Drives both parallel execution streams inside daemonized isolation barriers.

        Blocks execution until both threads terminate or the safety timeout triggers,
        then automatically invokes verification shutdown guards.

        Args:
            timeout: Maximum temporal boundary tolerance allowed before forced abort.
        """
        if timeout is not None:
            self._timeout_tolerance = timeout

        infra_target = self._create_infra_worker()
        domain_target = self._create_domain_worker()

        self._infra_thread = threading.Thread(target=infra_target, daemon=True)
        self._domain_thread = threading.Thread(target=domain_target, daemon=True)

        try:
            self._infra_thread.start()
            self._domain_thread.start()

            self._infra_thread.join(timeout=self._timeout_tolerance)
            self._domain_thread.join(timeout=self._timeout_tolerance)
        finally:
            self.bridge.stop_simulation()

        # Enforce automatic structural shutdown check after threading teardown
        self._assert_graceful_shutdown()

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
