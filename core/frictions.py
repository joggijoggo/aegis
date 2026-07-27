"""Aegis Framework - IG Group Financial Friction Models.

Simulates volatility-adjusted dynamic spreads and localized interbank liquidity
drain markup penalties tailored to modern FX clearing conditions.
"""

from datetime import datetime

from zoneinfo import ZoneInfo

from core.models import MarketPricePoint

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class IGGroupFrictionEngine:
    """Emulates dynamic spreads and interbank rollover constraints of IG Market."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        base_spread_pips: float,
        pip_value: float = 0.0001
    ):
        """Initializes the pricing friction simulator.

        Args:
            base_spread_pips (float): Minimum tight spread value in pips.
            pip_value (float): Market pip translation scale (e.g., 0.0001).
        """
        self.base_spread_pips = base_spread_pips
        self.pip_value = pip_value
        self.london_tz = ZoneInfo('Europe/London')

# -----------------------------------------------------------------------------

    def get_market_prices(
        self,
        utc_time: datetime,
        mid_price: float,
        current_atr: float
    ) -> MarketPricePoint:
        """Calculates bid/ask parameters factoring in localized time filters.

        Args:
            utc_time (datetime): Time anchor location mapped to global timeline.
            mid_price (float): Pure mid-market transaction price baseline.
            current_atr (float): Immediate market volatility metric index.

        Returns:
            MarketPricePoint: Structured snapshot mapping absolute spreads.
        """
        london_time = utc_time.astimezone(self.london_tz)
        h = london_time.hour
        m = london_time.minute

        is_rollover = False
        if (h == 21 and m >= 45) or (h == 22) or (h == 23 and m <= 15):
            is_rollover = True

        multiplier = 4.0 if is_rollover else 1.0

        vol_markup = current_atr / self.pip_value if current_atr > 0 else 0.0
        total_spread_pips = (self.base_spread_pips + vol_markup) * multiplier
        half_spread_value = (total_spread_pips * self.pip_value) / 2.0

        return MarketPricePoint(
            timestamp=utc_time,
            mid_price=mid_price,
            bid=mid_price - half_spread_value,
            ask=mid_price + half_spread_value,
            current_atr=current_atr
        )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
