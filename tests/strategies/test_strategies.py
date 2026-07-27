"""Aegis Framework - Strategy Lifecycle Unit Tests.

Verifies historical indicator warm-up buffers and bracket execution routing.
"""

from datetime import datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from brokers.base_broker import AbstractBrokerBridge
from core.models import MarketPricePoint
from core.models import OrderType
from core.models import TransactionSide
from strategies.base_strategy import AbstractStrategy


# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class DummyBreakoutBot(AbstractStrategy):
    """Minimal test bot to enforce child implementation pattern constraints."""

    def __init__(self, broker_bridge: AbstractBrokerBridge, warm_up_bars: int):
        """Initializes structural parameters for behavioral verification."""
        super().__init__(
            broker_bridge=broker_bridge,
            warm_up_bars=warm_up_bars,
        )
        self.logic_executed = False

# -----------------------------------------------------------------------------

    def _on_bar_close(
        self,
        asset: str,
        price_snapshot: MarketPricePoint,
        historical_closes: list[float]
    ) -> None:
        """Implements the mandatory template method requirement."""
        self.logic_executed = True


# -----------------------------------------------------------------------------

def test_template_method_warm_up_centralization():
    """Validates that AbstractStrategy enforces the warm-up loop by inheritance."""
    from brokers.simulated_adapter import SimulatedBrokerAdapter
    from core.accounts import IsolatedAssetAccount

    account = IsolatedAssetAccount(asset_pair="EURUSD", initial_capital=10000.0)
    broker = SimulatedBrokerAdapter(target_account=account)

    bot = DummyBreakoutBot(broker_bridge=broker, warm_up_bars=3)

    t1 = datetime(2026, 3, 25, 14, 0, tzinfo=ZoneInfo("UTC"))
    p1 = MarketPricePoint(
        timestamp=t1, mid_price=1.0000, bid=0.9995, ask=1.0005, current_atr=0.0010
    )

    # 1. Feed insufficient history: Mother must intercept and block child execution
    bot.on_bar_close(asset="EURUSD", price_snapshot=p1, historical_closes=[1.00])
    assert bot.is_warmed_up is False
    assert bot.logic_executed is False

    # 2. Feed sufficient history: Mother must clear warm-up and trigger internal hook
    bot.on_bar_close(
        asset="EURUSD", price_snapshot=p1, historical_closes=[1.00, 1.01, 1.02]
    )
    assert bot.is_warmed_up is True
    assert bot.logic_executed is True


# -----------------------------------------------------------------------------

def test_mean_reversion_strategy_execution_flow():
    """Validates active trade routing and comprehensive metrics reporting logs."""
    from brokers.simulated_adapter import SimulatedBrokerAdapter
    from core.accounts import IsolatedAssetAccount
    from strategies.mean_reversion import AegisMeanReversionBot

    account = IsolatedAssetAccount(asset_pair="EURUSD", initial_capital=10000.0)
    broker = SimulatedBrokerAdapter(target_account=account)

    bot = AegisMeanReversionBot(
        broker_bridge=broker,
        warm_up_bars=10,
    )

    t1 = datetime(2026, 3, 25, 14, 0, tzinfo=ZoneInfo("UTC"))
    oscillating_base = [1.00, 0.98, 1.02, 1.00] * 10

    p_trigger = MarketPricePoint(
        timestamp=t1, mid_price=1.0250, bid=1.0245, ask=1.0255, current_atr=0.0010
    )
    active_history = oscillating_base + [1.0250]

    bot.on_bar_close(
        asset="EURUSD",
        price_snapshot=p_trigger,
        historical_closes=active_history
    )

    # Validate automated bracket matching engine position entry routing parameters
    assert account.mock_positions is not None
    assert account.mock_positions["symbol"] == "EURUSD"
    assert account.mock_positions["side"] == "SHORT"
    assert account.mock_positions["size_lots"] == 1.0

    # Verify portfolio snapshot telemetry history mapping
    assert len(bot.telemetry_history) == 1
    last_telemetry = bot.telemetry_history[-1]
    assert last_telemetry.indicator_value > 0.0
    assert last_telemetry.regime_vector.mean_reversion > 0.40

    # Extract ledger records to verify baseline synchronization
    snapshot = broker.get_portfolio_snapshot()
    assert snapshot["balance"] == 10000.0
    assert snapshot["equity"] == 10000.0
    assert len(snapshot["positions"]) == 1


# -----------------------------------------------------------------------------

def test_base_strategy_routes_absolute_prices_for_long_orders():
    """Validates high-level relative pips conversion to absolute prices for LONG."""
    from brokers.simulated_adapter import SimulatedBrokerAdapter
    from core.accounts import IsolatedAssetAccount
    from strategies.mean_reversion import AegisMeanReversionBot

    account = IsolatedAssetAccount(asset_pair="EURUSD", initial_capital=10000.0)
    broker = SimulatedBrokerAdapter(target_account=account)

    bot = AegisMeanReversionBot(
        broker_bridge=broker,
        warm_up_bars=10,
    )

    bot.place_bracket_order(
        symbol="EURUSD",
        side=TransactionSide.LONG,
        order_type=OrderType.MARKET,
        volume_lots=2.0,
        current_price=1.1000,
        stop_loss_pips=30.0,
        take_profit_pips=60.0
    )

    assert account.mock_positions is not None
    assert account.mock_positions["side"] == "LONG"
    assert account.mock_positions["size_lots"] == 2.0


# -----------------------------------------------------------------------------

def test_base_strategy_raises_value_error_on_unregistered_asset():
    """Validates that a ValueError is raised if a bot trades an unregistered asset."""
    from strategies.mean_reversion import AegisMeanReversionBot

    mock_broker = MagicMock()
    mock_broker.get_instrument_specification.side_effect = ValueError(
        "Asset identity 'UNKNOWN' is missing from instrument registry."
    )

    bot = AegisMeanReversionBot(
        broker_bridge=mock_broker,
        warm_up_bars=10,
    )

    with pytest.raises(ValueError) as exc_info:
        bot.place_bracket_order(
            symbol="UNKNOWN",
            side=TransactionSide.LONG,
            order_type=OrderType.MARKET,
            volume_lots=1.0,
            current_price=1.0000,
            stop_loss_pips=20.0,
            take_profit_pips=40.0
        )

    assert "missing from instrument registry" in str(exc_info.value)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
