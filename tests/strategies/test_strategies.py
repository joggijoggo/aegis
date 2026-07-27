"""Aegis Framework - Strategy Lifecycle Unit Tests.

Verifies historical indicator warm-up buffers and bracket execution routing.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from core.models import MarketPricePoint


# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_strategy_lifecycle_and_warm_up_shield():
    """Validates that execution blocks trades until historical warm-up completes."""
    from brokers.simulated_adapter import SimulatedBrokerAdapter
    from core.accounts import IsolatedAssetAccount
    from strategies.mean_reversion import AegisMeanReversionBot

    account = IsolatedAssetAccount(asset_pair="EURUSD", initial_capital=10000.0)
    broker = SimulatedBrokerAdapter(target_account=account)

    # Instantiate bot with a strict requirement of 10 warm-up bars to clear classifier
    bot = AegisMeanReversionBot(broker_bridge=broker, warm_up_bars=10)

    # Base price parameters shell
    t1 = datetime(2026, 3, 25, 14, 0, tzinfo=ZoneInfo("UTC"))
    p1 = MarketPricePoint(
        timestamp=t1, mid_price=1.0000, bid=0.9995, ask=1.0005, current_atr=0.0010
    )

    # Create a cyclical history of 9 elements (insufficient for a warm-up of 10)
    insufficient_history = [
        1.00, 0.98, 1.02, 1.00, 0.98, 1.02, 1.00, 0.98, 1.02
    ]

    # Feed insufficient history: Strategy must remain in warm-up state
    bot.on_bar_close(
        asset="EURUSD",
        price_snapshot=p1,
        historical_closes=insufficient_history
    )
    assert bot.is_warmed_up is False
    assert len(account.mock_positions) == 0

    # Build a valid 10-element history that satisfies warm-up lock
    sufficient_history = insufficient_history + [1.0000]
    bot.on_bar_close(
        asset="EURUSD",
        price_snapshot=p1,
        historical_closes=sufficient_history
    )
    assert bot.is_warmed_up is True

    # Generate a massive series of 40 oscillating data points to hard-lock MR
    oscillating_base = [1.00, 0.98, 1.02, 1.00] * 10

    # Apply a target price point that triggers the 2% price expansion rule
    # without destroying the mathematical properties of the previous oscillations
    p_trigger = MarketPricePoint(
        timestamp=t1, mid_price=1.0250, bid=1.0245, ask=1.0255, current_atr=0.0010
    )
    active_history = oscillating_base + [1.0250]

    bot.on_bar_close(
        asset="EURUSD",
        price_snapshot=p_trigger,
        historical_closes=active_history
    )

    # Validate bracket position routing and audit telemetry allocation
    assert len(account.mock_positions) == 1
    assert account.mock_positions[0]["side"] == "SHORT"
    assert account.mock_positions[0]["size_lots"] == 1.0

    # Verify portfolio snapshot telemetry history mapping
    assert len(bot.telemetry_history) == 1
    last_telemetry = bot.telemetry_history[-1]
    assert last_telemetry.indicator_value > 0.0
    assert last_telemetry.regime_vector.mean_reversion > 0.40

    # Extract ledger records to verify baseline account parameters synchronization
    snapshot = broker.get_portfolio_snapshot()
    assert snapshot["balance"] == 10000.0
    assert snapshot["equity"] == 10000.0
    assert len(snapshot["positions"]) == 1

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
