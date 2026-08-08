"""Aegis Framework - Order Group Domain Unit Tests.

Verifies the comprehensive behavioral integrity, state transition matrices,
and invariant enforcement guardrails of the order group domain aggregate.
"""

from decimal import Decimal

import pytest

from core.exceptions import (
    ClearingCorruptionError,
    CorruptedOrderGroupError,
    NettingRestrictionError,
    UntrackedOrderException,
)
from core.models import (
    OrderGroupState,
    OrderReceipt,
    OrderSide,
    OrderState,
    OrderType,
)
from core.order_group import OrderGroup
from tests.testutils import (
    create_order_factory,
    create_order_receipt_factory,
    create_trade_receipt_factory,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

# ---[ TEST INITIALIZATION

# -----------------------------------------------------------------------------

def test_order_group_initialization_nominal_topologies() -> None:
    """Verifies that the constructor maps indices and defaults across topologies."""
    # Scenario A: Parent with full protective bracket sub-orders via factories
    parent_order = create_order_factory(
        client_order_id='ORD-FULL',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        stop_loss_price=Decimal('1.0800'),
        take_profit_price=Decimal('1.0950'),
    )
    sl_order = create_order_factory(
        client_order_id='ORD-FULL-SL',
        side=OrderSide.SELL,
        order_type=OrderType.STOP,
        price=Decimal('1.0800'),
    )
    tp_order = create_order_factory(
        client_order_id='ORD-FULL-TP',
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        price=Decimal('1.0950'),
    )

    orders_collection = [parent_order, sl_order, tp_order]
    group = OrderGroup(parent_id='ORD-FULL', orders=orders_collection)

    # Validate absolute internal encapsulation parameters
    assert group._parent_id == 'ORD-FULL'
    assert group.state == OrderGroupState.PENDING
    assert group._clearing_closed is None  # Verify neutral 3-state baseline
    assert not group.is_terminal()

    # Verify technical specification index records mapping
    assert len(group._orders) == 3
    assert group._orders['ORD-FULL'] == parent_order
    assert group._orders['ORD-FULL-SL'] == sl_order
    assert group._orders['ORD-FULL-TP'] == tp_order

    # Verify transactional state tracking ledger birth values
    assert len(group._order_states) == 3
    assert group._order_states['ORD-FULL'] == OrderState.PENDING
    assert group._order_states['ORD-FULL-SL'] == OrderState.PENDING
    assert group._order_states['ORD-FULL-TP'] == OrderState.PENDING

# -----------------------------------------------------------------------------

def test_order_group_initialization_defensive_orphan_barrier() -> None:
    """Ensures constructor triggers a ValueError if parent_id is missing."""
    orphan_child = create_order_factory(client_order_id='ORD-CHILD')

    # Enforce birth invariant protection via explicit value matching check
    with pytest.raises(ValueError, match='Initialization failed: parent order'):
        OrderGroup(parent_id='ORD-WRONG-PARENT', orders=[orphan_child])

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

# ---[ TEST ORDER NOTIFICATION

# -----------------------------------------------------------------------------

def test_order_group_unsupported_states_circuit_breaker() -> None:
    """Verifies that unhandled infrastructure states trigger corruption and a crash."""
    parent_order = create_order_factory(client_order_id='ORD-01')

    for unsupported_state in OrderGroup._UNSUPPORTED_STATES:
        group = OrderGroup(parent_id='ORD-01', orders=[parent_order])
        receipt = create_order_receipt_factory(
            group_id='ORD-01',
            client_order_id='ORD-01',
            state=unsupported_state,
        )

        # Invariant: Must mutate to CORRUPTED and raise NotImplementedError
        with pytest.raises(NotImplementedError, match='not supported in the current framework'):
            group.notify_order_change(receipt)

        assert group.state == OrderGroupState.CORRUPTED

# -----------------------------------------------------------------------------

def test_order_group_untracked_identity_circuit_breaker() -> None:
    """Ensures unrecognized order identifiers trigger an untracked exception."""
    parent_order = create_order_factory(client_order_id='ORD-01')
    group = OrderGroup(parent_id='ORD-01', orders=[parent_order])
    receipt = create_order_receipt_factory(
        group_id='ORD-01',
        client_order_id='GHOST-ID',
        state=OrderState.FILLED,
    )

    with pytest.raises(UntrackedOrderException, match='not found in group'):
        group. notify_order_change(receipt)

    # Validate that no internal metrics have experienced drift
    assert group.state == OrderGroupState.PENDING
    assert group._order_states['ORD-01'] == OrderState.PENDING

# -----------------------------------------------------------------------------

def test_order_group_corrupted_state_denies_mutations() -> None:
    """Ensures living aggregates lock completely once state moves to corrupted."""
    parent_order = create_order_factory(client_order_id='ORD-CORRUPT')
    group = OrderGroup(parent_id='ORD-CORRUPT', orders=[parent_order])

    # Force the group into a CORRUPTED state via an unsupported event
    receipt_unsupported = create_order_receipt_factory(
        group_id='ORD-CORRUPT',
        client_order_id='ORD-CORRUPT',
        state=OrderState.PARTIALLY_FILLED,
    )
    with pytest.raises(NotImplementedError):
        group.notify_order_change(receipt_unsupported)
    assert group.state == OrderGroupState.CORRUPTED

    # Assert order change mutations are now strictly blocked
    receipt_late = create_order_receipt_factory(
        group_id='ORD-CORRUPT',
        client_order_id='ORD-CORRUPT',
        state=OrderState.FILLED,
    )
    with pytest.raises(CorruptedOrderGroupError, match='is corrupted'):
        group.notify_order_change(receipt_late)

    # Assert trade change mutations are also strictly blocked
    trade_receipt = create_trade_receipt_factory(
        group_id='ORD-CORRUPT',
        is_open=True,
    )
    with pytest.raises(CorruptedOrderGroupError, match='is corrupted'):
        group.notify_trade_change(trade_receipt)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

# ---[ TEST TRADE NOTIFICATION

# -----------------------------------------------------------------------------

def test_order_group_clearing_witness_lifecycle() -> None:
    """Verifies the three-state transitions of the clearing closed record witness."""
    parent_order = create_order_factory(client_order_id='O-ACC1')
    group = OrderGroup(parent_id='O-ACC1', orders=[parent_order])

    # Invariant 1: Birth state must resolve to net neutral None
    assert group._clearing_closed is None

    # Invariant 2: Broker open exposure event drives witness to False
    group.notify_trade_change(create_trade_receipt_factory(group_id='O-ACC1', is_open=True))
    assert group._clearing_closed is False

    # Invariant 3: Broker close exposure event drives witness to True
    group.notify_trade_change(create_trade_receipt_factory(group_id='O-ACC1', is_open=False))
    assert group._clearing_closed is True

# -----------------------------------------------------------------------------

def test_order_group_clandestine_closure_forensic_detection() -> None:
    """Ensures external manual intervention triggers an immediate corruption state."""
    parent_order = create_order_factory(client_order_id='O-ACC2')
    sl_order = create_order_factory(client_order_id='O-ACC2-SL')

    group = OrderGroup(parent_id='O-ACC2', orders=[parent_order, sl_order])

    # Push to ACTIVE state via parent fill notification
    group.notify_order_change(create_order_receipt_factory(
        group_id='O-ACC2', client_order_id='O-ACC2', state=OrderState.FILLED
    ))
    assert group.state == OrderGroupState.ACTIVE

    # Inflict flat trade receipt without any child protective order being filled
    with pytest.raises(CorruptedOrderGroupError):
        group.notify_trade_change(
            create_trade_receipt_factory(group_id='O-ACC2', is_open=False)
    )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

# ---[ ACCESSORS

# -----------------------------------------------------------------------------

def test_order_group_retrieves_parent_order_nominally() -> None:
    """Verify that get_parent_order returns the root order anchoring the group."""
    parent_order = create_order_factory(client_order_id='ORDER_ROOT_123')
    order_group = OrderGroup(parent_id='ORDER_ROOT_123', orders=[parent_order])

    extracted_order = order_group.get_parent_order()

    assert extracted_order.client_order_id == 'ORDER_ROOT_123'
    assert extracted_order == parent_order

# -----------------------------------------------------------------------------

def test_order_group_allows_liquidation_in_nominal_active_state() -> None:
    """Verify that a nominal active group with open exposure permits market liquidation."""
    parent_order = create_order_factory(client_order_id='ORDER_123')
    order_group = OrderGroup(parent_id='ORDER_123', orders=[parent_order])

    order_group.notify_order_change(create_order_receipt_factory(
        client_order_id='ORDER_123', state=OrderState.FILLED,
    ))

    order_group.notify_trade_change(create_trade_receipt_factory(
        group_id='ORDER_123', is_open=True,
    ))

    assert order_group.is_closable()
    assert not order_group.is_cancelable()

# -----------------------------------------------------------------------------

def test_order_group_denies_liquidation_on_closed_clearing_race_condition() -> None:
    """Verify that liquidation is barred if clearing closes before book updates state."""
    order_group = OrderGroup(
        parent_id='ORDER_123',
        orders=[create_order_factory(client_order_id='ORDER_123')],
    )

    parent_receipt = create_order_receipt_factory(
        group_id='ORDER_123',
        client_order_id='ORDER_123',
        state=OrderState.FILLED,
        executed_quantity=Decimal('10.0'),
        average_execution_price=Decimal('100.0'),
    )
    order_group.notify_order_change(parent_receipt)

    # Attach exit order to authorize the incoming flat trade clearing packet
    exit_order = create_order_factory(
        client_order_id='ORDER_123-XT',
        side=OrderSide.SELL,
    )
    order_group.attach_exit_order(exit_order)

    trade_receipt = create_trade_receipt_factory(
        group_id='ORDER_123',
        is_open=False,
    )
    order_group.notify_trade_change(trade_receipt)

    assert not order_group.is_closable()

# -----------------------------------------------------------------------------

def test_order_group_denies_liquidation_while_already_closing() -> None:
    """Verify that liquidation commands are rejected if an exit order is present."""
    order_group = OrderGroup(
        parent_id='O1',
        orders=[create_order_factory(client_order_id='O1')],
    )

    parent_receipt = create_order_receipt_factory(
        group_id='O1',
        client_order_id='O1',
        state=OrderState.FILLED,
        executed_quantity=Decimal('10.0'),
        average_execution_price=Decimal('100.0'),
    )
    order_group.notify_order_change(parent_receipt)

    exit_order = create_order_factory(client_order_id='O1-XT')
    order_group.attach_exit_order(exit_order)

    assert not order_group.is_closable()

# -----------------------------------------------------------------------------

def test_order_group_denies_nominal_liquidation_while_corrupted() -> None:
    """Verify that liquidation is flatly rejected if the group is corrupted."""
    order_group = OrderGroup(
        parent_id='O1',
        orders=[create_order_factory(client_order_id='O1')],
    )

    order_group._is_corrupted = True

    assert not order_group.is_closable()

# -----------------------------------------------------------------------------

def test_order_group_denies_cancellation_in_active_state() -> None:
    """Verify that a classical cancellation request is barred once the group is active."""
    order_group = OrderGroup(
        parent_id='ORDER_123',
        orders=[create_order_factory(client_order_id='ORDER_123')],
    )

    parent_receipt = create_order_receipt_factory(
        group_id='ORDER_123',
        client_order_id='ORDER_123',
        state=OrderState.FILLED,
        executed_quantity=Decimal('10.0'),
        average_execution_price=Decimal('100.0'),
    )
    order_group.notify_order_change(parent_receipt)

    assert not order_group.is_cancelable()

# -----------------------------------------------------------------------------

def test_order_group_denies_cancellation_while_already_closing() -> None:
    """Verify that cancellation is barred if the group has transitioned to CLOSING."""
    order_group = OrderGroup(
        parent_id='ORDER_123',
        orders=[create_order_factory(client_order_id='ORDER_123')],
    )

    parent_receipt = create_order_receipt_factory(
        group_id='ORDER_123',
        client_order_id='ORDER_123',
        state=OrderState.FILLED,
        executed_quantity=Decimal('10.0'),
        average_execution_price=Decimal('100.0'),
    )
    order_group.notify_order_change(parent_receipt)

    exit_order = create_order_factory(
        client_order_id='ORDER_123-XT',
        side=OrderSide.SELL,
    )
    order_group.attach_exit_order(exit_order)

    exit_receipt = create_order_receipt_factory(
        group_id='ORDER_123',
        client_order_id='ORDER_123-XT',
        state=OrderState.FILLED,
        executed_quantity=Decimal('10.0'),
        average_execution_price=Decimal('100.0'),
    )
    order_group.notify_order_change(exit_receipt)

    assert not order_group.is_cancelable()

# -----------------------------------------------------------------------------

def test_order_group_denies_cancellation_in_terminal_rejected_state() -> None:
    """Verify that a cancellation command is barred if the group is already rejected."""
    order_group = OrderGroup(
        parent_id='ORDER_123',
        orders=[create_order_factory(client_order_id='ORDER_123')],
    )

    reject_receipt = create_order_receipt_factory(
        group_id='ORDER_123',
        client_order_id='ORDER_123',
        state=OrderState.REJECTED,
        executed_quantity=Decimal('0.0'),
        average_execution_price=None,
    )
    order_group.notify_order_change(reject_receipt)

    assert not order_group.is_cancelable()

# -----------------------------------------------------------------------------

def test_order_group_is_closable_returns_false_when_corrupted() -> None:
    """Verify that a corrupted group state flatly blocks the closable check."""
    order_group = OrderGroup(
        parent_id='O1',
        orders=[create_order_factory(client_order_id='O1')],
    )

    # 1. Open exposure via parent fill to pass the physical balance check
    parent_receipt = create_order_receipt_factory(
        group_id='O1',
        client_order_id='O1',
        state=OrderState.FILLED,
        executed_quantity=Decimal('10.0'),
        average_execution_price=Decimal('100.0'),
    )
    order_group.notify_order_change(parent_receipt)

    # 2. Trigger the unifed safety circuit breaker
    order_group._is_corrupted = True

    # Invariant: State is CORRUPTED, which triggers the invalid state guard
    assert order_group.state == OrderGroupState.CORRUPTED
    assert order_group.is_closable() is False

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_attach_exit_order_nominal():
    """Verify clean attachment under nominal conditions."""
    parent_order = create_order_factory(client_order_id='ORD_123')
    group = OrderGroup(parent_id='ORD_123', orders=[parent_order])

    exit_order = create_order_factory(client_order_id='ORD_123-XT')

    assert group._exit_order_id is None

    group.attach_exit_order(exit_order)
    assert group._exit_order_id is exit_order.client_order_id

# -----------------------------------------------------------------------------

def test_attach_exit_order_duplicate_raises():
    """Verify subsequent attachments trigger a netting error."""
    parent_order = create_order_factory(client_order_id='ORD_123')
    group = OrderGroup(parent_id='ORD_123', orders=[parent_order])

    exit_1 = create_order_factory(client_order_id='ORD_123-XT')
    exit_2 = create_order_factory(client_order_id='ORD_123-XT2')

    group.attach_exit_order(exit_1)

    assert group._orders[group._exit_order_id] is exit_1

    expected_msg = 'is already registered for group "ORD_123".'
    with pytest.raises(NettingRestrictionError, match=expected_msg):
        group.attach_exit_order(exit_2)

# -----------------------------------------------------------------------------

def test_attach_exit_order_identity_conflict_raises():
    """Verify identity collisions trigger a value error."""
    parent_order = create_order_factory(client_order_id='ORD_123')
    group = OrderGroup(parent_id='ORD_123', orders=[parent_order])

    conflicting_exit = create_order_factory(client_order_id='ORD_123')

    assert group._exit_order_id is None

    expected_msg = (
        'Order ID "ORD_123" conflicts with an '
        'existing order in group.'
    )
    with pytest.raises(ValueError, match=expected_msg):
        group.attach_exit_order(conflicting_exit)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_order_group_routes_parent_fill_to_ledger() -> None:
    """Verify that a nominal parent execution fill updates the inner ledger."""
    parent_order = create_order_factory(
        client_order_id='ORD_PARENT',
        side=OrderSide.BUY,
    )
    group = OrderGroup(parent_id='ORD_PARENT', orders=[parent_order])

    assert group.ledger.position_size == Decimal('0.0')

    receipt = OrderReceipt(
        client_order_id='ORD_PARENT',
        group_id='ORD_PARENT',
        state='FILLED',
        executed_quantity=Decimal('10.0'),
        average_execution_price=Decimal('100.0'),
        broker_order_id='B_01',
        reject_reason=None,
    )

    group.notify_order_change(receipt)

    assert group.ledger.position_size == Decimal('10.0')
    assert group.ledger.average_price == Decimal('100.0')

# -----------------------------------------------------------------------------

def test_order_group_routes_exit_order_fill_to_ledger() -> None:
    """Verify that an exit ticket fill bypasses filters and clears exposure."""
    parent_order = create_order_factory(
        client_order_id='ORD_PARENT',
        side=OrderSide.BUY,
    )
    group = OrderGroup(parent_id='ORD_PARENT', orders=[parent_order])

    # Execute parent order to satisfy legacy matrix and open exposure
    parent_receipt = OrderReceipt(
        client_order_id='ORD_PARENT',
        group_id='ORD_PARENT',
        state='FILLED',
        executed_quantity=Decimal('10.0'),
        average_execution_price=Decimal('100.0'),
        broker_order_id='B_01',
        reject_reason=None,
    )
    group.notify_order_change(parent_receipt)

    assert group.ledger.position_size == Decimal('10.0')
    assert group.ledger.realized_pnl == Decimal('0.0')

    # Attach and execute the exit order to clear physical exposure
    exit_order = create_order_factory(
        client_order_id='ORD_PARENT-XT',
        side=OrderSide.SELL,
    )
    group.attach_exit_order(exit_order)

    exit_receipt = OrderReceipt(
        client_order_id='ORD_PARENT-XT',
        group_id='ORD_PARENT',
        state='FILLED',
        executed_quantity=Decimal('10.0'),
        average_execution_price=Decimal('110.0'),
        broker_order_id='B_02',
        reject_reason=None,
    )
    group.notify_order_change(exit_receipt)

    assert group.ledger.position_size == Decimal('0.0')
    assert group.ledger.realized_pnl == Decimal('100.0')

# -----------------------------------------------------------------------------

def test_order_group_missing_price_raises_clearing_corruption() -> None:
    """Verify that execution volume without a price triggers a fault routing."""
    parent_order = create_order_factory(
        client_order_id='ORD_PARENT',
        side=OrderSide.BUY,
    )
    group = OrderGroup(parent_id='ORD_PARENT', orders=[parent_order])

    receipt = OrderReceipt(
        client_order_id='ORD_PARENT',
        group_id='ORD_PARENT',
        state='FILLED',
        executed_quantity=Decimal('5.0'),
        average_execution_price=None,
        broker_order_id='B_03',
        reject_reason=None,
    )

    expected_pattern = 'volume-weighted execution price was missing'
    with pytest.raises(ClearingCorruptionError, match=expected_pattern):
        group.notify_order_change(receipt)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

@pytest.mark.parametrize(
    'terminal_state',
    [
        OrderState.REJECTED,
        OrderState.CANCELED,
    ],
)
def test_order_group_circuit_breaker_locks_on_exit_order_failure(
    terminal_state: OrderState,
) -> None:
    """Verify that an exit failure triggers a corrupted state disjunction."""
    parent_order = create_order_factory(
        client_order_id='ORD_PARENT',
        side=OrderSide.BUY,
    )
    group = OrderGroup(parent_id='ORD_PARENT', orders=[parent_order])

    # Open position at the ledger and satisfy legacy matrix initialization
    parent_receipt = OrderReceipt(
        client_order_id='ORD_PARENT',
        group_id='ORD_PARENT',
        state=OrderState.FILLED,
        executed_quantity=Decimal('10.0'),
        average_execution_price=Decimal('100.0'),
        broker_order_id='B_01',
        reject_reason=None,
    )
    group.notify_order_change(parent_receipt)

    # Attach the exit order that will fail to execute
    exit_order = create_order_factory(
        client_order_id='ORD_PARENT-XT',
        side=OrderSide.SELL,
    )
    group.attach_exit_order(exit_order)

    exit_receipt = OrderReceipt(
        client_order_id='ORD_PARENT-XT',
        group_id='ORD_PARENT',
        state=terminal_state,
        executed_quantity=Decimal('0.0'),
        average_execution_price=None,
        broker_order_id='B_02',
        reject_reason='Venue execution failure infrastructure fault',
    )
    group.notify_order_change(exit_receipt)

    # Validate fail-fast protection and structural storage isolation
    assert group.state == OrderGroupState.CORRUPTED
    assert 'ORD_PARENT-XT' in group._order_states
    assert group._order_states['ORD_PARENT-XT'] == terminal_state

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_computed_state_prioritizes_corruption_guard() -> None:
    """Verify that the corruption flag forces CORRUPTED regardless of data."""
    parent_order = create_order_factory(
        client_order_id='ORD_PARENT',
        side=OrderSide.BUY,
    )
    group = OrderGroup(parent_id='ORD_PARENT', orders=[parent_order])

    receipt = OrderReceipt(
        client_order_id='ORD_PARENT',
        group_id='ORD_PARENT',
        state=OrderState.FILLED,
        executed_quantity=Decimal('10.0'),
        average_execution_price=Decimal('100.0'),
        broker_order_id='B_01',
        reject_reason=None,
    )
    group.notify_order_change(receipt)

    group._is_corrupted = True

    assert group.state == OrderGroupState.CORRUPTED

# -----------------------------------------------------------------------------

def test_computed_state_returns_pending_on_initial_setup() -> None:
    """Verify that a flat group with a pending parent evaluates to PENDING."""
    parent_order = create_order_factory(
        client_order_id='ORD_PARENT',
        side=OrderSide.BUY,
    )
    group = OrderGroup(parent_id='ORD_PARENT', orders=[parent_order])

    receipt = OrderReceipt(
        client_order_id='ORD_PARENT',
        group_id='ORD_PARENT',
        state=OrderState.PENDING,
        executed_quantity=Decimal('0.0'),
        average_execution_price=None,
        broker_order_id='B_01',
        reject_reason=None,
    )
    group.notify_order_change(receipt)

    assert group.state == OrderGroupState.PENDING

# -----------------------------------------------------------------------------

def test_computed_state_returns_active_on_open_exposure() -> None:
    """Verify that an open physical position evaluates to ACTIVE."""
    parent_order = create_order_factory(
        client_order_id='ORD_PARENT',
        side=OrderSide.BUY,
    )
    group = OrderGroup(parent_id='ORD_PARENT', orders=[parent_order])

    receipt = OrderReceipt(
        client_order_id='ORD_PARENT',
        group_id='ORD_PARENT',
        state=OrderState.FILLED,
        executed_quantity=Decimal('10.0'),
        average_execution_price=Decimal('100.0'),
        broker_order_id='B_01',
        reject_reason=None,
    )
    group.notify_order_change(receipt)

    assert group.state == OrderGroupState.ACTIVE

# -----------------------------------------------------------------------------

def test_computed_state_returns_closing_on_over_hedged_residual() -> None:
    """Verify that an executed exit order with residual exposure sets CLOSING."""
    parent_order = create_order_factory(
        client_order_id='ORD_PARENT',
        side=OrderSide.BUY,
    )
    group = OrderGroup(parent_id='ORD_PARENT', orders=[parent_order])

    parent_receipt = OrderReceipt(
        client_order_id='ORD_PARENT',
        group_id='ORD_PARENT',
        state=OrderState.FILLED,
        executed_quantity=Decimal('10.0'),
        average_execution_price=Decimal('100.0'),
        broker_order_id='B_01',
        reject_reason=None,
    )
    group.notify_order_change(parent_receipt)

    exit_order = create_order_factory(
        client_order_id='ORD_PARENT-XT',
        side=OrderSide.SELL,
    )
    group.attach_exit_order(exit_order)

    exit_receipt = OrderReceipt(
        client_order_id='ORD_PARENT-XT',
        group_id='ORD_PARENT',
        state=OrderState.FILLED,
        executed_quantity=Decimal('15.0'),
        average_execution_price=Decimal('105.0'),
        broker_order_id='B_02',
        reject_reason=None,
    )
    group.notify_order_change(exit_receipt)

    assert group.state == OrderGroupState.CLOSING

# -----------------------------------------------------------------------------

def test_computed_state_returns_closing_when_awaiting_child_purges() -> None:
    """Verify that a flat group awaiting child cancellations evaluates to CLOSING."""
    parent_order = create_order_factory(
        client_order_id='ORD_PARENT',
        side=OrderSide.BUY,
    )
    # Inject a child order to simulate a protection remaining in the book
    child_order = create_order_factory(
        client_order_id='ORD_CHILD_SL',
        side=OrderSide.SELL,
    )
    group = OrderGroup(
        parent_id='ORD_PARENT',
        orders=[parent_order, child_order],
    )

    parent_receipt = OrderReceipt(
        client_order_id='ORD_PARENT',
        group_id='ORD_PARENT',
        state=OrderState.FILLED,
        executed_quantity=Decimal('10.0'),
        average_execution_price=Decimal('100.0'),
        broker_order_id='B_01',
        reject_reason=None,
    )
    group.notify_order_change(parent_receipt)

    exit_order = create_order_factory(
        client_order_id='ORD_PARENT-XT',
        side=OrderSide.SELL,
    )
    group.attach_exit_order(exit_order)

    exit_receipt = OrderReceipt(
        client_order_id='ORD_PARENT-XT',
        group_id='ORD_PARENT',
        state=OrderState.FILLED,
        executed_quantity=Decimal('10.0'),
        average_execution_price=Decimal('100.0'),
        broker_order_id='B_02',
        reject_reason=None,
    )
    group.notify_order_change(exit_receipt)

    # Flat position but child_order is still PENDING: must evaluate to CLOSING
    assert group.state == OrderGroupState.CLOSING

# -----------------------------------------------------------------------------

def test_computed_state_returns_completed_when_all_orders_terminal() -> None:
    """Verify that a flat group with all orders terminal evaluates to COMPLETED."""
    parent_order = create_order_factory(
        client_order_id='ORD_PARENT',
        side=OrderSide.BUY,
    )
    # Inject a child order to simulate a protection bracket setup
    child_order = create_order_factory(
        client_order_id='ORD_CHILD_SL',
        side=OrderSide.SELL,
    )
    group = OrderGroup(
        parent_id='ORD_PARENT',
        orders=[parent_order, child_order],
    )

    parent_receipt = OrderReceipt(
        client_order_id='ORD_PARENT',
        group_id='ORD_PARENT',
        state=OrderState.FILLED,
        executed_quantity=Decimal('10.0'),
        average_execution_price=Decimal('100.0'),
        broker_order_id='B_01',
        reject_reason=None,
    )
    group.notify_order_change(parent_receipt)

    exit_order = create_order_factory(
        client_order_id='ORD_PARENT-XT',
        side=OrderSide.SELL,
    )
    group.attach_exit_order(exit_order)

    exit_receipt = OrderReceipt(
        client_order_id='ORD_PARENT-XT',
        group_id='ORD_PARENT',
        state=OrderState.FILLED,
        executed_quantity=Decimal('10.0'),
        average_execution_price=Decimal('100.0'),
        broker_order_id='B_02',
        reject_reason=None,
    )
    group.notify_order_change(exit_receipt)

    # Simulate broker confirming the cancellation of the protection order
    child_receipt = OrderReceipt(
        client_order_id='ORD_CHILD_SL',
        group_id='ORD_PARENT',
        state=OrderState.CANCELED,
        executed_quantity=Decimal('0.0'),
        average_execution_price=None,
        broker_order_id='B_03',
        reject_reason=None,
    )
    group.notify_order_change(child_receipt)

    assert group.state == OrderGroupState.COMPLETED

# -----------------------------------------------------------------------------

def test_computed_state_returns_rejected_on_parent_failure() -> None:
    """Verify that a rejected parent entry order evaluates to REJECTED."""
    parent_order = create_order_factory(
        client_order_id='ORD_PARENT',
        side=OrderSide.BUY,
    )
    group = OrderGroup(parent_id='ORD_PARENT', orders=[parent_order])

    receipt = OrderReceipt(
        client_order_id='ORD_PARENT',
        group_id='ORD_PARENT',
        state=OrderState.REJECTED,
        executed_quantity=Decimal('0.0'),
        average_execution_price=None,
        broker_order_id='B_01',
        reject_reason='Margin insufficiency fault',
    )
    group.notify_order_change(receipt)

    assert group.state == OrderGroupState.REJECTED

# -----------------------------------------------------------------------------

def test_computed_state_returns_canceled_on_parent_abort() -> None:
    """Verify that a canceled parent entry order evaluates to CANCELED."""
    parent_order = create_order_factory(
        client_order_id='ORD_PARENT',
        side=OrderSide.BUY,
    )
    group = OrderGroup(parent_id='ORD_PARENT', orders=[parent_order])

    receipt = OrderReceipt(
        client_order_id='ORD_PARENT',
        group_id='ORD_PARENT',
        state=OrderState.CANCELED,
        executed_quantity=Decimal('0.0'),
        average_execution_price=None,
        broker_order_id='B_01',
        reject_reason=None,
    )
    group.notify_order_change(receipt)

    assert group.state == OrderGroupState.CANCELED

# -----------------------------------------------------------------------------

def test_computed_state_returns_closing_on_nominal_protection_fill() -> None:
    """Verify that a filled protection order with pending sibling sets CLOSING."""
    parent_order = create_order_factory(
        client_order_id='ORD_PARENT',
        side=OrderSide.BUY,
    )
    child_sl = create_order_factory(
        client_order_id='ORD_CHILD_SL',
        side=OrderSide.SELL,
    )
    child_tp = create_order_factory(
        client_order_id='ORD_CHILD_TP',
        side=OrderSide.SELL,
    )
    group = OrderGroup(
        parent_id='ORD_PARENT',
        orders=[parent_order, child_sl, child_tp],
    )

    parent_receipt = OrderReceipt(
        client_order_id='ORD_PARENT',
        group_id='ORD_PARENT',
        state=OrderState.FILLED,
        executed_quantity=Decimal('10.0'),
        average_execution_price=Decimal('100.0'),
        broker_order_id='B_01',
        reject_reason=None,
    )
    group.notify_order_change(parent_receipt)

    # Enforce the market hit on the Stop-Loss order to flatten exposure
    sl_receipt = OrderReceipt(
        client_order_id='ORD_CHILD_SL',
        group_id='ORD_PARENT',
        state=OrderState.FILLED,
        executed_quantity=Decimal('10.0'),
        average_execution_price=Decimal('95.0'),
        broker_order_id='B_02',
        reject_reason=None,
    )
    group.notify_order_change(sl_receipt)

    # Flat ledger but pending Take-Profit sibling must trigger CLOSING state
    assert group.state == OrderGroupState.CLOSING

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
