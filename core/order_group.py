"""Aegis Framework - Order Group Execution Container.

Handles and tracks volatile transactional execution context records, encapsulating
the state management, validation guardrails, and transition rules governing
bracket trading lifecycles.
"""

from dataclasses import dataclass

from core.models import (
    Order,
    OrderGroupState,
    OrderState,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

@dataclass
class OrderGroup:
    """Tracking container maintaining volatile execution context records.

    Attributes:
        clearing_closed: Boolean flag confirming asset ledger inventory is flat.
        group_id: Unique internal tracking identifier for the parent group.
        order_states: Live lifecycle tracking state mapping for each order ID.
        orders: Immutable technical specification records for each order ID.
        state: Aggregated execution lifecycle state of the entire bracket.
    """
    clearing_closed: bool
    group_id: str
    order_states: dict[str, OrderState]
    orders: dict[str, Order]
    state: OrderGroupState

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
