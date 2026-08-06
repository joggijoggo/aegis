"""Aegis Framework - Backtrader Portfolio Confrontation Integration Tests.

Validates zero-drift universal accounting equation matrix across all asset regimes.
All test components and functions are organized in strict alphabetical order.
"""

from datetime import datetime
from decimal import Decimal
from typing import List

import backtrader as bt

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

class PortfolioActiveTestBot(TelemetryBot):
    """Stateful test bot capturing telemetry while driving a controlled lifecycle."""

    def __init__(self, exposure_intent: ExposureIntent) -> None:
        """Initializes the active testing instance with its single scheduled intent."""
        super().__init__()
        self._exposure_intent = exposure_intent

    def _evaluate(
        self, market_context: MarketContext, historical_values: List[float]
    ) -> ExposureIntent:
        """Emits entry on first tick, then maintains bracket bounds sequentially."""
        if len(self.history) == 0:
            return self._exposure_intent

        return ExposureIntent(
            alpha_direction=None,
            stop_loss_ticks=self._exposure_intent.stop_loss_ticks,
            take_profit_ticks=self._exposure_intent.take_profit_ticks,
        )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_portfolio_accounting_forex_dynamic_leverage() -> None:
    """Scenario 1: Audits dynamic gearing automargin leverage accounting metrics."""

    class ForexDynamicLeverageScheme(bt.CommissionInfo):
        """Forex margin scheme with percentage based leverage (Automargin)."""

        params = (
            ("commission", 0.0),
            ("mult", 1.0),
            ("margin", 0.0),
            ("commtype", bt.CommInfoBase.COMM_FIXED),
            ("stocklike", True),
            ("leverage", 50.0),
            ("automargin", 0.02),
            ("interest", 0.0),
            ("interest_long", False),
        )

    historical_prices = [
        [datetime(2026, 8, 1, 12, 0), 1.1200, 1.1250, 1.1180, 1.1220, 5000.0, 0.0],
        [datetime(2026, 8, 1, 12, 1), 1.1220, 1.1235, 1.1210, 1.1225, 5500.0, 0.0],
        # Bar 3: High stretches to 1.1290 to hit the 20-tick take profit line
        [datetime(2026, 8, 1, 12, 2), 1.1225, 1.1290, 1.1210, 1.1280, 6000.0, 0.0],
    ]

    intent = ExposureIntent(
        alpha_direction=1.0, stop_loss_ticks=1000.0, take_profit_ticks=20.0
    )
    active_bot = PortfolioActiveTestBot(exposure_intent=intent)
    harness = BacktraderTestHarness(
        bot=active_bot,
        records=historical_prices,
        symbol="EURUSD",
        initial_cash=10000.0,
        commission_scheme=ForexDynamicLeverageScheme(),
    )
    harness.execute_synchronized_run(timeout=2.0)

    assert len(active_bot.history) == 3

    # Cycle # 1: Active Entry Flotation Phase Validation (0.1 lots dynamic sizing)
    snap_c1 = active_bot.history[1].account_snapshot
    assert snap_c1.available_margin == Decimal("9999.997756")
    assert snap_c1.equity == Decimal("10000.00005")
    assert snap_c1.balance == Decimal("10000.00")

    # Cycle # 2: Next bar triggers the take profit target level -> Flat
    snap_c2 = active_bot.history[2].account_snapshot
    assert len(active_bot.history[2].position_ledger.records) == 0
    assert snap_c2.balance > Decimal("10000.00")

# -----------------------------------------------------------------------------

def test_portfolio_accounting_forex_fixed_margin() -> None:
    """Scenario 2: Audits static lot requirements under forex override traps."""

    class ForexFixedMarginScheme(bt.CommissionInfo):
        """Forex margin scheme with static lot requirements."""

        params = (
            ("commission", 0.0),
            ("mult", 1.0),
            ("margin", 50.0),
            ("commtype", bt.CommInfoBase.COMM_FIXED),
            ("stocklike", True),
            ("leverage", 1.0),
            ("automargin", False),
            ("interest", 0.0),
            ("interest_long", False),
        )

    historical_prices = [
        [datetime(2026, 8, 1, 12, 0), 1.1200, 1.1250, 1.1180, 1.1220, 5000.0, 0.0],
        [datetime(2026, 8, 1, 12, 1), 1.1220, 1.1235, 1.1210, 1.1225, 5500.0, 0.0],
        # Bar 3: High stretches to 1.1290 to hit the 20-tick take profit line
        [datetime(2026, 8, 1, 12, 2), 1.1225, 1.1290, 1.1210, 1.1280, 6000.0, 0.0],
    ]

    intent = ExposureIntent(
        alpha_direction=1.0, stop_loss_ticks=1000.0, take_profit_ticks=20.0
    )
    active_bot = PortfolioActiveTestBot(exposure_intent=intent)
    harness = BacktraderTestHarness(
        bot=active_bot,
        records=historical_prices,
        symbol="EURUSD",
        initial_cash=10000.0,
        commission_scheme=ForexFixedMarginScheme(),
    )
    harness.execute_synchronized_run(timeout=2.0)

    assert len(active_bot.history) == 3

    # Cycle # 1: Active Entry Flotation Phase Validation (0.1 lots spot override)
    snap_c1 = active_bot.history[1].account_snapshot
    assert snap_c1.available_margin == Decimal("9999.8878")
    assert snap_c1.equity == Decimal("10000.00005")
    assert snap_c1.balance == Decimal("10000.00")

    # Cycle # 2: Next bar triggers the take profit target level -> Flat
    snap_c2 = active_bot.history[2].account_snapshot
    assert len(active_bot.history[2].position_ledger.records) == 0
    assert snap_c2.balance > Decimal("10000.00")

# -----------------------------------------------------------------------------

def test_portfolio_accounting_future_fixed_margin() -> None:
    """Scenario 3: Audits future asset schemes applying MTM cash adjustments."""

    class FutureFixedMarginScheme(bt.CommissionInfo):
        """Future scheme with fixed margin requirement and MTM cashadjust."""

        params = (
            ("commission", 0.0),
            ("mult", 1.0),
            ("margin", 50.0),
            ("commtype", bt.CommInfoBase.COMM_FIXED),
            ("stocklike", False),
            ("leverage", 1.0),
            ("automargin", False),
            ("interest", 0.0),
            ("interest_long", False),
        )

    historical_prices = [
        [datetime(2026, 8, 1, 12, 0), 1.1200, 1.1250, 1.1180, 1.1220, 5000.0, 0.0],
        [datetime(2026, 8, 1, 12, 1), 1.1220, 1.1235, 1.1210, 1.1225, 5500.0, 0.0],
        # Bar 3: High stretches to 1.1290 to hit the 20-tick take profit line
        [datetime(2026, 8, 1, 12, 2), 1.1225, 1.1290, 1.1210, 1.1280, 6000.0, 0.0],
    ]

    intent = ExposureIntent(
        alpha_direction=1.0, stop_loss_ticks=1000.0, take_profit_ticks=20.0
    )
    active_bot = PortfolioActiveTestBot(exposure_intent=intent)
    harness = BacktraderTestHarness(
        bot=active_bot,
        records=historical_prices,
        symbol="EURUSD",
        initial_cash=10000.0,
        commission_scheme=FutureFixedMarginScheme(),
    )
    harness.execute_synchronized_run(timeout=2.0)

    assert len(active_bot.history) == 3

    # Cycle # 1: Pristine zero-drift alignment verification under Future rules
    snap_c1 = active_bot.history[1].account_snapshot
    assert snap_c1.available_margin == Decimal("9995.00005")
    assert snap_c1.equity == Decimal("10000.00005")
    assert snap_c1.balance == Decimal("10000.00005")

    # Cycle # 2: Next bar triggers the take profit target level -> Flat
    snap_c2 = active_bot.history[2].account_snapshot
    assert len(active_bot.history[2].position_ledger.records) == 0
    assert snap_c2.balance > Decimal("10000.00")

# -----------------------------------------------------------------------------

def test_portfolio_accounting_spot_stock_cash() -> None:
    """Scenario 4: Audits spot stock cash profiles requiring full payment."""

    class SpotStockCashScheme(bt.CommissionInfo):
        """Spot Cash asset scheme requiring full payment upfront (No Margin)."""

        params = (
            ("commission", 0.0),
            ("mult", 1.0),
            ("margin", 0.0),
            ("commtype", bt.CommInfoBase.COMM_PERC),
            ("stocklike", True),
            ("leverage", 1.0),
            ("automargin", False),
            ("interest", 0.0),
            ("interest_long", False),
        )

    historical_prices = [
        [datetime(2026, 8, 1, 12, 0), 1.1200, 1.1250, 1.1180, 1.1220, 5000.0, 0.0],
        [datetime(2026, 8, 1, 12, 1), 1.1220, 1.1235, 1.1210, 1.1225, 5500.0, 0.0],
        # Bar 3: High stretches to 1.1290 to hit the 20-tick take profit line
        [datetime(2026, 8, 1, 12, 2), 1.1225, 1.1290, 1.1210, 1.1280, 6000.0, 0.0],
    ]

    intent = ExposureIntent(
        alpha_direction=1.0, stop_loss_ticks=1000.0, take_profit_ticks=20.0
    )
    active_bot = PortfolioActiveTestBot(exposure_intent=intent)
    harness = BacktraderTestHarness(
        bot=active_bot,
        records=historical_prices,
        symbol="EURUSD",
        initial_cash=10000.0,
        commission_scheme=SpotStockCashScheme(),
    )
    harness.execute_synchronized_run(timeout=2.0)

    assert len(active_bot.history) == 3

    # Cycle # 1: Pristine zero-drift alignment verification for spot stock cash rules
    snap_c1 = active_bot.history[1].account_snapshot
    assert snap_c1.available_margin == Decimal("9999.8878")
    assert snap_c1.equity == Decimal("10000.00005")
    assert snap_c1.balance == Decimal("10000.00")

    # Cycle # 2: Next bar triggers the take profit target level -> Flat
    snap_c2 = active_bot.history[2].account_snapshot
    assert len(active_bot.history[2].position_ledger.records) == 0
    assert snap_c2.balance > Decimal("10000.00")

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
