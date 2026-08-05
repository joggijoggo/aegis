"""Aegis Framework - Order Group Domain Unit Tests.

Verifies the comprehensive behavioral integrity, state transition matrices,
and invariant enforcement guardrails of the order group domain aggregate.
"""

from core.models import (
    OrderGroupState,
    OrderState,
)
from core.order_group import OrderGroup

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_order_group_matrices_coverage() -> None:
    """Verifies that all possible state combinations are explicitly mapped in class matrices."""
    # Isolate valid execution states by extracting the unsupported infrastructure frames
    valid_order_states = [
        state for state in OrderState
        if state not in OrderGroup._UNSUPPORTED_STATES
    ]

    # Enforce absolute coverage mapping for the parent entrance matrix layout
    for group_state in OrderGroupState:
        for order_state in valid_order_states:
            assert group_state in OrderGroup._PARENT_MATRIX, (
                f'Missing parent matrix root mapping for group state: {group_state}'
            )
            assert order_state in OrderGroup._PARENT_MATRIX[group_state], (
                f'Missing parent matrix transition definition for '
                f'[{group_state}][{order_state}]'
            )

    # Enforce absolute coverage mapping for the child protection matrix layout
    for group_state in OrderGroupState:
        for order_state in valid_order_states:
            assert group_state in OrderGroup._CHILD_MATRIX, (
                f'Missing child matrix root mapping for group state: {group_state}'
            )
            assert order_state in OrderGroup._CHILD_MATRIX[group_state], (
                f'Missing child matrix transition definition for '
                f'[{group_state}][{order_state}]'
            )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
