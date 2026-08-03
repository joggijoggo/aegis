"""Aegis Framework - Backtrader Hybrid Integration Tests.

Executes end-to-end integration tests over synchronized multi-threaded environments
leveraging the automated testing harness infrastructure.
"""

from datetime import datetime
from typing import List

from bots.base_bot import BaseBot
from core.models import (
    ExposureIntent,
    MarketContext,
)
from tests.testutils.backtrader_harness import BacktraderTestHarness
from tests.testutils.mocks import FakeBot

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class ActiveStatefulFakeBot(BaseBot):
    """Stateful fake bot emitting a single long signal then turning passive."""

    def __init__(self, warm_up: int = 0) -> None:
        """Initializes the tracking state flag and warm-up requirements.

        Args:
            warm_up: Minimum data length required before evaluation.
        """
        self._signal_emitted = False
        self._warm_up_period = warm_up

# -----------------------------------------------------------------------------

    def evaluate(self, market_context: MarketContext, historical_values: List[float]) -> ExposureIntent:
        """Emits an entry signal on the first tick, then switches to passive holding.

        Args:
            market_context: The current market state context.
            historical_values: Trailing price series.

        Returns:
            The calculated market exposure intent.
        """
        if not self._signal_emitted:
            self._signal_emitted = True
            return ExposureIntent(alpha_direction=1.0, stop_loss_ticks=10.0, take_profit_ticks=20.0)

        return ExposureIntent(alpha_direction=None, stop_loss_ticks=0.0, take_profit_ticks=0.0)

# -----------------------------------------------------------------------------

    @property
    def warm_up_period(self) -> int:
        """Gets the minimum data length boundary required for strategy evaluation.

        Returns:
            The minimum number of historical elements required.
        """
        return self._warm_up_period

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_backtrader_integration_active_flow() -> None:
    """Verifies end-to-end active transaction processing in a multi-threaded closed loop.

    Asserts that trading commands are dynamically sized by real quantitative systems
    and routed cleanly to Cerebro matching layers through the bridge.
    """
    # 1. Supply raw historical pricing matrix variables
    historical_prices = [
        [datetime(2026, 8, 1, 12, 0), 1.1200, 1.1250, 1.1180, 1.1220, 5000.0, 0.0],
        [datetime(2026, 8, 1, 12, 1), 1.1220, 1.1260, 1.1210, 1.1240, 5500.0, 0.0],
        [datetime(2026, 8, 1, 12, 2), 1.1240, 1.1290, 1.1230, 1.1280, 6000.0, 0.0],
    ]

    active_bot = ActiveStatefulFakeBot(warm_up=0)

    # 2. Instantiate the container harness (Boilerplate and PositionSizer factories run natively)
    harness = BacktraderTestHarness(
        bot=active_bot,
        records=historical_prices,
        symbol='EURUSD',
        initial_cash=10000.0
    )

    # 3. Launch synchronized processing loop (Triggers automatic internal shutdown assertions)
    harness.execute_synchronized_run(timeout=2.0)

# -----------------------------------------------------------------------------

def test_backtrader_integration_passive_flow() -> None:
    """Verifies end-to-end synchronization mechanics using real domain components.

    Validates that neutral/flat exposure desires safely bypass the transaction routing
    pipeline without introducing asset ledger mutations.
    """
    # 1. Supply raw historical pricing matrix variables
    historical_prices = [
        [datetime(2026, 8, 1, 12, 0), 1.1200, 1.1250, 1.1180, 1.1220, 5000.0, 0.0],
        [datetime(2026, 8, 1, 12, 1), 1.1220, 1.1260, 1.1210, 1.1240, 5500.0, 0.0],
    ]

    flat_intent = ExposureIntent(alpha_direction=None, stop_loss_ticks=0.0, take_profit_ticks=0.0)
    passive_bot = FakeBot(exposure_intent=flat_intent, warm_up=0)

    # 2. Configure the automated harness
    harness = BacktraderTestHarness(
        bot=passive_bot,
        records=historical_prices,
        symbol='EURUSD',
        initial_cash=10000.0
    )

    # 3. Run multi-threaded isolation stream
    harness.execute_synchronized_run(timeout=1.0)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
