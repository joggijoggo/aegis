"""Aegis Framework - Backtrader Bridge Component Tests.

Validates thread-safe synchronization mechanics, event routing, and binding lifecycles.
"""

from queue import Queue
import threading
from unittest.mock import MagicMock

import backtrader as bt
import pytest

from broker_adapters.backtrader_bridge import (
    BacktraderBridge,
    BridgeAlreadyBoundError,
    BridgeUnboundError,
)
from core.models.enums import EventType

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_backtrader_bridge_allocation_lifecycle() -> None:
    """Verifies default initialization states and queue properties."""
    bridge = BacktraderBridge()

    assert isinstance(bridge.get_broker_queue(), Queue)
    assert isinstance(bridge.get_market_queue(), Queue)
    assert bridge.is_simulation_completed() is False

# -----------------------------------------------------------------------------

def test_backtrader_bridge_binding_constraints() -> None:
    """Verifies strategy single-assignment enforcement and access guards."""
    bridge = BacktraderBridge()

    mock_strategy_1 = MagicMock(spec=bt.Strategy)
    mock_strategy_2 = MagicMock(spec=bt.Strategy)

    with pytest.raises(BridgeUnboundError):
        _ = bridge.strategy

    bridge.bind_strategy(mock_strategy_1)
    assert bridge.strategy is mock_strategy_1

    with pytest.raises(BridgeAlreadyBoundError):
        bridge.bind_strategy(mock_strategy_2)

# -----------------------------------------------------------------------------

def test_backtrader_bridge_broker_event_routing() -> None:
    """Verifies that non-market events route directly without blocking threads."""
    bridge = BacktraderBridge()
    fake_data = {'order_id': 'ORD-123', 'status': 'FILLED'}

    bridge.submit_event(EventType.ORDER_NOTIFICATION, fake_data)
    broker_queue = bridge.get_broker_queue()

    assert broker_queue.empty() is False
    event_type, routed_data = broker_queue.get()
    assert event_type == EventType.ORDER_NOTIFICATION
    assert routed_data == fake_data

# -----------------------------------------------------------------------------

def test_backtrader_bridge_simulation_termination() -> None:
    """Verifies completion state flags switch successfully."""
    bridge = BacktraderBridge()
    assert bridge.is_simulation_completed() is False

    bridge.stop_simulation()
    assert bridge.is_simulation_completed() is True

# -----------------------------------------------------------------------------

def test_backtrader_bridge_thread_synchronization() -> None:
    """Verifies thread-safe ping-pong blocking on market context boundaries."""
    bridge = BacktraderBridge()
    execution_trace: list[str] = []

    def simulate_backtrader_thread() -> None:
        execution_trace.append('bt_start')
        bridge.submit_event(EventType.MARKET_TICK, 'tick_data_1')
        execution_trace.append('bt_released')

    bt_thread = threading.Thread(target=simulate_backtrader_thread)
    bt_thread.start()

    bt_thread.join(timeout=0.05)

    market_queue = bridge.get_market_queue()
    assert market_queue.empty() is False
    assert market_queue.get() == 'tick_data_1'

    execution_trace.append('engine_processed')

    bridge.advance_time()
    bt_thread.join(timeout=0.1)

    assert execution_trace == ['bt_start', 'engine_processed', 'bt_released']

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
