"""Aegis Framework - Immutable Domain Model Specifications.

Defines unified structured storage data containers protecting type safety.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

@dataclass(frozen=True)
class InstrumentSpecification:
    """Enforces compile-time type validation for multi-asset market parameters."""
    pip_size: float
    lot_size: int

# -----------------------------------------------------------------------------

class TransactionSide(Enum):
    """Enforces execution direction flags across internal accounting nodes."""
    LONG = "LONG"
    SHORT = "SHORT"

# -----------------------------------------------------------------------------

class OrderType(Enum):
    """Enforces structural routing parameter limitations for orders executions."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"

# -----------------------------------------------------------------------------

class OrderStatus(Enum):
    """Enforces compile-time type safety for asynchronous lifecycle states."""
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class OrderEvent:
    """Captures absolute transactional metadata generated during order updates."""
    order_id: int
    symbol: str
    status: OrderStatus
    side: TransactionSide
    executed_price: float
    executed_size: int
    timestamp: datetime

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class MarketPricePoint:
    """Protects pricing snapshots matrix calculations from mutations."""
    timestamp: datetime
    mid_price: float
    bid: float
    ask: float
    current_atr: float

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class RegimeConfidenceVector:
    """Stores statistical confidence metrics computed by math classifiers."""
    mean_reversion: float
    trending: float
    noise: float

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class TradeTelemetrySnapshot:
    """Captures explicable post-mortem operational metrics records snapshots."""
    timestamp: datetime
    indicator_value: float
    regime_vector: RegimeConfidenceVector

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
