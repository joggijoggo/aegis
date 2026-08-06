"""Aegis Framework - Domain Enumerations.

Enforces unified execution directions, lifecycle states, and internal accounting
flags across the framework boundaries.
"""

from enum import StrEnum

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class EventType(StrEnum):
    """Infrastructure event categories."""
    MARKET_TICK = 'MARKET_TICK'
    ORDER_NOTIFICATION = 'ORDER_NOTIFICATION'
    TRADE_NOTIFICATION = 'TRADE_NOTIFICATION'

# -----------------------------------------------------------------------------

class OrderGroupState(StrEnum):
    """Aggregated execution lifecycle state of an entire bracket group in RAM.

    States:
        ACTIVE: Parent order is filled; market exposure is live and protected.
        CANCELED: Manual intervention or global cancellation finalized.
        CLOSING: A child order has filled; position unwinding is underway.
        COMPLETED: Cycle successfully closed out at zero remaining contracts.
        CORRUPTED: Microstructural failure or protection rupture detected.
        PENDING: Group instantiated; awaiting parent entrance order execution.
        REJECTED: Parent entrance order failed or rejected upon submission.
        REJECTING: Parent failed; group sequester waiting for child cancellations.
    """
    ACTIVE = 'ACTIVE'
    CANCELED = 'CANCELED'
    CLOSING = 'CLOSING'
    COMPLETED = 'COMPLETED'
    CORRUPTED = 'CORRUPTED'
    PENDING = 'PENDING'
    REJECTED = 'REJECTED'
    REJECTING = 'REJECTING'

    @property
    def is_terminal(self) -> bool:
        """Determines if the group execution cycle is completely dead or closed."""
        return self in {
            OrderGroupState.CANCELED,
            OrderGroupState.COMPLETED,
            OrderGroupState.REJECTED,
        }

# -----------------------------------------------------------------------------

class OrderSide(StrEnum):
    """Enforces execution direction flags across external gateway adapters."""
    BUY = 'BUY'
    SELL = 'SELL'

# -----------------------------------------------------------------------------

class OrderState(StrEnum):
    """Atomic execution lifecycle state of a single order in the broker book.

    States:
        CANCELED: Order explicitly removed from the book before execution.
        EXPIRED: Order validity time-limit exceeded session boundaries.
        FILLED: Order volume fully matched and executed by the venue.
        PARTIALLY_FILLED: Fractional execution matching partial volume.
        PENDING: Order actively waiting in the book for market matching.
        REJECTED: Order refused upon submission due to margin or technical rules.
    """
    CANCELED = 'CANCELED'
    EXPIRED = 'EXPIRED'
    FILLED = 'FILLED'
    PARTIALLY_FILLED = 'PARTIALLY_FILLED'
    PENDING = 'PENDING'
    REJECTED = 'REJECTED'

    @property
    def is_terminal(self) -> bool:
        """Determines if the atomic execution state represents a final lifecycle boundary."""
        return self in {
            OrderState.CANCELED,
            OrderState.FILLED,
            OrderState.REJECTED,
        }

# -----------------------------------------------------------------------------

class OrderType(StrEnum):
    """Enforces structural routing parameter limitations for orders executions."""
    MARKET = 'MARKET'
    LIMIT = 'LIMIT'
    STOP = 'STOP'

# -----------------------------------------------------------------------------

class PositionSide(StrEnum):
    """Direction of an active financial exposure open on the market."""
    LONG = 'LONG'
    SHORT = 'SHORT'

# -----------------------------------------------------------------------------

class TimeInForce(StrEnum):
    """Enforces execution expiration boundaries across broker gateways."""
    DAY = 'DAY'
    GTC = 'GTC'
    IOC = 'IOC'

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
