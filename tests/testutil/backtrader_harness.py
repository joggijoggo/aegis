"""Aegis Framework - Multi-Threaded Backtrader Test Harness and Memory Feeds.

Provides standardized encapsulation orchestration to drive synchronized execution loops,
completely abstracting core infrastructure instantiation boilerplate.
"""

from dataclasses import dataclass
from typing import (
    Any,
    List,
)

import backtrader as bt

from aegis.core.base import BaseBot
from aegis.core.model import (
    AccountSnapshot,
    ExposureIntent,
    MarketContext,
    PositionLedgerSnapshot,
)
from aegis.core.position_sizer import PositionSizer
from aegis.infra.backtrader import (
    BacktraderBrokerAdapter,
    BacktraderRunner,
)
from tests.testutil.factory import (
    create_contract_specification_factory,
    create_position_sizer_factory,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

@dataclass(frozen=True)
class DomainTelemetryRecord:
    """Immutable historic entry capturing complete Aegis state at a single step."""
    account_snapshot: AccountSnapshot
    exposure_intent: ExposureIntent
    market_context: MarketContext
    position_ledger: PositionLedgerSnapshot

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
            # pylint: disable=no-member
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

class TelemetryBot(BaseBot):
    """Stateful testing bot capturing architecture telemetry metrics while driving market intents."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        broker_adapter: BacktraderBrokerAdapter | None = None,
        warm_up: int = 0,
    ) -> None:
        """Initializes the telemetry logger buffer and binds optional adapter dependencies.

        Args:
            broker_adapter: Optional production adapter interface plugged into the harness.
            warm_up: Minimum data length required before evaluation loops.
        """
        super().__init__()
        self._adapter = broker_adapter
        self._warm_up_period = warm_up

        self.history: List[DomainTelemetryRecord] = []

# -----------------------------------------------------------------------------

    def _evaluate(self, market_context: MarketContext, historical_values: List[float]) -> ExposureIntent:
        """Executes the internal strategy decision logic, defaulting to a permanent flat posture.

        This method should be overridden by specific integration test scenarios to control
        active transactional flows.

        Args:
            market_context: The active market price and volume context point.
            historical_values: Trailing price array series.

        Returns:
            A neutral market exposure intent forcing a flat posture loop by default.
        """
        # Stay flat by default.
        return ExposureIntent(alpha_direction=None, stop_loss_ticks=None, take_profit_ticks=None)

# -----------------------------------------------------------------------------

    def evaluate(self, market_context: MarketContext, historical_values: List[float]) -> ExposureIntent:
        """Captures active domain state telemetry internally and routes core strategy calculations.

        Args:
            market_context: The active market price and volume context point.
            historical_values: Trailing price array series.

        Returns:
            The calculated market exposure intent mapped from the internal decision logic.
        """
        if self._adapter is None:
            raise RuntimeError(
                "TelemetryBot execution aborted: The broker_adapter reference was not coupled. "
                "Ensure set_broker_adapter() is invoked before starting the simulation loop."
            )

        broker_snapshot = self._adapter.get_broker_snapshot()

        exposure_intent = self._evaluate(market_context, historical_values)

        self.history.append(
            DomainTelemetryRecord(
                account_snapshot=broker_snapshot.account,
                exposure_intent=exposure_intent,
                market_context=market_context,
                position_ledger=broker_snapshot.position_ledger,
            )
        )
        return exposure_intent

# -----------------------------------------------------------------------------

    def set_broker_adapter(self, broker_adapter: BacktraderBrokerAdapter) -> None:
        """Couples the production broker adapter reference into the telemetry spy bot.

        Args:
            broker_adapter: The active production infrastructure adapter instance.
        """
        self._adapter = broker_adapter

# -----------------------------------------------------------------------------

    @property
    def warm_up_period(self) -> int:
        """Gets the minimum historical data length boundary required for evaluation.

        Returns:
            The minimum data length integer constraint.
        """
        return self._warm_up_period

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class BacktraderTestRunner(BacktraderRunner):
    """Orchestrates multi-threaded data execution and infrastructure setup."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        bot: TelemetryBot,
        records: List[List[Any]],
        symbol: str = 'EURUSD',
        initial_cash: float = 10000.0,
        commission_scheme: bt.CommissionInfo | None = None,
        position_sizer: PositionSizer | None = None,
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
        data_feed = MemoryDataFeed(records=records)
        contract_specification = create_contract_specification_factory(symbol=symbol)

        if position_sizer is None:
            position_sizer = create_position_sizer_factory()

        super().__init__(
            data_feed=data_feed,
            bot=bot,
            initial_cash=initial_cash,
            commission_scheme=commission_scheme,
            position_sizer=position_sizer,
            contract_specification=contract_specification,
        )

        bot.set_broker_adapter(self._get_broker_adapter())

# -----------------------------------------------------------------------------

    def run(self, timeout: float | None = None) -> None:
        if timeout is None:
            timeout = 2.0

        super().run(timeout=timeout)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
