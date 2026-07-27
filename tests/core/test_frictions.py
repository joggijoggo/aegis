"""Aegis Framework - IG Group Friction Unit Tests.

Enforces TDD validation protocols onto the dynamic pricing and spread layers.
"""

from datetime import datetime

from zoneinfo import ZoneInfo

from core.frictions import IGGroupFrictionEngine

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

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
