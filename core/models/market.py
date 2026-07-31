"""Aegis Framework - Market Continuous Analytics.

Stores mathematical valuation price points and physical market snapshots using
high-performance float structures.
"""

from dataclasses import dataclass
from datetime import datetime

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

# LEGACY
@dataclass(frozen=True)
class InstrumentSpecification:
    """Enforces compile-time type validation for multi-asset market parameters.

    Attributes:
        base_spread_ticks: The structural minimum cost measured in ticks.
        lot_size: The absolute quantity of underlying assets per standard contract.
        lot_step: The minimum contract fractional increments permitted by the broker.
        margin_requirement: The percentage of total nominal exposure required
            as margin liquidity, expressed as a decimal.
        min_lot: The absolute minimum trade volume threshold enforced for orders.
        tick_size: The minimum price movement allowed for the asset.
        volatility_factor: The multiplier adjusting the standard deviation.
    """
    base_spread_ticks: float
    lot_size: int
    lot_step: float
    margin_requirement: float
    min_lot: float
    tick_size: float
    volatility_factor: float

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class MarketPricePoint:
    """Protects pricing snapshots matrix calculations from mutations.

    Attributes:
        timestamp: The exact temporal coordinate of the market sample.
        mid_price: The fair center price between current liquidity boundaries.
        bid: The highest available quote for selling operations.
        ask: The lowest available quote for buying operations.
        current_atr: The smoothed trailing range proxy for local volatility.
        is_night_tariff: Flag enforcing specific premium spreads after hours.
    """
    timestamp: datetime
    mid_price: float
    bid: float
    ask: float
    current_atr: float
    is_night_tariff: bool = False

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class MarketContext:
    """Immutable record capturing the current market state.

    Attributes:
        prices: Current market price information.
        volume: (Optional) Current market trading volume.
    """
    prices: MarketPricePoint
    volume: float | None = None

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
