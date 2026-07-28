"""Aegis Framework - Financial Friction Models.

Simulates volatility-adjusted dynamic spreads and localized interbank liquidity
drain markup penalties tailored to modern clearing conditions.
"""

from datetime import datetime

from zoneinfo import ZoneInfo

from core.models import MarketPricePoint

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class DynamicFrictionEngine:
    """Emulates dynamic spreads and interbank rollover constraints."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        base_spread_ticks: float,
        tick_size: float = 0.0001,
        volatility_factor: float = 0.1,
    ):
        """Initializes the pricing friction simulator.

        Args:
            base_spread_ticks (float): Minimum tight spread value in ticks.
            tick_size (float): Market tick translation scale (e.g., 0.0001).
            volatility_factor (float): Sensitivity coefficient for
                ATR-driven spread expansion.
        """
        self.base_spread_ticks = base_spread_ticks
        self.tick_size = tick_size
        self.volatility_factor = volatility_factor

# -----------------------------------------------------------------------------

    def get_market_prices(
        self,
        utc_time: datetime,
        mid_price: float,
        current_atr: float,
    ) -> MarketPricePoint:
        """Calculates bid/ask parameters factoring in localized time filters.

        Args:
            utc_time (datetime): Time anchor location mapped to global timeline.
            mid_price (float): Pure mid-market transaction price baseline.
            current_atr (float): Immediate market volatility metric index.

        Returns:
            MarketPricePoint: Structured snapshot mapping absolute spreads.
        """
        paris_zone = ZoneInfo("Europe/Paris")
        local_time = utc_time.astimezone(paris_zone)

        is_night = local_time.hour >= 23 or local_time.hour < 8
        multiplier = 4.0 if is_night else 1.0
        time_spread = self.base_spread_ticks * multiplier * self.tick_size
        volatility_markup = current_atr * self.volatility_factor
        total_spread = time_spread + volatility_markup

        half_spread = total_spread / 2.0
        bid_price = mid_price - half_spread
        ask_price = mid_price + half_spread

        return MarketPricePoint(
            timestamp=utc_time,
            mid_price=mid_price,
            bid=bid_price,
            ask=ask_price,
            current_atr=current_atr,
            is_night_tariff=is_night,
        )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
