"""Aegis Framework - Immutable Domain Model Specifications.

Defines unified structured storage data containers protecting type safety.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class OrderSide(Enum):
    """Enforces execution direction flags across external gateway adapters."""
    BUY = "BUY"
    SELL = "SELL"

# -----------------------------------------------------------------------------

class OrderStatus(Enum):
    """Enforces execution lifecycle state tracking across broker gateways."""
    CANCELED = "CANCELED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"

# -----------------------------------------------------------------------------

class OrderType(Enum):
    """Enforces structural routing parameter limitations for orders executions."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"

# -----------------------------------------------------------------------------

class TimeInForce(Enum):
    """Enforces execution expiration boundaries across broker gateways."""
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"

# -----------------------------------------------------------------------------

class TransactionSide(Enum):
    """Enforces execution direction flags across internal accounting nodes."""
    LONG = "LONG"
    SHORT = "SHORT"

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

@dataclass(frozen=True)
class AccountSnapshot:
    """Financial metrics of the trading account.

    Attributes:
        balance: Account cash excluding open positions.
        equity: Account cash including unrealized profits and losses.
        available_margin: Account cash excluding locked position margin.
    """
    balance: Decimal
    equity: Decimal
    available_margin: Decimal

# -----------------------------------------------------------------------------

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
class ExposureIntent:
    """Immutable data record capturing passive execution desires.

    Attributes:
        alpha_direction: The continuous trend conviction scalar bounded strictly
            between -1.0 and 1.0. A value of 0.0 explicitly enforces a flat position
            and triggers a portfolio liquidation. A value of None indicates no active
            opinion, instructing the engine to maintain ongoing exposures.
        stop_loss_ticks: The protective exit distance measured in ticks.
        take_profit_ticks: The target take-profit distance measured in ticks.
    """
    alpha_direction: float | None = None
    stop_loss_ticks: float = 0.0
    take_profit_ticks: float = 0.0

# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class Order:
    """Broker execution request.

    Attributes:
        client_order_id: Unique internal tracking identifier.
        timestamp: Creation time.
        symbol: Target financial asset.
        side: Execution direction (BUY or SELL).
        order_type: Order routing type (e.g., MARKET or LIMIT).
        time_in_force: Execution expiration policy (e.g., DAY or IOC).
        quantity: Order volume expressed in absolute asset units.
        price: Target execution price or None for MARKET orders.
        stop_loss_price: (Optional) Absolute exit price for loss protection.
        take_profit_price: (Optional) Absolute exit price for profit capture.
    """
    client_order_id: str
    timestamp: datetime
    symbol: str
    side: OrderSide
    order_type: OrderType
    time_in_force: TimeInForce
    quantity: Decimal
    price: Decimal | None = None
    stop_loss_price: Decimal | None = None
    take_profit_price: Decimal | None = None

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class OrderEvent:
    """Captures absolute transactional metadata generated during order updates.

    Attributes:
        broker_reference: The unique tracking identifier returned by the broker.
        symbol: The targeted financial instrument ticker.
        status: The exact state inside the execution lifecycle.
        side: The directional positioning constraint of the order.
        executed_price: The financial settlement price recorded by the broker.
        executed_size: The absolute amount of lots fulfilled by the execution.
        timestamp: The definitive execution time of the transaction.
    """
    broker_reference: str
    symbol: str
    status: OrderStatus
    side: OrderSide
    executed_price: float
    executed_size: float
    timestamp: datetime

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class OrderReceipt:
    """Broker execution response details.

    Attributes:
        broker_order_id: (Optional) Unique broker tracking identifier.
        client_order_id: Unique internal tracking identifier.
        status: Order execution lifecycle state.
        average_execution_price: (Optional) Volume-weighted execution price.
        reject_reason: (Optional) Broker rejection cause description.
    """
    broker_order_id: str | None
    client_order_id: str
    status: OrderStatus
    average_execution_price: Decimal | None = None
    reject_reason: str | None = None

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
class PortfolioSnapshot:
    """Immutable asset valuation metrics snapshot extracted from the broker gateway.

    Attributes:
        account_id: The unique financial node identification string.
        raw_balance: The settled cash value available inside the accounting nodes.
        raw_margin_allocated: The current total margin capital locked by exposure.
        raw_unrealized_pnl: The cumulative floating valuation of active contracts.
        timestamp: The exact temporal coordinate of ledger extraction.
    """
    account_id: str
    raw_balance: float
    raw_margin_allocated: float
    raw_unrealized_pnl: float
    timestamp: datetime

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
