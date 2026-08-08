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
    assert group._state == OrderGroupState.PENDING
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

        assert group._state == OrderGroupState.CORRUPTED

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
    assert group._state == OrderGroupState.PENDING
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
    assert group._state == OrderGroupState.CORRUPTED

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

# -----------------------------------------------------------------------------

def test_order_group_nominal_transition_sequences() -> None:
    """Tracks step-by-step structural mutations across complete and bare topologies."""
    # Sub-case A: Complete bracket sequence tracking
    parent_order = create_order_factory(client_order_id='O-BRK')
    sl_order = create_order_factory(client_order_id='O-BRK-SL')
    tp_order = create_order_factory(client_order_id='O-BRK-TP')

    group_full = OrderGroup(parent_id='O-BRK', orders=[parent_order, sl_order, tp_order])

    # 1. Parent fulfillment triggers active market exposure mapping
    group_full.notify_order_change(create_order_receipt_factory(
        group_id='O-BRK', client_order_id='O-BRK', state=OrderState.FILLED
    ))
    assert group_full._state == OrderGroupState.ACTIVE
    assert group_full._order_states['O-BRK'] == OrderState.FILLED
    assert group_full._order_states['O-BRK-SL'] == OrderState.PENDING
    assert group_full._order_states['O-BRK-TP'] == OrderState.PENDING

    # 2. Child protective fill shifts lifecycle toward closing sequester
    group_full.notify_order_change(create_order_receipt_factory(
        group_id='O-BRK', client_order_id='O-BRK-SL', state=OrderState.FILLED
    ))
    assert group_full._state == OrderGroupState.CLOSING
    assert group_full._order_states['O-BRK-SL'] == OrderState.FILLED

    # Sub-case B: Bare parent execution validation
    parent_bare = create_order_factory(client_order_id='O-BARE')
    group_bare = OrderGroup(parent_id='O-BARE', orders=[parent_bare])

    group_bare.notify_order_change(create_order_receipt_factory(
        group_id='O-BARE', client_order_id='O-BARE', state=OrderState.FILLED
    ))
    assert group_bare._state == OrderGroupState.ACTIVE

# -----------------------------------------------------------------------------

def test_order_group_clean_cancellation_lifecycle() -> None:
    """Verifies transition to CANCELED when parent is canceled and children are terminal."""
    parent_order = create_order_factory(client_order_id='O-TDD')
    child_order = create_order_factory(client_order_id='O-TDD-SL')

    group = OrderGroup(parent_id='O-TDD', orders=[parent_order, child_order])

    # 1. Parent cancellation pushes the aggregate into REJECTING sequester
    group.notify_order_change(create_order_receipt_factory(
        group_id='O-TDD', client_order_id='O-TDD', state=OrderState.CANCELED
    ))
    assert group._state == OrderGroupState.REJECTING

    # 2. Child protection order returns CANCELED, triggering line 218 eviction
    group.notify_order_change(create_order_receipt_factory(
        group_id='O-TDD', client_order_id='O-TDD-SL', state=OrderState.CANCELED
    ))

    # The eviction barrier must now transition the group state to CANCELED
    assert group._state == OrderGroupState.CANCELED

# -----------------------------------------------------------------------------

def test_order_group_parent_rejection_sequester_nominal() -> None:
    """Verifies complete eviction to terminal rejected state after children cleanup."""
    parent_order = create_order_factory(client_order_id='O-REJ')
    sl_order = create_order_factory(client_order_id='O-REJ-SL')
    tp_order = create_order_factory(client_order_id='O-REJ-TP')

    group = OrderGroup(parent_id='O-REJ', orders=[parent_order, sl_order, tp_order])

    # 1. Parent failure triggers the defensive REJECTING sequester block
    group.notify_order_change(create_order_receipt_factory(
        group_id='O-REJ', client_order_id='O-REJ', state=OrderState.REJECTED
    ))
    assert group._state == OrderGroupState.REJECTING
    assert not group.is_terminal()

    # 2. First child cancellation leaves aggregate in sequester
    group.notify_order_change(create_order_receipt_factory(
        group_id='O-REJ', client_order_id='O-REJ-SL', state=OrderState.CANCELED
    ))
    assert group._state == OrderGroupState.REJECTING
    assert not group.is_terminal()

    # 3. Final child cancellation satisfies barrier, resolving to terminal REJECTED
    group.notify_order_change(create_order_receipt_factory(
        group_id='O-REJ', client_order_id='O-REJ-TP', state=OrderState.CANCELED
    ))
    assert group._state == OrderGroupState.REJECTED
    assert group.is_terminal()

# -----------------------------------------------------------------------------

def test_order_group_child_rejection_during_sequester() -> None:
    """Verifies the behavior when a child order returns REJECTED during a sequester phase."""
    parent_order = create_order_factory(client_order_id='O-TDD')
    sl_order = create_order_factory(client_order_id='O-TDD-SL')
    tp_order = create_order_factory(client_order_id='O-TDD-TP')

    group = OrderGroup(parent_id='O-TDD', orders=[parent_order, sl_order, tp_order])

    # 1. Parent failure pushes the aggregate into REJECTING sequester
    group.notify_order_change(create_order_receipt_factory(
        group_id='O-TDD', client_order_id='O-TDD', state=OrderState.REJECTED
    ))
    assert group._state == OrderGroupState.REJECTING

    # 2. Child protective order returns REJECTED instead of CANCELED
    group.notify_order_change(create_order_receipt_factory(
        group_id='O-TDD', client_order_id='O-TDD-SL', state=OrderState.REJECTED
    ))

    assert group._state == OrderGroupState.REJECTING

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
    assert group._state == OrderGroupState.ACTIVE

    # Inflict flat trade receipt without any child protective order being filled
    with pytest.raises(CorruptedOrderGroupError):
        group.notify_trade_change(
            create_trade_receipt_factory(group_id='O-ACC2', is_open=False)
    )

# -----------------------------------------------------------------------------

def test_order_group_nominal_unwind_and_eviction_barrier() -> None:
    """Validates full lifecycle resolution to completed once final criteria are met."""
    parent_order = create_order_factory(client_order_id='O-ACC3')
    sl_order = create_order_factory(client_order_id='O-ACC3-SL')
    tp_order = create_order_factory(client_order_id='O-ACC3-TP')

    group = OrderGroup(parent_id='O-ACC3', orders=[parent_order, sl_order, tp_order])

    # 1. Establish active position footprint
    group.notify_order_change(create_order_receipt_factory(
        group_id='O-ACC3', client_order_id='O-ACC3', state=OrderState.FILLED
    ))
    group.notify_trade_change(create_trade_receipt_factory(group_id='O-ACC3', is_open=True))

    # 2. Trigger nominal stop-loss execution to initiate closing sequester
    group.notify_order_change(create_order_receipt_factory(
        group_id='O-ACC3', client_order_id='O-ACC3-SL', state=OrderState.FILLED
    ))
    assert group._state == OrderGroupState.CLOSING

    # 3. Clean up the opposite take-profit protection leg
    group.notify_order_change(create_order_receipt_factory(
        group_id='O-ACC3', client_order_id='O-ACC3-TP', state=OrderState.CANCELED
    ))
    assert not group.is_terminal()  # Order states are terminal, but clearing barrier remains open

    # 4. Supply the flat clearing receipt to drop the final barrier
    group.notify_trade_change(create_trade_receipt_factory(group_id='O-ACC3', is_open=False))

    assert group._state == OrderGroupState.COMPLETED
    assert group.is_terminal()

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

# ---[ NETWORK DESYNC

# -----------------------------------------------------------------------------

def test_order_group_early_clearing_race_condition() -> None:
    """Ensures trade updates arriving before order confirmation are absorbed cleanly."""
    parent_order = create_order_factory(client_order_id='O-DES1')
    group = OrderGroup(parent_id='O-DES1', orders=[parent_order])

    # 1. Simulate an early clearing arrival stating exposure has started
    group.notify_trade_change(create_trade_receipt_factory(group_id='O-DES1', is_open=True))

    # Verify the witness updates without corrupting the molecular lifecycle state
    assert group._clearing_closed is False
    assert group._state == OrderGroupState.PENDING

    # 2. Supply the delayed order fulfillment confirmation receipt later
    group.notify_order_change(create_order_receipt_factory(
        group_id='O-DES1', client_order_id='O-DES1', state=OrderState.FILLED
    ))

    # Invariant: The aggregate must resolve successfully to the nominal ACTIVE state
    assert group._state == OrderGroupState.ACTIVE

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

# ---[ ANOMALIES

# -----------------------------------------------------------------------------

def test_order_group_duplicate_order_receipt_corruption() -> None:
    """Ensures duplicate order fill receipts trigger an immediate corruption lock."""
    parent_order = create_order_factory(client_order_id='O-ANM1')
    group = OrderGroup(parent_id='O-ANM1', orders=[parent_order])

    # First legitimate fill transitions the molecular state to ACTIVE
    group.notify_order_change(create_order_receipt_factory(
        group_id='O-ANM1', client_order_id='O-ANM1', state=OrderState.FILLED
    ))
    assert group._state == OrderGroupState.ACTIVE

    # Malicious or broken network duplication of the exact same fill receipt
    with pytest.raises(CorruptedOrderGroupError):
        group.notify_order_change(create_order_receipt_factory(
            group_id='O-ANM1', client_order_id='O-ANM1', state=OrderState.FILLED
        ))

# -----------------------------------------------------------------------------

def test_order_group_forbidden_reopening_during_sequester() -> None:
    """Captures aggregate behavior when an exposure reopens during a closing sequester."""
    parent_order = create_order_factory(client_order_id='O-ANM2')
    sl_order = create_order_factory(client_order_id='O-ANM2-SL')
    group = OrderGroup(parent_id='O-ANM2', orders=[parent_order, sl_order])

    # 1. Establish and trigger standard closing sequester sequence
    group.notify_order_change(create_order_receipt_factory(
        group_id='O-ANM2', client_order_id='O-ANM2', state=OrderState.FILLED
    ))
    group.notify_order_change(create_order_receipt_factory(
        group_id='O-ANM2', client_order_id='O-ANM2-SL', state=OrderState.FILLED
    ))
    assert group._state == OrderGroupState.CLOSING

    # 2. Complete the clearing sequence with a flat ledger statement
    group.notify_trade_change(create_trade_receipt_factory(group_id='O-ANM2', is_open=False))
    assert group._clearing_closed is True

    # 3. Anomaly: Supply a trade receipt reopening the position context
    group.notify_trade_change(create_trade_receipt_factory(group_id='O-ANM2', is_open=True))

    # Capture state to audit if current behavior enforces corruption flags
    assert group._clearing_closed is False

# -----------------------------------------------------------------------------

def test_order_group_double_clearing_flat_on_living_aggregate() -> None:
    """Validates that duplicate flat clearing statements are absorbed harmlessly."""
    parent_order = create_order_factory(client_order_id='O-ANM3')
    sl_order = create_order_factory(client_order_id='O-ANM3-SL')
    tp_order = create_order_factory(client_order_id='O-ANM3-TP')
    group = OrderGroup(parent_id='O-ANM3', orders=[parent_order, sl_order, tp_order])

    # Move context to CLOSING sequester with orders still active in carnet
    group.notify_order_change(create_order_receipt_factory(
        group_id='O-ANM3', client_order_id='O-ANM3', state=OrderState.FILLED
    ))
    group.notify_order_change(create_order_receipt_factory(
        group_id='O-ANM3', client_order_id='O-ANM3-SL', state=OrderState.FILLED
    ))
    assert group._state == OrderGroupState.CLOSING

    # First flat clearing payload updates witness metrics cleanly
    group.notify_trade_change(create_trade_receipt_factory(group_id='O-ANM3', is_open=False))
    assert group._clearing_closed is True
    assert group._state == OrderGroupState.CLOSING  # Living because TP is still PENDING

    # Duplicate flat clearing payload hits the living entity aggregate
    group.notify_trade_change(create_trade_receipt_factory(group_id='O-ANM3', is_open=False))

    # Invariant: Must remain structural, stable, and untainted by the network noise
    assert group._clearing_closed is True
    assert group._state == OrderGroupState.CLOSING

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

# ---[ EXTREME/GHOST EXECUTION

# -----------------------------------------------------------------------------

def test_order_group_late_child_protective_ghost_fill() -> None:
    """Ensures an unhandled child protective fill during rejection locks into corruption."""
    parent_order = create_order_factory(client_order_id='O-EXT1')
    sl_order = create_order_factory(client_order_id='O-EXT1-SL')
    group = OrderGroup(parent_id='O-EXT1', orders=[parent_order, sl_order])

    # 1. Move to REJECTING sequester block after parent entry failure
    group.notify_order_change(create_order_receipt_factory(
        group_id='O-EXT1', client_order_id='O-EXT1', state=OrderState.CANCELED
    ))
    assert group._state == OrderGroupState.REJECTING

    # 2. Anomaly: Child protective order executes filled while group is clearing out
    with pytest.raises(CorruptedOrderGroupError):
        group.notify_order_change(create_order_receipt_factory(
            group_id='O-EXT1', client_order_id='O-EXT1-SL', state=OrderState.FILLED
        ))

# -----------------------------------------------------------------------------

def test_order_group_premature_child_ghost_fill_before_parent() -> None:
    """Ensures premature child execution prior to parent entry triggers corruption."""
    parent_order = create_order_factory(client_order_id='O-EXT2')
    sl_order = create_order_factory(client_order_id='O-EXT2-SL')
    group = OrderGroup(parent_id='O-EXT2', orders=[parent_order, sl_order])

    # Invariant Birth Check
    assert group._state == OrderGroupState.PENDING

    # Anomaly: Venue ledger reports a protective child execution while parent is PENDING
    with pytest.raises(CorruptedOrderGroupError):
        group.notify_order_change(create_order_receipt_factory(
            group_id='O-EXT2', client_order_id='O-EXT2-SL', state=OrderState.FILLED
        ))

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

def test_order_group_is_cancelable_in_initial_pending_state() -> None:
    """Verify that a fresh pending group with untouched clearing allows cancellation."""
    parent_order = create_order_factory(client_order_id='ORDER_123')
    order_group = OrderGroup(parent_id='ORDER_123', orders=[parent_order])

    order_group._state = OrderGroupState.PENDING
    order_group._clearing_closed = None

    assert order_group.is_cancelable()
    assert not order_group.is_closable()

# -----------------------------------------------------------------------------

def test_order_group_denies_cancellation_on_open_clearing_race_condition() -> None:
    """Verify that cancellation is barred if clearing opens before book updates state."""
    parent_order = create_order_factory(client_order_id='ORDER_123')
    order_group = OrderGroup(parent_id='ORDER_123', orders=[parent_order])

    order_group._state = OrderGroupState.PENDING
    order_group._clearing_closed = False

    assert not order_group.is_cancelable()

# -----------------------------------------------------------------------------

def test_order_group_allows_liquidation_in_nominal_active_state() -> None:
    """Verify that a nominal active group with open exposure permits market liquidation."""
    parent_order = create_order_factory(client_order_id='ORDER_123')
    order_group = OrderGroup(parent_id='ORDER_123', orders=[parent_order])

    order_group._state = OrderGroupState.ACTIVE
    order_group._clearing_closed = False

    assert order_group.is_closable()
    assert not order_group.is_cancelable()

# -----------------------------------------------------------------------------

def test_order_group_allows_liquidation_on_open_clearing_race_condition() -> None:
    """Verify that liquidation is allowed if clearing opens before book updates state."""
    parent_order = create_order_factory(client_order_id='ORDER_123')
    order_group = OrderGroup(parent_id='ORDER_123', orders=[parent_order])

    order_group._state = OrderGroupState.PENDING
    order_group._clearing_closed = False

    assert order_group.is_closable()

# -----------------------------------------------------------------------------

def test_order_group_denies_liquidation_on_closed_clearing_race_condition() -> None:
    """Verify that liquidation is barred if clearing closes before book updates state."""
    parent_order = create_order_factory(client_order_id='ORDER_123')
    order_group = OrderGroup(parent_id='ORDER_123', orders=[parent_order])

    order_group._state = OrderGroupState.ACTIVE
    order_group._clearing_closed = True

    assert not order_group.is_closable()

# -----------------------------------------------------------------------------

def test_order_group_denies_liquidation_while_already_closing() -> None:
    """Verify that liquidation is barred if the group is already in CLOSING state."""
    parent_order = create_order_factory(client_order_id='ORDER_123')
    order_group = OrderGroup(parent_id='ORDER_123', orders=[parent_order])

    order_group._state = OrderGroupState.CLOSING
    order_group._clearing_closed = False

    assert not order_group.is_closable()

# -----------------------------------------------------------------------------

def test_order_group_denies_liquidation_while_rejecting() -> None:
    """Verify that liquidation is barred if the group is in REJECTING state."""
    parent_order = create_order_factory(client_order_id='ORDER_123')
    order_group = OrderGroup(parent_id='ORDER_123', orders=[parent_order])

    order_group._state = OrderGroupState.REJECTING
    order_group._clearing_closed = None

    assert not order_group.is_closable()

# -----------------------------------------------------------------------------

def test_order_group_denies_liquidation_in_terminal_completed_state() -> None:
    """Verify that liquidation is barred if the group is in COMPLETED state."""
    parent_order = create_order_factory(client_order_id='ORDER_123')
    order_group = OrderGroup(parent_id='ORDER_123', orders=[parent_order])

    order_group._state = OrderGroupState.COMPLETED
    order_group._clearing_closed = True

    assert not order_group.is_closable()

# -----------------------------------------------------------------------------

def test_order_group_denies_nominal_liquidation_while_corrupted() -> None:
    """Verify that automated nominal liquidation is barred if the group is corrupted."""
    parent_order = create_order_factory(client_order_id='ORDER_123')
    order_group = OrderGroup(parent_id='ORDER_123', orders=[parent_order])

    order_group._state = OrderGroupState.CORRUPTED
    order_group._clearing_closed = False

    assert not order_group.is_closable()

# -----------------------------------------------------------------------------

def test_order_group_denies_cancellation_in_active_state() -> None:
    """Verify that a classical cancellation request is barred once the group is active."""
    parent_order = create_order_factory(client_order_id='ORDER_123')
    order_group = OrderGroup(parent_id='ORDER_123', orders=[parent_order])

    order_group._state = OrderGroupState.ACTIVE
    order_group._clearing_closed = False

    assert not order_group.is_cancelable()

# -----------------------------------------------------------------------------

def test_order_group_allows_liquidation_on_book_priority_asynchronism() -> None:
    """Verify that liquidation is permitted if book reaches active state before clearing."""
    parent_order = create_order_factory(client_order_id='ORDER_123')
    order_group = OrderGroup(parent_id='ORDER_123', orders=[parent_order])

    order_group._state = OrderGroupState.ACTIVE
    order_group._clearing_closed = None

    assert order_group.is_closable()

# -----------------------------------------------------------------------------

def test_order_group_denies_cancellation_if_clearing_is_already_closed() -> None:
    """Verify that cancellation is barred if clearing signals closure while state is pending."""
    parent_order = create_order_factory(client_order_id='ORDER_123')
    order_group = OrderGroup(parent_id='ORDER_123', orders=[parent_order])

    order_group._state = OrderGroupState.PENDING
    order_group._clearing_closed = True

    assert not order_group.is_cancelable()

# -----------------------------------------------------------------------------

def test_order_group_denies_cancellation_while_already_closing() -> None:
    """Verify that cancellation is barred if the group has transitioned to CLOSING."""
    parent_order = create_order_factory(client_order_id='ORDER_123')
    order_group = OrderGroup(parent_id='ORDER_123', orders=[parent_order])

    order_group._state = OrderGroupState.CLOSING
    order_group._clearing_closed = None

    assert not order_group.is_cancelable()

# -----------------------------------------------------------------------------

def test_order_group_denies_liquidation_in_terminal_rejected_state() -> None:
    """Verify that market liquidation is barred if the group is dead-on-arrival."""
    parent_order = create_order_factory(client_order_id='ORDER_123')
    order_group = OrderGroup(parent_id='ORDER_123', orders=[parent_order])

    order_group._state = OrderGroupState.REJECTED
    order_group._clearing_closed = None

    assert not order_group.is_closable()

# -----------------------------------------------------------------------------

def test_order_group_denies_cancellation_in_terminal_rejected_state() -> None:
    """Verify that a cancellation command is barred if the group is already rejected."""
    parent_order = create_order_factory(client_order_id='ORDER_123')
    order_group = OrderGroup(parent_id='ORDER_123', orders=[parent_order])

    order_group._state = OrderGroupState.REJECTED
    order_group._clearing_closed = None

    assert not order_group.is_cancelable()

# -----------------------------------------------------------------------------

def test_order_group_denies_cancellation_on_book_active_priority() -> None:
    """Verify that cancellation is barred once book reaches active state regardless of clearing."""
    parent_order = create_order_factory(client_order_id='ORDER_123')
    order_group = OrderGroup(parent_id='ORDER_123', orders=[parent_order])

    order_group._state = OrderGroupState.ACTIVE
    order_group._clearing_closed = None

    assert not order_group.is_cancelable()

# -----------------------------------------------------------------------------

def test_order_group_denies_cancellation_while_rejecting_with_clearing_latency() -> None:
    """Verify that cancellation is barred if the group is in REJECTING state with late clearing."""
    parent_order = create_order_factory(client_order_id='ORDER_123')
    order_group = OrderGroup(parent_id='ORDER_123', orders=[parent_order])

    order_group._state = OrderGroupState.REJECTING
    order_group._clearing_closed = None

    assert not order_group.is_cancelable()

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_attach_exit_order_nominal():
    """Verify clean attachment under nominal conditions."""
    parent_order = create_order_factory(client_order_id='ORD_123')
    group = OrderGroup(parent_id='ORD_123', orders=[parent_order])

    exit_order = create_order_factory(client_order_id='ORD_123-XT')

    assert group._exit_order is None

    group.attach_exit_order(exit_order)
    assert group._exit_order is exit_order

# -----------------------------------------------------------------------------

def test_attach_exit_order_duplicate_raises():
    """Verify subsequent attachments trigger a netting error."""
    parent_order = create_order_factory(client_order_id='ORD_123')
    group = OrderGroup(parent_id='ORD_123', orders=[parent_order])

    exit_1 = create_order_factory(client_order_id='ORD_123-XT')
    exit_2 = create_order_factory(client_order_id='ORD_123-XT2')

    group.attach_exit_order(exit_1)

    assert group._exit_order is exit_1

    expected_msg = 'An exit order is already registered for group "ORD_123".'
    with pytest.raises(NettingRestrictionError, match=expected_msg):
        group.attach_exit_order(exit_2)

# -----------------------------------------------------------------------------

def test_attach_exit_order_identity_conflict_raises():
    """Verify identity collisions trigger a value error."""
    parent_order = create_order_factory(client_order_id='ORD_123')
    group = OrderGroup(parent_id='ORD_123', orders=[parent_order])

    conflicting_exit = create_order_factory(client_order_id='ORD_123')

    assert group._exit_order is None

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
