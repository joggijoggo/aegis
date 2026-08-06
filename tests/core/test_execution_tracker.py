"""Aegis Framework - Unit tests for the core execution tracking ledger.

Validates execution lifecycles, tracking group updates, and bot isolation bounds.
"""

import pytest

from core.exceptions import NettingRestrictionError
from core.execution_tracker import ExecutionTracker
from core.models import (
    OrderSide,
)
from tests.testutils import create_order_factory

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_execution_tracker_initialization_state() -> None:
    """Verify that the tracker initializes empty and reports no active executions."""
    tracker = ExecutionTracker()

    assert not tracker.has_active_execution('BOT_TEST_A')

# -----------------------------------------------------------------------------

def test_execution_tracker_register_order_without_brackets() -> None:
    """Verify registration of a root order without brackets creates a single-item group."""
    tracker = ExecutionTracker()
    domain_order = create_order_factory(
        client_order_id="ORDER_123",
        stop_loss_price=None,
        take_profit_price=None,
    )

    assert not tracker.has_active_execution('BOT_TEST_A')

    tracker.register_order('BOT_TEST_A', domain_order)

    assert tracker.has_active_execution('BOT_TEST_A')

# -----------------------------------------------------------------------------

def test_execution_tracker_register_order_with_brackets() -> None:
    """Verify registration of a buy order with brackets generates SL and TP children."""
    tracker = ExecutionTracker()
    domain_order = create_order_factory(
        client_order_id="ORDER_123",
        side=OrderSide.BUY,
        stop_loss_price=90.0,
        take_profit_price=110.0,
    )

    assert not tracker.has_active_execution('BOT_TEST_A')

    tracker.register_order('BOT_TEST_A', domain_order)

    assert tracker.has_active_execution('BOT_TEST_A')

# -----------------------------------------------------------------------------

def test_execution_tracker_register_order_violates_netting_restriction() -> None:
    """Verify that registering an order for a bot with an active execution raises an error."""
    tracker = ExecutionTracker()
    order_a = create_order_factory(client_order_id='ORDER_A')
    order_b = create_order_factory(client_order_id='ORDER_B')

    tracker.register_order('BOT_TEST_A', order_a)

    with pytest.raises(NettingRestrictionError) as exc_info:
        tracker.register_order('BOT_TEST_A', order_b)

    assert 'Netting rule restriction' in str(exc_info.value)

# -----------------------------------------------------------------------------

def test_execution_tracker_enforces_strict_bot_isolation() -> None:
    """Verify that active executions are completely isolated across individual bot identifiers."""
    tracker = ExecutionTracker()
    domain_order = create_order_factory(client_order_id='ORDER_123')

    tracker.register_order('BOT_TEST_A', domain_order)

    assert tracker.has_active_execution('BOT_TEST_A')
    assert not tracker.has_active_execution('BOT_TEST_B')

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
