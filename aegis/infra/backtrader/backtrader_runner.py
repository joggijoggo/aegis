"""Aegis Framework - Backtrader Infrastructure Runner.

Provides the structural isolation layer to orchestrate the lifecycle
and multi-threaded synchronization of a Backtrader-driven backtest simulation.
"""

from threading import Thread
from typing import Callable
import logging

import backtrader as bt

from aegis.core.base import BaseBot
from aegis.core.contract_registry import ContractRegistry
from aegis.core.execution_engine import AegisExecutionEngine
from aegis.core.model import ContractSpecification
from aegis.core.position_sizer import PositionSizer
from aegis.core.telemetry import TelemetryEmitter
from aegis.infra.backtrader import (
    BacktraderBridge,
    BacktraderBrokerAdapter,
    BacktraderMarketFeed,
    BacktraderProxyStrategy,
)

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class BacktraderRunner(TelemetryEmitter):
    """Orchestrates multi-threaded data execution and infrastructure setup."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        bot: BaseBot,
        data_feed: bt.feed.DataBase,
        position_sizer: PositionSizer,
        contract_specification: ContractSpecification,
        initial_cash: float = 10000.0,
        commission_scheme: bt.CommissionInfo | None = None,
    ):
        """Initializes and completely automates the unified infrastructure boilerplate.

        Args:
            bot: The trading bot instance undergoing validation.
            data_feed: The Backtrader-compatible market data feed source.
            position_sizer: Component managing position sizing logic.
            contract_specification: Specifications detailing the target asset contract.
            initial_cash: Starting virtual capital balance. Defaults to 10000.0.
            commission_scheme: Optional commission and fee model configuration.
        """
        super().__init__()

        self._symbol = contract_specification.symbol

        self._bridge: BacktraderBridge = BacktraderBridge()
        self._bridge.register_listener(self.emit)

        self._market_feed = BacktraderMarketFeed(bridge=self._bridge)
        self._broker_adapter = BacktraderBrokerAdapter(bridge=self._bridge)

        self._cerebro: bt.Cerebro = bt.Cerebro()
        self._cerebro.adddata(data_feed, self._symbol)
        self._cerebro.broker.setcash(initial_cash)
        self._cerebro.addstrategy(BacktraderProxyStrategy, bridge=self._bridge)

        if commission_scheme is not None:
            self._cerebro.broker.addcommissioninfo(
                commission_scheme,
                name=self._symbol,
            )

        contract_registry = ContractRegistry(
            specifications={self._symbol: contract_specification},
        )

        self._engine = AegisExecutionEngine(
            bot=bot,
            broker_adapter=self._broker_adapter,
            contract_registry=contract_registry,
            position_sizer=position_sizer,
        )

        # Pre-bind structural background daemon thread handles
        self._domain_thread: Thread | None = None
        self._infra_thread: Thread | None = None

# -----------------------------------------------------------------------------

    def _assert_graceful_shutdown(self) -> None:
        """Asserts that both parallel thread processing lines terminated cleanly."""
        assert self._bridge.is_simulation_completed() is True
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
                self._engine.run_execution_cycle(
                    symbol=self._symbol,
                    market_feed=self._market_feed,
                )
            except Exception:
                self._bridge.stop_simulation()
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
                self._cerebro.run()
            except Exception:
                self._bridge.stop_simulation()
                raise
        return infra_worker

# -----------------------------------------------------------------------------

    # Needed for bot late binding in test runner.
    def _get_broker_adapter(self) -> BacktraderBrokerAdapter:
        """Returns the Backtrader broker adapter."""
        return self._broker_adapter

# -----------------------------------------------------------------------------

    def run(self, timeout: float | None = None) -> None:
        """Drives both parallel execution streams inside daemonized isolation barriers.

        Blocks execution until both threads terminate or the safety timeout triggers.

        Args:
            timeout: Maximum temporal boundary tolerance allowed before forced abort.
        """
        logger.info('Initializing workers...')

        infra_target = self._create_infra_worker()
        domain_target = self._create_domain_worker()

        self._infra_thread = Thread(target=infra_target, daemon=True, name='INFRA')
        self._domain_thread = Thread(target=domain_target, daemon=True, name='MAIN')

        logger.info('Starting run...')

        try:
            self._infra_thread.start()
            self._domain_thread.start()

            self._infra_thread.join(timeout=timeout)
            self._domain_thread.join(timeout=timeout)
        finally:
            self._bridge.stop_simulation()

        # Enforce automatic structural shutdown check after threading teardown
        self._assert_graceful_shutdown()

        logger.info('Run completed')

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
