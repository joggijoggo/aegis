"""Aegis Framework - Backtrader Broker Adapter Component Tests.

Validates accounting parsing, asynchronous queue polling, and notification mapping.
"""

from decimal import Decimal
from queue import Queue
from unittest.mock import MagicMock

from broker_adapters.backtrader_bridge import BacktraderBridge
from broker_adapters.backtrader_broker_adapter import BacktraderBrokerAdapter
from core.models import (
    AccountSnapshot,
    BrokerEvent,
    EventType,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_backtrader_broker_adapter_account_snapshot() -> None:
    """Verifies precision parsing of float portfolio balances into decimals."""
    mock_bridge = MagicMock(spec=BacktraderBridge)

    # Remove spec on strategy to allow dynamic mocking of the broker attribute hierarchy
    mock_strategy = MagicMock()
    mock_strategy.broker.get_cash.return_value = 10000.50
    mock_strategy.broker.get_value.return_value = 10500.75
    mock_bridge.strategy = mock_strategy

    adapter = BacktraderBrokerAdapter(bridge=mock_bridge)
    snapshot = adapter.get_account_snapshot()

    assert isinstance(snapshot, AccountSnapshot)
    assert snapshot.currency == 'USD'
    assert snapshot.balance == Decimal('10000.50')
    assert snapshot.equity == Decimal('10500.75')
    assert snapshot.available_margin == Decimal('10500.75')

# -----------------------------------------------------------------------------

def test_backtrader_broker_adapter_polling_mechanics() -> None:
    """Verifies that non-blocking polling retrieves and translates buffered events."""
    mock_bridge = MagicMock(spec=BacktraderBridge)
    fake_queue: Queue = Queue()
    mock_bridge.get_broker_queue.return_value = fake_queue

    adapter = BacktraderBrokerAdapter(bridge=mock_bridge)
    assert adapter.has_pending_events() is False

    fake_queue.put((EventType.ORDER_NOTIFICATION, 'raw_order_payload'))
    assert adapter.has_pending_events() is True

    event = adapter.poll_event()
    assert isinstance(event, BrokerEvent)
    assert event.event_type == EventType.ORDER_NOTIFICATION
    assert event.payload == 'raw_order_payload'
    assert adapter.has_pending_events() is False

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
