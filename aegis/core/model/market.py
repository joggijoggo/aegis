"""Aegis Framework - Market Continuous Analytics.

Stores mathematical valuation price points and physical market snapshots using
high-performance float structures.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

@dataclass(frozen=True)
class ContractSpecification:
    """Microstructural parameter specification for trading contracts.

    Attributes:
        symbol: Unique financial instrument market identifier.
            Example: 'EURUSD' or 'IX.D.DOW.IFS.IP'.
        base_spread_ticks: Minimum structural transaction cost in ticks.
            Example: 2.0 for a two-tick spread.
        contract_multiplier: Leverage scaling factor linking price to nominal values.
            Example: 100000 for Forex, 1 for indices.
        base_currency: Native currency unit of the underlying contract.
            Example: "EUR" for EURUSD, "USD" for Wall Street index.
        quote_currency: Currency unit denominating the transaction price.
            Example: "USD" for EURUSD, "EUR" for France 40 index.
        contract_step: Minimum fractional volume increment permitted for orders.
            Example: 0.01 for Forex, 0.1 for indices.
        margin_requirement: Percentage of total exposure required as safety collateral.
            Example: 0.0333 for a thirty-to-one leverage ratio.
        min_contract_size: Absolute minimum volume threshold accepted for execution.
            Example: 0.1 for micro-contracts.
        tick_size: Minimum incremental fraction of price movement.
            Example: 0.00001 for EURUSD, 1.0 for Dow Jones.
    """
    symbol: str
    base_spread_ticks: Decimal
    contract_multiplier: Decimal
    base_currency: str
    quote_currency: str
    contract_step: Decimal
    margin_requirement: Decimal
    min_contract_size: Decimal
    tick_size: Decimal

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
