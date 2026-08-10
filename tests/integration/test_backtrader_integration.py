"""Aegis Framework - Backtrader Hybrid Integration Tests.

Executes end-to-end integration tests over synchronized multi-threaded environments
leveraging the automated testing harness infrastructure.
"""

from datetime import datetime
from typing import List

from aegis.core.model import (
    ExposureIntent,
    MarketContext,
)
from tests.testutil.backtrader_harness import (
    BacktraderTestHarness,
    TelemetryBot,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class MultiIntentTestBot(TelemetryBot):
    """Stateful test bot capturing telemry while driving multiple intent."""

# -----------------------------------------------------------------------------

    def __init__(self, exposure_intents: list[ExposureIntent]) -> None:
        """Initializes the active testing instance with its scheduled intent.

        Args:
            expore_intents: The intent to emit at each cycle (can be shorter
                than the whole simulation to stay flat).
        """
        super().__init__()
        self._exposure_intents = exposure_intents

# -----------------------------------------------------------------------------

    def  _evaluate(
        self,
        market_context: MarketContext,
        historical_values: List[float]
    ) -> ExposureIntent:
        """Emits the cycle target intent, then switches to passive holding.

        Args:
            market_context: The active market price and volume context point.
            historical_values: Trailing price array series.

        Returns:
            The scheduled exposure intent, otherwise a neutral passive intent.
        """

        try:
            return self._exposure_intents[len(self.history)]
        except IndexError:
            # Stay flat.
            return ExposureIntent(
                alpha_direction=None,
                stop_loss_ticks=0.0,
                take_profit_ticks=0.0,
            )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def print_history(history, historical_prices = None):

    if historical_prices:
        print('Historical Prices:')
        for price in historical_prices:
            print(f'- {price}')

    print('\n')
    for (cycle, telemetry) in enumerate(history):
        print(f'Cycle # {cycle}')
        print('- ' + str(telemetry.market_context))
        print('- ' + str(telemetry.exposure_intent))
        print('- ' + str(telemetry.account_snapshot))
        print('- ' + str(telemetry.position_ledger))

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_backtrader_integration_active_buy_and_hold() -> None:
    """Scenario 1: Verifies entry execution and continuous flotation holding without bracket interference.

    Asserts that the position remains fully active and un-liquidated across the whole historic trail.
    """
    historical_prices = [
        [datetime(2026, 8, 1, 12, 0), 1.1200, 1.1250, 1.1180, 1.1220, 5000.0, 0.0],
        [datetime(2026, 8, 1, 12, 1), 1.1220, 1.1260, 1.1210, 1.1240, 5500.0, 0.0],
        [datetime(2026, 8, 1, 12, 2), 1.1240, 1.1290, 1.1230, 1.1280, 6000.0, 0.0],
    ]

    intent = ExposureIntent(alpha_direction=1.0, stop_loss_ticks=1000.0, take_profit_ticks=1000.0)
    active_bot = MultiIntentTestBot([intent])
    harness = BacktraderTestHarness(bot=active_bot, records=historical_prices, symbol="EURUSD")
    harness.execute_synchronized_run(timeout=2.0)

    assert len(active_bot.history) == 3

    # Step 1: Order submitted, portfolio flat
    assert len(active_bot.history[0].position_ledger.records) == 0

    # Step 2: Order filled, position is active and floating
    assert "EURUSD" in active_bot.history[1].position_ledger.records

    # Step 3: Continues to hold position cleanly
    assert "EURUSD" in active_bot.history[2].position_ledger.records

# -----------------------------------------------------------------------------

def test_backtrader_integration_bracket_delayed_stop_loss() -> None:
    """Scenario 2: Verifies delayed Stop Loss liquidation at the subsequent cycle."""
    historical_prices = [
        [datetime(2026, 8, 1, 12, 0), 1.1200, 1.1250, 1.1180, 1.1220, 5000.0, 0.0],
        # Open 1.1220, Low 1.1210. Survives a 150-tick stop loss at 1.1205 floor.
        [datetime(2026, 8, 1, 12, 1), 1.1220, 1.1260, 1.1210, 1.1240, 5500.0, 0.0],
        # Next Bar: Low drops to 1.1100, breaching our 1.1205 protective level.
        [datetime(2026, 8, 1, 12, 2), 1.1240, 1.1290, 1.1100, 1.1280, 6000.0, 0.0],
    ]

    intent = ExposureIntent(
        alpha_direction=1.0, stop_loss_ticks=150.0, take_profit_ticks=1000.0
    )
    active_bot = MultiIntentTestBot([intent])
    harness = BacktraderTestHarness(
        bot=active_bot, records=historical_prices, symbol="EURUSD"
    )
    harness.execute_synchronized_run(timeout=2.0)

    assert len(active_bot.history) == 3

    # Cycle # 0: Entry order submitted, portfolio flat
    assert len(active_bot.history[0].position_ledger.records) == 0

    # Cycle # 1: Position survives the first bar and floats actively at 50.0 lots
    assert "EURUSD" in active_bot.history[1].position_ledger.records

    # Cycle # 2: Next bar low breach triggers liquidation. Ledger returns to flat.
    assert len(active_bot.history[2].position_ledger.records) == 0

# -----------------------------------------------------------------------------

def test_backtrader_integration_bracket_delayed_take_profit() -> None:
    """Scenario 3: Verifies delayed Take Profit liquidation at the subsequent cycle."""
    historical_prices = [
        [datetime(2026, 8, 1, 12, 0), 1.1200, 1.1250, 1.1180, 1.1220, 5000.0, 0.0],
        # Open 1.1220, High 1.1260. Survives a 500-tick take profit target at 1.1270.
        [datetime(2026, 8, 1, 12, 1), 1.1220, 1.1260, 1.1210, 1.1240, 5500.0, 0.0],
        # Next Bar: High stretches to 1.1290, capturing our 1.1270 profit target.
        [datetime(2026, 8, 1, 12, 2), 1.1240, 1.1290, 1.1230, 1.1280, 6000.0, 0.0],
    ]

    intent = ExposureIntent(
        alpha_direction=1.0, stop_loss_ticks=1000.0, take_profit_ticks=500.0
    )
    active_bot = MultiIntentTestBot([intent])
    harness = BacktraderTestHarness(
        bot=active_bot, records=historical_prices, symbol="EURUSD"
    )
    harness.execute_synchronized_run(timeout=2.0)

    assert len(active_bot.history) == 3

    # Cycle # 0: Entry order submitted, portfolio flat
    assert len(active_bot.history[0].position_ledger.records) == 0

    # Cycle # 1: Position survives the first bar and floats actively at 50.0 lots
    assert "EURUSD" in active_bot.history[1].position_ledger.records

    # Cycle # 2: Next bar high stretch hits the target line -> Liquidated back to flat
    assert len(active_bot.history[2].position_ledger.records) == 0

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
