"""Aegis Framework - Domain Model Testing Factories."""

from decimal import Decimal
import uuid

from core.models import (
    AccountSnapshot,
    ContractSpecification,
    Order,
    OrderSide,
    OrderType,
    Position,
    PositionLedger,
    PositionSide,
    TimeInForce,
)
from core.models.market import (
    MarketContext,
    MarketPricePoint,
)
from tests.testutils.constants import (
    BASE_TIMESTAMP,
    DEFAULT_ASSET_CURRENCY,
    DEFAULT_BALANCE,
    DEFAULT_BASE_SPREAD_TICKS,
    DEFAULT_CONTRACT_MULTIPLIER,
    DEFAULT_CONTRACT_STEP,
    DEFAULT_EQUITY,
    DEFAULT_MARGIN,
    DEFAULT_MARGIN_REQUIREMENT,
    DEFAULT_MIN_CONTRACT_SIZE,
    DEFAULT_ORDER_QUANTITY,
    DEFAULT_QUOTE_CURRENCY,
    DEFAULT_SYMBOL,
    DEFAULT_TICK_SIZE,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def create_account_snapshot_factory(**kwargs) -> AccountSnapshot:
    """Generates an AccountSnapshot instance with dynamic keyword overrides."""
    defaults = {
        'currency': DEFAULT_ASSET_CURRENCY,
        'balance': DEFAULT_BALANCE,
        'equity': DEFAULT_EQUITY,
        'available_margin': DEFAULT_MARGIN,
    }
    defaults.update(kwargs)
    return AccountSnapshot(**defaults)

# -----------------------------------------------------------------------------

def create_contract_specification_factory(**kwargs) -> ContractSpecification:
    """Generates a ContractSpecification instance with dynamic keyword overrides."""
    defaults = {
        'symbol': DEFAULT_SYMBOL,
        'base_spread_ticks': DEFAULT_BASE_SPREAD_TICKS,
        'contract_multiplier': DEFAULT_CONTRACT_MULTIPLIER,
        'base_currency': DEFAULT_ASSET_CURRENCY,
        'quote_currency': DEFAULT_QUOTE_CURRENCY,
        'contract_step': DEFAULT_CONTRACT_STEP,
        'margin_requirement': DEFAULT_MARGIN_REQUIREMENT,
        'min_contract_size': DEFAULT_MIN_CONTRACT_SIZE,
        'tick_size': DEFAULT_TICK_SIZE,
    }
    defaults.update(kwargs)
    return ContractSpecification(**defaults)

# -----------------------------------------------------------------------------

def create_market_context_factory(**kwargs) -> MarketContext:
    """Generates a MarketContext instance with dynamic keyword overrides."""
    prices_defaults = {
        'timestamp': BASE_TIMESTAMP,
        'mid_price': 1.08500,
        'bid': 1.08490,
        'ask': 1.08510,
        'current_atr': 0.0020,
    }
    # Permet de surcharger les prix s'ils sont passés en kwargs
    prices_kwargs = {
        k: kwargs.pop(k) for k in list(kwargs.keys()) if k in prices_defaults
    }
    prices_defaults.update(prices_kwargs)

    defaults = {
        'prices': MarketPricePoint(**prices_defaults),
        'volume': 1000.0,
    }
    defaults.update(kwargs)
    return MarketContext(**defaults)

# -----------------------------------------------------------------------------

def create_order_factory(**kwargs) -> Order:
    """Generates an Order instance with dynamic keyword overrides."""
    defaults = {
        'client_order_id': f'AEGIS-TEST-{uuid.uuid4()}',
        'timestamp': BASE_TIMESTAMP,
        'symbol': DEFAULT_SYMBOL,
        'side': OrderSide.BUY,
        'order_type': OrderType.MARKET,
        'time_in_force': TimeInForce.DAY,
        'quantity': DEFAULT_ORDER_QUANTITY,
        'price': None,
        'stop_loss_price': None,
        'take_profit_price': None,
    }
    defaults.update(kwargs)
    return Order(**defaults)

# -----------------------------------------------------------------------------

def create_position_factory(**kwargs) -> Position:
    """Generates a Position instance with dynamic keyword overrides."""
    defaults = {
        'symbol': DEFAULT_SYMBOL,
        'ticket_id': 'TKT-CHILEAN-TEST-ID',
        'side': PositionSide.LONG,
        'quantity': Decimal('1.0'),
        'entry_price': Decimal('1.08500'),
    }
    defaults.update(kwargs)
    return Position(**defaults)

# -----------------------------------------------------------------------------

def create_position_ledger_factory(**kwargs) -> PositionLedger:
    """Generates a PositionLedger instance with dynamic keyword overrides."""
    defaults = {
        'records': {},
    }
    defaults.update(kwargs)
    return PositionLedger(**defaults)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
