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
