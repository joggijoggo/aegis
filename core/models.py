"""Aegis Framework - Immutable Domain Model Specifications.

Defines unified structured storage data containers protecting type safety.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class OrderStatus(Enum):
    """Enforces compile-time type safety for asynchronous lifecycle states."""

    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"

# -----------------------------------------------------------------------------

class OrderType(Enum):
    """Enforces structural routing parameter limitations for orders executions."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"

# -----------------------------------------------------------------------------

class TransactionSide(Enum):
    """Enforces execution direction flags across internal accounting nodes."""

    LONG = "LONG"
    SHORT = "SHORT"

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

@dataclass(frozen=True)
class InstrumentSpecification:
    """Enforces compile-time type validation for multi-asset market parameters.

    Attributes:
        base_spread_ticks: The structural minimum cost measured in ticks.
        lot_size: The absolute quantity of underlying assets per standard contract.
        lot_step: The minimum contract fractional increments permitted by the broker.
        min_lot: The absolute minimum trade volume threshold enforced for orders.
        tick_size: The minimum price movement allowed for the asset.
        volatility_factor: The multiplier adjusting the standard deviation.
    """
    base_spread_ticks: float
    lot_size: int
    lot_step: float
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
class OrderEvent:
    """Captures absolute transactional metadata generated during order updates.

    Attributes:
        order_id: The unique system identifier assigned to this request.
        symbol: The targeted financial instrument ticker.
        status: The exact state inside the execution lifecycle.
        side: The directional positioning constraint of the order.
        executed_price: The financial settlement price recorded by the broker.
        executed_size: The absolute amount of lots fulfilled by the execution.
        timestamp: The definitive execution time of the transaction.
    """
    order_id: int
    symbol: str
    status: "OrderStatus"
    side: "TransactionSide"
    executed_price: float
    executed_size: int
    timestamp: datetime

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class OrderRequest:
    """Immutable data container representing a strategy trade intention.

    Attributes:
        symbol: The targeted financial asset identifier.
        stop_loss_ticks: The structural protection distance measured in ticks.
        risk_percentage: The maximum fraction of account equity risked on the trade.
        confidence_factor: A fractional scaling coefficient that can only reduce size.
    """
    symbol: str
    stop_loss_ticks: float
    risk_percentage: float
    confidence_factor: float

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class PositionCloseEvent:
    """Encapsulates definitive accounting metrics records when a trade is finalized.

    Attributes:
        symbol: The financial instrument ticker of the position.
        side: The long or short orientation of the line.
        pnl_gross: The raw financial output before accounting frictions.
        pnl_net: The absolute structural payout clear of broker charges.
        commission: The financial fee deducted by the gateway adapter.
        bars_duration: The total discrete time steps this trade was sustained.
        entry_timestamp: The temporal execution anchor for trade opening.
        exit_timestamp: The temporal execution anchor for trade settlement.
    """
    symbol: str
    side: "TransactionSide"
    pnl_gross: float
    pnl_net: float
    commission: float
    bars_duration: int
    entry_timestamp: datetime
    exit_timestamp: datetime

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class RegimeConfidenceVector:
    """Stores statistical confidence metrics computed by math classifiers.

    Attributes:
        mean_reversion: Probability weight assigned to cyclic behaviors.
        trending: Probability weight assigned to directional patterns.
        noise: Probability weight assigned to non-exploitable random dynamics.
    """
    mean_reversion: float
    trending: float
    noise: float

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskValidationResult:
    """Immutable verdict profile generated by the risk management systems.

    Attributes:
        is_approved: Flag signaling if the intention complies with risk filters.
        calculated_volume_lots: The final calculated order size in standardized lots.
        rejection_reason: The descriptive reason detailing why an order was rejected.
    """
    is_approved: bool
    calculated_volume_lots: float
    rejection_reason: str

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class TradeTelemetrySnapshot:
    """Captures explicable post-mortem operational metrics records snapshots.

    Attributes:
        timestamp: The technical log time of this measurement.
        indicator_value: The numerical output of the underlying formula.
        regime_vector: The complex mathematical probability context of the market.
    """
    timestamp: datetime
    indicator_value: float
    regime_vector: RegimeConfidenceVector

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
