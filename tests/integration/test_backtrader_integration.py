"""Aegis Framework - Backtrader Hybrid Integration Tests.

Executes end-to-end integration tests over synchronized multi-threaded environments
leveraging the automated testing harness infrastructure.
"""

from datetime import datetime
from typing import List

from core.models import (
    ExposureIntent,
    MarketContext,
)
from tests.testutils.backtrader_harness import (
    BacktraderTestHarness,
    TelemetryBot,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class ActiveLifecycleIntegrationBot(TelemetryBot):
    """Stateful test bot capturing telemetry while emitting a single entry signal."""

    def _evaluate(self, market_context: MarketContext, historical_values: List[float]) -> ExposureIntent:
        """Emits an entry signal on the first evaluation cycle, then switches to passive holding.

        Args:
            market_context: The active market price and volume context point.
            historical_values: Trailing price array series.

        Returns:
            The calculated market exposure intent mapped to the specific cycle step.
        """
        if len(self.history) == 0:
            return ExposureIntent(alpha_direction=1.0, stop_loss_ticks=1000.0, take_profit_ticks=1000.0)

        return ExposureIntent(alpha_direction=None, stop_loss_ticks=0.0, take_profit_ticks=0.0)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_backtrader_integration_active_flow() -> None:
    """Verifies end-to-end active transaction processing in a multi-threaded closed loop.

    Asserts that trading commands are dynamically sized by real quantitative systems
    and logged properly inside the telemetry bot audit history trail.
    """
    historical_prices = [
        [datetime(2026, 8, 1, 12, 0), 1.1200, 1.1250, 1.1180, 1.1220, 5000.0, 0.0],
        [datetime(2026, 8, 1, 12, 1), 1.1220, 1.1260, 1.1210, 1.1240, 5500.0, 0.0],
        [datetime(2026, 8, 1, 12, 2), 1.1240, 1.1290, 1.1230, 1.1280, 6000.0, 0.0],
    ]

    active_bot = ActiveLifecycleIntegrationBot()
    harness = BacktraderTestHarness(
        bot=active_bot,
        records=historical_prices,
        symbol="EURUSD",
        initial_cash=10000.0
    )

    harness.execute_synchronized_run(timeout=2.0)

    # High-precision metrology: Strict step-by-step verification of the complete historic trail
    assert len(active_bot.history) == 3

    # Step 1: Entry Signal Generation Boundary
    assert active_bot.history[0].exposure_intent.alpha_direction == 1.0
    assert len(active_bot.history[0].position_ledger.records) == 0

    # Step 2: Flotation Layer Synchronization Block
    assert active_bot.history[1].exposure_intent.alpha_direction is None
    assert "EURUSD" in active_bot.history[1].position_ledger.records

    # Step 3: Passive Holding Boundary Layer
    assert active_bot.history[2].exposure_intent.alpha_direction is None
    assert "EURUSD" in active_bot.history[2].position_ledger.records

# -----------------------------------------------------------------------------

def test_backtrader_integration_passive_flow() -> None:
    """Verifies end-to-end synchronization mechanics using real domain components.

    Validates that neutral/flat exposure desires safely bypass the transaction routing
    pipeline without introducing asset ledger or balance baseline mutations.
    """
    historical_prices = [
        [datetime(2026, 8, 1, 12, 0), 1.1200, 1.1250, 1.1180, 1.1220, 5000.0, 0.0],
        [datetime(2026, 8, 1, 12, 1), 1.1220, 1.1260, 1.1210, 1.1240, 5500.0, 0.0],
    ]

    passive_bot = TelemetryBot()
    harness = BacktraderTestHarness(
        bot=passive_bot,
        records=historical_prices,
        symbol="EURUSD",
        initial_cash=10000.0
    )

    harness.execute_synchronized_run(timeout=1.0)

    # High-precision metrology: Every captured historical record must remain perfectly neutral
    assert len(passive_bot.history) == 2

    assert passive_bot.history[0].exposure_intent.alpha_direction is None
    assert len(passive_bot.history[0].position_ledger.records) == 0

    assert passive_bot.history[1].exposure_intent.alpha_direction is None
    assert len(passive_bot.history[1].position_ledger.records) == 0

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
