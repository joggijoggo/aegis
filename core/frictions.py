"""Aegis Framework - Financial Friction Models.

Simulates volatility-adjusted dynamic spreads and localized interbank liquidity
drain markup penalties tailored to modern clearing conditions.
"""

from datetime import datetime
from decimal import Decimal
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
        tick_size: float,
        volatility_factor: float,
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
        multiplier_dec = Decimal("4.0") if is_night else Decimal("1.0")

        # Cast raw inputs to string-based exact decimal instances
        mid_dec = Decimal(str(mid_price))
        atr_dec = Decimal(str(current_atr))
        base_spread_dec = Decimal(str(self.base_spread_ticks))
        tick_size_dec = Decimal(str(self.tick_size))
        vol_factor_dec = Decimal(str(self.volatility_factor))

        # Compute dynamic execution prices via high-precision base-10 math
        time_spread = base_spread_dec * multiplier_dec * tick_size_dec
        volatility_markup = atr_dec * vol_factor_dec
        total_spread = time_spread + volatility_markup

        half_spread = total_spread / Decimal("2.0")
        bid_price = float(mid_dec - half_spread)
        ask_price = float(mid_dec + half_spread)

        return MarketPricePoint(
            timestamp=utc_time,
            mid_price=mid_price,
            bid=bid_price,
            ask=ask_price,
            current_atr=current_atr,
            is_night_tariff=is_night,
        )

# -----------------------------------------------------------------------------

    def calculate_commission(
        self,
        size: float,
        commission_per_lot: float,
    ) -> float:
        """Calculates the absolute institutional execution fee based on volume.

        Args:
            size (float): Position size expressed in transaction lots.
            commission_per_lot (float): Contract commission rate per volume unit.

        Returns:
            float: Total calculated fee currency volume value.
        """
        size_dec = Decimal(str(size))
        rate_dec = Decimal(str(commission_per_lot))
        return float(size_dec * rate_dec)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
