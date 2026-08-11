"""Aegis Framework - Unit tests for the core execution tracking ledger.

Validates execution lifecycles, tracking group updates, and bot isolation bounds.
"""

from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

from aegis.core.exception import (
    DanglingExecutionError,
    NettingRestrictionError,
    UnsupportedBrokerEventError,
    UntrackedOrderException,
)
from aegis.core.execution_tracker import ExecutionTracker
from aegis.core.model import (
    BrokerEvent,
    EventType,
    OrderSide,
    OrderState,
)
from aegis.core.order_group import OrderGroup
from tests.testutil import (
    FakeBrokerAdapter,
    create_order_factory,
    create_order_receipt_factory,
    create_trade_receipt_factory,
)

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

# -----------------------------------------------------------------------------

def test_execution_tracker_routes_order_notification_nominally() -> None:
    """Verify that an order notification event is correctly routed to the targeted order group."""
    tracker = ExecutionTracker()
    domain_order = create_order_factory(client_order_id='ORDER_123')
    tracker.register_order('BOT_TEST_A', domain_order)
    assert tracker.has_active_execution('BOT_TEST_A')

    receipt = create_order_receipt_factory(group_id='ORDER_123')
    broker_event = BrokerEvent(event_type=EventType.ORDER_NOTIFICATION, payload=receipt)

    with (
        patch.object(
            tracker._executions['BOT_TEST_A'], 'notify_order_change') as mock_notify,
        patch.object(
            OrderGroup, 'is_terminal', return_value=False),
    ):
        tracker.process_broker_event(broker_event)

        mock_notify.assert_called_once_with(receipt)
        # Checks that it is still alive.
        assert tracker.has_active_execution('BOT_TEST_A')

# -----------------------------------------------------------------------------

def test_execution_tracker_routes_trade_notification_nominally() -> None:
    """Verify that a trade notification event is correctly routed to the targeted order group."""
    tracker = ExecutionTracker()
    domain_order = create_order_factory(client_order_id='ORDER_123')
    tracker.register_order('BOT_TEST_A', domain_order)
    assert tracker.has_active_execution('BOT_TEST_A')

    receipt = create_trade_receipt_factory(group_id='ORDER_123')
    broker_event = BrokerEvent(event_type=EventType.TRADE_NOTIFICATION, payload=receipt)

    with (
        patch.object(
            tracker._executions['BOT_TEST_A'], 'notify_trade_change') as mock_notify,
        patch.object(
            OrderGroup, 'is_terminal', return_value=False),
    ):
        tracker.process_broker_event(broker_event)

        mock_notify.assert_called_once_with(receipt)
        assert tracker.has_active_execution('BOT_TEST_A')

# -----------------------------------------------------------------------------

def test_execution_tracker_clears_memory_on_terminal_state() -> None:
    """Verify that the tracker purges all internal RAM references when group is terminal."""
    tracker = ExecutionTracker()
    domain_order = create_order_factory(client_order_id='ORDER_123')
    tracker.register_order('BOT_TEST_A', domain_order)
    assert tracker.has_active_execution('BOT_TEST_A')

    receipt = create_order_receipt_factory(group_id='ORDER_123')
    broker_event = BrokerEvent(event_type=EventType.ORDER_NOTIFICATION, payload=receipt)

    with (
        patch.object(
            tracker._executions['BOT_TEST_A'], 'notify_order_change'),
        patch.object(
            OrderGroup, 'is_terminal', return_value=True),
    ):
        tracker.process_broker_event(broker_event)

        assert not tracker.has_active_execution('BOT_TEST_A')

# -----------------------------------------------------------------------------

def test_execution_tracker_process_broker_event_raises_untracked_order() -> None:
    """Verify that processing an event for an unrecognized order ID raises an error."""
    tracker = ExecutionTracker()
    receipt = create_order_receipt_factory(group_id='UNKNOWN_ID')
    broker_event = BrokerEvent(event_type=EventType.ORDER_NOTIFICATION, payload=receipt)

    with pytest.raises(UntrackedOrderException) as exc_info:
        tracker.process_broker_event(broker_event)

    assert "order identity 'UNKNOWN_ID' is untracked" in str(exc_info.value)

# -----------------------------------------------------------------------------

def test_execution_tracker_process_broker_event_raises_unsupported_event() -> None:
    """Verify that processing an event with an unhandled event type raises an error."""
    tracker = ExecutionTracker()
    domain_order = create_order_factory(client_order_id='ORDER_123')
    tracker.register_order('BOT_TEST_A', domain_order)

    receipt = create_order_receipt_factory(client_order_id='ORDER_123')
    corrupted_event = BrokerEvent(event_type='UNKNOWN_EVENT_TAXONOMY', payload=receipt)

    with pytest.raises(UnsupportedBrokerEventError) as exc_info:
        tracker.process_broker_event(corrupted_event)

    assert 'Received unhandled or corrupted event type' in str(exc_info.value)

# -----------------------------------------------------------------------------

def test_execution_tracker_terminate_execution_cancels_when_cancelable() -> None:
    """Verify that terminate_execution calls cancel_order if the group is cancelable."""
    tracker = ExecutionTracker()
    domain_order = create_order_factory(client_order_id='ORDER_123')
    tracker.register_order('BOT_TEST_A', domain_order)
    mock_adapter = MagicMock()

    with (
        patch.object(OrderGroup, 'get_parent_order', return_value=domain_order),
        patch.object(OrderGroup, 'is_cancelable', return_value=True),
        patch.object(OrderGroup, 'is_closable', return_value=False),
        patch.object(OrderGroup, 'is_terminal', return_value=False),
    ):
        tracker.terminate_execution('BOT_TEST_A', mock_adapter)

        mock_adapter.cancel_order.assert_called_once_with(domain_order)
        assert tracker.has_active_execution('BOT_TEST_A')

# -----------------------------------------------------------------------------

def test_execution_tracker_terminate_execution_closes_when_closable() -> None:
    """Verify that terminate_execution calls close_position if the group is closable."""
    tracker = ExecutionTracker()
    domain_order = create_order_factory(
        client_order_id='ORDER_123',
        side=OrderSide.BUY
    )
    tracker.register_order('BOT_TEST_A', domain_order)
    mock_adapter = MagicMock()

    with (
        patch.object(OrderGroup, 'is_cancelable', return_value=False),
        patch.object(OrderGroup, 'is_closable', return_value=True),
        patch.object(OrderGroup, 'is_terminal', return_value=False),
    ):
        tracker.terminate_execution('BOT_TEST_A', mock_adapter)

    assert 'ORDER_123-XT' in tracker._order_id_to_bot_id

    called_order = mock_adapter.close_position.call_args[0][0]
    assert called_order.client_order_id == 'ORDER_123-XT'
    assert called_order.side == OrderSide.SELL
    assert called_order.stop_loss_price is None
    assert called_order.take_profit_price is None
    assert tracker.has_active_execution('BOT_TEST_A')

# -----------------------------------------------------------------------------

def test_execution_tracker_terminate_execution_raises_dangling_execution() -> None:
    """Verify that terminate_execution raises an error if a terminal group persists in RAM."""
    tracker = ExecutionTracker()
    domain_order = create_order_factory(client_order_id='ORDER_123')
    tracker.register_order('BOT_TEST_A', domain_order)
    mock_adapter = MagicMock()

    with (
        patch.object(OrderGroup, 'get_parent_order', return_value=domain_order),
        patch.object(OrderGroup, 'is_cancelable', return_value=False),
        patch.object(OrderGroup, 'is_closable', return_value=False),
        patch.object(OrderGroup, 'is_terminal', return_value=True),
    ):
        with pytest.raises(DanglingExecutionError) as exc_info:
            tracker.terminate_execution('BOT_TEST_A', mock_adapter)

        assert 'is already terminal but was not evicted from memory' in str(exc_info.value)

# -----------------------------------------------------------------------------

def test_execution_tracker_terminate_execution_raises_untracked_order() -> None:
    """Verify that forcing termination on an inactive bot raises an error."""
    tracker = ExecutionTracker()
    mock_adapter = MagicMock()

    with pytest.raises(UntrackedOrderException) as exc_info:
        tracker.terminate_execution('BOT_UNKNOWN', mock_adapter)

    assert "Termination failure: bot 'BOT_UNKNOWN' has no active" in str(exc_info.value)

# -----------------------------------------------------------------------------

def test_execution_tracker_terminate_execution_ignores_transitional_phases() -> None:
    """Verify that terminate_execution does nothing if the group is in a transitional phase."""
    tracker = ExecutionTracker()
    domain_order = create_order_factory(client_order_id='ORDER_123')
    tracker.register_order('BOT_TEST_A', domain_order)
    mock_adapter = MagicMock()

    with (
        patch.object(OrderGroup, 'get_parent_order', return_value=domain_order),
        patch.object(OrderGroup, 'is_cancelable', return_value=False),
        patch.object(OrderGroup, 'is_closable', return_value=False),
        patch.object(OrderGroup, 'is_terminal', return_value=False),
    ):
        tracker.terminate_execution('BOT_TEST_A', mock_adapter)

        mock_adapter.cancel_order.assert_not_called()
        mock_adapter.close_position.assert_not_called()
        assert tracker.has_active_execution('BOT_TEST_A')

# -----------------------------------------------------------------------------

def test_terminate_execution_forges_and_tracks_xt_order():
    """Verify closure forges, indexes and routes the exit XT ticket."""
    tracker = ExecutionTracker()
    broker_adapter = FakeBrokerAdapter()

    parent_order = create_order_factory(
        client_order_id='ORD_123',
        side=OrderSide.BUY,
        stop_loss_price=1.0800,
        take_profit_price=1.0900
    )

    tracker.register_order(bot_id='BOT_ID', order=parent_order)
    group = tracker._executions['BOT_ID']

    receipt = create_order_receipt_factory(
        client_order_id='ORD_123',
        group_id='ORD_123',
        state=OrderState.FILLED
    )
    group.notify_order_change(receipt)

    assert 'ORD_123-XT' not in tracker._order_id_to_bot_id
    assert group._exit_order_id is None

    tracker.terminate_execution(
        bot_id='BOT_ID',
        broker_adapter=broker_adapter
    )

    assert tracker._order_id_to_bot_id['ORD_123-XT'] == 'BOT_ID'

    exit_order = group._orders[group._exit_order_id]
    assert exit_order is not None
    assert exit_order.client_order_id == 'ORD_123-XT'
    assert exit_order.side == OrderSide.SELL
    assert exit_order.stop_loss_price is None
    assert exit_order.take_profit_price is None

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
