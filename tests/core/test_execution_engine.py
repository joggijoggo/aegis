"""Aegis Framework - Execution Engine Unit Tests.

Validates core engine orchestration mechanics, transaction lifecycle dispatching,
and contextual order generation workflows.
"""

from decimal import Decimal
from unittest.mock import MagicMock, Mock, call

from core.execution_engine import AegisExecutionEngine
from core.models import (
    BrokerEvent,
    EventType,
    ExposureIntent,
    MarketContext,
    MarketPricePoint,
)
from tests.testutils import (
    BASE_TIMESTAMP,
    DEFAULT_SYMBOL,
    FakeBot,
    FakeBrokerAdapter,
    FakeMarketFeed,
    create_contract_registry_factory,
    create_contract_specification_factory,
    create_market_context_factory,
    create_order_receipt_factory,
    create_position_sizer_factory,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_execution_engine_broker_event_flushing() -> None:
    """Verify that all pending broker events are fully routed after fetching market data."""
    fake_bot = FakeBot(warm_up=10)
    fake_adapter = FakeBrokerAdapter()
    engine = AegisExecutionEngine(
        fake_bot,
        fake_adapter,
        create_contract_registry_factory(
            specifications={
                'EURUSD': create_contract_specification_factory(
                    symbol='EURUSD'
                )
            }
        ),
        create_position_sizer_factory(),
    )
    engine._tracker = MagicMock()

    event_1 = BrokerEvent(
        event_type=EventType.ORDER_NOTIFICATION,
        payload=create_order_receipt_factory(client_order_id='ORDER_1'),
    )
    event_2 = BrokerEvent(
        event_type=EventType.ORDER_NOTIFICATION,
        payload=create_order_receipt_factory(client_order_id='ORDER_2'),
    )
    fake_adapter._pending_events.put(event_1)
    fake_adapter._pending_events.put(event_2)

    mock_manager = Mock()
    mock_manager.attach_mock(
        engine._tracker.process_broker_event, 'process_event'
    )

    class MonitoredFeed:

        def __init__(self, items: list) -> None:
            self._iterator = iter(items)

        def __next__(self) -> MarketContext:
            mock_manager.next_tick()
            return next(self._iterator)

    clean_feed = MonitoredFeed([create_market_context_factory()])

    assert fake_adapter.has_pending_events()
    engine.run_execution_cycle('EURUSD', clean_feed)
    assert not fake_adapter.has_pending_events()

    expected_calls = [
        call.next_tick(),
        call.process_event(event_1),
        call.process_event(event_2),
    ]
    assert mock_manager.method_calls[:3] == expected_calls

# -----------------------------------------------------------------------------

def test_engine_cycle_executes_order_on_valid_intent(
    contract_registry,
    position_sizer,
) -> None:
    """Ensures a valid bot alpha direction triggers full sizer routing."""
    intent = ExposureIntent(
        alpha_direction=1.0,
        stop_loss_ticks=500.0,
        take_profit_ticks=1000.0,
    )
    bot = FakeBot(exposure_intent=intent, warm_up=10)
    broker = FakeBrokerAdapter()

    engine = AegisExecutionEngine(
        bot=bot,
        broker_adapter=broker,
        contract_registry=contract_registry,
        position_sizer=position_sizer,
    )

    prices = MarketPricePoint(
        timestamp=BASE_TIMESTAMP,
        mid_price=1.08500,
        bid=1.08490,
        ask=1.08510,
        current_atr=0.0020,
    )
    context = MarketContext(prices=prices)
    feed = FakeMarketFeed(market_contexts=[context])

    engine.run_execution_cycle(symbol=DEFAULT_SYMBOL, market_feed=feed)

    assert len(broker.submitted_orders) == 1
    assert broker.submitted_orders[0].symbol == DEFAULT_SYMBOL
    assert broker.submitted_orders[0].quantity == Decimal('0.20')
    # Assert that the atomic temporal snapshot was pulled exactly once during the cycle
    assert broker.snapshot_call_count == 1

# -----------------------------------------------------------------------------

def test_engine_cycle_handles_exit_with_active_execution(
    contract_registry,
    position_sizer,
) -> None:
    """Verify that an exit intent triggers termination when execution is active."""
    intent = ExposureIntent(alpha_direction=0.0)
    bot = FakeBot(exposure_intent=intent, warm_up=10)
    broker = FakeBrokerAdapter()
    engine = AegisExecutionEngine(
        bot=bot,
        broker_adapter=broker,
        contract_registry=contract_registry,
        position_sizer=position_sizer,
    )
    engine._tracker = MagicMock()
    engine._tracker.has_active_execution.return_value = True

    market_context = create_market_context_factory()
    feed = FakeMarketFeed(market_contexts=[market_context])

    engine.run_execution_cycle(symbol=DEFAULT_SYMBOL, market_feed=feed)
    engine._tracker.terminate_execution.assert_called_once_with(
        bot_id='BOT_ID',
        broker_adapter=broker,
    )

# -----------------------------------------------------------------------------

def test_engine_cycle_skips_processing_on_none_intent(
    contract_registry,
    position_sizer,
) -> None:
    """Ensures an absent alpha signal skips downstream infrastructure routing."""
    intent = ExposureIntent(alpha_direction=None)
    bot = FakeBot(exposure_intent=intent)
    broker = FakeBrokerAdapter()

    engine = AegisExecutionEngine(
        bot=bot,
        broker_adapter=broker,
        contract_registry=contract_registry,
        position_sizer=position_sizer,
    )

    prices = MarketPricePoint(
        timestamp=BASE_TIMESTAMP,
        mid_price=1.08500,
        bid=1.08490,
        ask=1.08510,
        current_atr=0.0020,
    )
    context = MarketContext(prices=prices)
    feed = FakeMarketFeed(market_contexts=[context])

    engine.run_execution_cycle(symbol=DEFAULT_SYMBOL, market_feed=feed)

    assert len(broker.submitted_orders) == 0
    assert broker.snapshot_call_count == 1

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
