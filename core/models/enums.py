"""Aegis Framework - Domain Enumerations.

Enforces unified execution directions, lifecycle states, and internal accounting
flags across the framework boundaries.
"""

from enum import Enum

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class EventType(Enum):
    """Infrastructure event categories."""
    MARKET_TICK = 'MARKET_TICK'
    ORDER_NOTIFICATION = 'ORDER_NOTIFICATION'
    TRADE_NOTIFICATION = 'TRADE_NOTIFICATION'

# -----------------------------------------------------------------------------

class OrderSide(Enum):
    """Enforces execution direction flags across external gateway adapters."""
    BUY = 'BUY'
    SELL = 'SELL'

# -----------------------------------------------------------------------------

class OrderStatus(Enum):
    """Enforces execution lifecycle state tracking across broker gateways."""
    CANCELED = 'CANCELED'
    FILLED = 'FILLED'
    PARTIALLY_FILLED = 'PARTIALLY_FILLED'
    PENDING = 'PENDING'
    REJECTED = 'REJECTED'

# -----------------------------------------------------------------------------

class OrderType(Enum):
    """Enforces structural routing parameter limitations for orders executions."""
    MARKET = 'MARKET'
    LIMIT = 'LIMIT'

# -----------------------------------------------------------------------------

class TimeInForce(Enum):
    """Enforces execution expiration boundaries across broker gateways."""
    DAY = 'DAY'
    GTC = 'GTC'
    IOC = 'IOC'

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
