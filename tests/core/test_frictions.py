"""Aegis Framework - IG Group Friction Unit Tests.

Enforces TDD validation protocols onto the dynamic pricing and spread layers.
"""

from datetime import datetime

from zoneinfo import ZoneInfo

from core.frictions import IGGroupFrictionEngine

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_ig_friction_engine_atr_volatility_expansion():
    """Verify spread expansion scaling driven by rolling ATR volatility metrics."""
    engine = IGGroupFrictionEngine(
        base_spread_pips=0.6,
        pip_value=0.0001,
        volatility_factor=0.1
    )

    # CASE 1: Day Time (14:00 UTC) with high volatility (ATR = 20 pips)
    t_day_volatile = datetime(2026, 3, 25, 14, 0, tzinfo=ZoneInfo('UTC'))
    prices_volatile = engine.get_market_prices(
        utc_time=t_day_volatile,
        mid_price=1.0800,
        current_atr=0.0020
    )
    assert round(prices_volatile.ask - prices_volatile.bid, 5) == 0.00026

# -----------------------------------------------------------------------------

def test_ig_friction_engine_paris_timezone_handling():
    """Verify seasonal Paris time rollover cutoff logic and dynamic night tariff flags."""
    engine = IGGroupFrictionEngine(base_spread_pips=0.6, pip_value=0.0001)

    # CASE 1: Winter Time (March) -> 22:55 Paris time (21:55 UTC) is STILL DAY
    t_winter_day = datetime(2026, 3, 25, 21, 55, tzinfo=ZoneInfo('UTC'))
    prices_winter_day = engine.get_market_prices(
        utc_time=t_winter_day,
        mid_price=1.0800,
        current_atr=0.0,
    )
    assert prices_winter_day.is_night_tariff is False
    assert round(prices_winter_day.ask - prices_winter_day.bid, 5) == 0.00006

    # CASE 2: Winter Time (March) -> 23:05 Paris time (22:05 UTC) is NIGHT
    t_winter_night = datetime(2026, 3, 25, 22, 5, tzinfo=ZoneInfo('UTC'))
    prices_winter_night = engine.get_market_prices(
        utc_time=t_winter_night,
        mid_price=1.0800,
        current_atr=0.0,
    )
    assert prices_winter_night.is_night_tariff is True
    assert round(prices_winter_night.ask - prices_winter_night.bid, 5) == 0.00024

    # CASE 3: Summer Time (July) -> 22:55 Paris time (20:55 UTC) is STILL DAY
    t_summer_day = datetime(2026, 7, 15, 20, 55, tzinfo=ZoneInfo('UTC'))
    prices_summer_day = engine.get_market_prices(
        utc_time=t_summer_day,
        mid_price=1.0800,
        current_atr=0.0,
    )
    assert prices_summer_day.is_night_tariff is False
    assert round(prices_summer_day.ask - prices_summer_day.bid, 5) == 0.00006

    # CASE 4: Summer Time (July) -> 23:05 Paris time (21:05 UTC) is NIGHT
    t_summer_night = datetime(2026, 7, 15, 21, 5, tzinfo=ZoneInfo('UTC'))
    prices_summer_night = engine.get_market_prices(
        utc_time=t_summer_night,
        mid_price=1.0800,
        current_atr=0.0,
    )
    assert prices_summer_night.is_night_tariff is True
    assert round(prices_summer_night.ask - prices_summer_night.bid, 5) == 0.00024

# -----------------------------------------------------------------------------

def test_ig_friction_engine_timezone_widening():
    """Validates dynamic spread calculation and local London cutoff penalties."""
    # Base spread of 0.6 pips, where 1 pip = 0.0001
    engine = IGGroupFrictionEngine(
        base_spread_pips=0.6,
        pip_value=0.0001
    )

    # Test Case 1: Standard liquid hours (14:00 UTC) with zero volatility
    t_liquid = datetime(2026, 3, 25, 14, 0, tzinfo=ZoneInfo('UTC'))
    prices_liquid = engine.get_market_prices(
        utc_time=t_liquid,
        mid_price=1.0800,
        current_atr=0.0
    )

    # Expected spread = 0.6 pips -> Ask/Bid boundary distance should match
    assert round(prices_liquid.ask - prices_liquid.bid, 5) == 0.00006

    # Test Case 2: Midnight liquidity dry-up (22:00 UTC / London Rollover active)
    # The spread must automatically undergo a 4x multiplier markup penalty
    t_rollover = datetime(2026, 3, 25, 22, 0, tzinfo=ZoneInfo('UTC'))
    prices_rollover = engine.get_market_prices(
        utc_time=t_rollover,
        mid_price=1.0800,
        current_atr=0.0
    )

    # Expected spread = 0.6 * 4 = 2.4 pips -> 0.00024 distance width
    assert round(prices_rollover.ask - prices_rollover.bid, 5) == 0.00024

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
