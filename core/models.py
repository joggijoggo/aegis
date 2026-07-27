"""Aegis Framework - Core Data Models.

Defines the strict contracts for pricing snapshots, order routing payloads,
regime confidence vectors, and execution metrics.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class TransactionSide(Enum):
    """Enforces strict cryptographic compilation bounds for order directions."""

    LONG = "LONG"
    SHORT = "SHORT"

# -----------------------------------------------------------------------------

class OrderType(Enum):
    """Enforces strict execution constraint parameters for broker matching engines."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

@dataclass(frozen=True)
class RegimeConfidenceVector:
    """Immutably stores normalized classification probabilities for market states.

    Attributes:
        mean_reversion (float): Probability score for cyclical range environments.
        trending (float): Probability score for persistent breakout regimes.
        noise (float): Probability score for balanced random walk conditions.
    """

    mean_reversion: float
    trending: float
    noise: float

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class TradeTelemetrySnapshot:
    """Immutably preserves execution context analytics for post-mortem audits.

    Attributes:
        timestamp (datetime): Exact timeline parameter of order generation.
        indicator_value (float): Value of the execution technical indicator anchor.
        regime_vector (RegimeConfidenceVector): Market state analysis snapshot.
    """

    timestamp: datetime
    indicator_value: float
    regime_vector: RegimeConfidenceVector

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class MarketPricePoint:
    """Unified synchronized price bucket anchoring absolute execution metrics.

    Attributes:
        timestamp (datetime): Absolute UTC Time Anchor.
        mid_price (float): Mid market valuation price.
        bid (float): Simulated selling liquidity boundary.
        ask (float): Simulated buying liquidity boundary.
        current_atr (float): Current volatility average value.
    """

    timestamp: datetime
    mid_price: float
    bid: float
    ask: float
    current_atr: float

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
