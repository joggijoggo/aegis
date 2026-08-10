"""Aegis Framework - Fixed Financial and Temporal Testing Constants."""

from datetime import datetime, timezone
from decimal import Decimal

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

DEFAULT_ACCOUNT_ID = 'ACC-AEGIS-TEST-01'
DEFAULT_ASSET_CURRENCY = 'EUR'
DEFAULT_QUOTE_CURRENCY = 'USD'
DEFAULT_SYMBOL = 'EURUSD'

# -----------------------------------------------------------------------------

DEFAULT_BALANCE = Decimal('10000.00')
DEFAULT_EQUITY = Decimal('10000.00')
DEFAULT_MARGIN = Decimal('10000.00')

# -----------------------------------------------------------------------------

DEFAULT_BASE_SPREAD_TICKS = Decimal('2.0')
DEFAULT_CONTRACT_MULTIPLIER = Decimal('100000.00')
DEFAULT_CONTRACT_STEP = Decimal('0.01')
DEFAULT_MARGIN_REQUIREMENT = Decimal('0.02')
DEFAULT_MIN_CONTRACT_SIZE = Decimal('0.1')
DEFAULT_TICK_SIZE = Decimal('0.00001')

# -----------------------------------------------------------------------------

DEFAULT_ORDER_QUANTITY = Decimal('1.0')

# -----------------------------------------------------------------------------

BASE_TIMESTAMP = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
