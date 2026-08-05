"""Aegis Framework - Execution Engine Unit Tests.

Validates core engine orchestration mechanics, transaction lifecycle dispatching,
and contextual order generation workflows.
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from core.contract_registry import ContractRegistry
from core.exceptions import (
    DuplicateOrderGroupError,
    UnsupportedBrokerEventError,
)
from core.execution_engine import AegisExecutionEngine
from core.models import (
    BrokerEvent,
    EventType,
    ExposureIntent,
    MarketContext,
    MarketPricePoint,
    OrderState,
)
from core.position_sizer import PositionSizer
from tests.testutils import (
    BASE_TIMESTAMP,
    DEFAULT_SYMBOL,
    FakeBot,
    FakeBrokerAdapter,
    FakeMarketFeed,
    create_contract_registry_factory,
    create_contract_specification_factory,
    create_market_context_factory,
    create_order_factory,
    create_order_receipt_factory,
    create_position_sizer_factory,
    create_trade_receipt_factory,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_execution_engine_broker_event_flushing() -> None:
    """Verifies that unread broker events are fully flushed before evaluating market feeds."""
    mock_bot = MagicMock(spec=FakeBot)
    mock_bot.warm_up_period = 10
    mock_bot.evaluate.side_effect = StopIteration  # Force loop termination after first step

    adapter = FakeBrokerAdapter()
    # Inject a fake unread broker event notification into the queue
    fake_event = BrokerEvent(event_type=EventType.ORDER_NOTIFICATION, payload={})
    adapter._pending_events.put(fake_event)

    mock_registry = MagicMock(spec=ContractRegistry)
    mock_sizer = MagicMock(spec=PositionSizer)

    engine = AegisExecutionEngine(
        bot=mock_bot,
        broker_adapter=adapter,
        contract_registry=mock_registry,
        position_sizer=mock_sizer,
    )

    engine._process_broker_event = MagicMock()
    mock_feed = MagicMock(spec=FakeMarketFeed)

    engine.run_execution_cycle(symbol='EURUSD', market_feed=mock_feed)

    # Assert the async event flushing loop was triggered and emptied the queue
    engine._process_broker_event.assert_called_once_with(fake_event)
    assert adapter.has_pending_events() is False

    # Assert that the atomic temporal snapshot was pulled exactly once during the cycle
    assert adapter.snapshot_call_count == 1

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

def test_engine_cycle_registers_volatile_order_group() -> None:
    """Ensures that a submitted order creates an isolated internal tracking group record."""
    intent = ExposureIntent(
        alpha_direction=1.0,
        stop_loss_ticks=500.0,
        take_profit_ticks=1000.0,
    )
    bot = FakeBot(exposure_intent=intent, warm_up=10)
    broker = FakeBrokerAdapter()

    spec = create_contract_specification_factory()
    registry = ContractRegistry(specifications={DEFAULT_SYMBOL: spec})
    sizer = create_position_sizer_factory()

    context = create_market_context_factory()
    feed = FakeMarketFeed(market_contexts=[context])

    engine = AegisExecutionEngine(
        bot=bot,
        broker_adapter=broker,
        contract_registry=registry,
        position_sizer=sizer,
    )

    assert len(engine._order_groups) == 0

    engine.run_execution_cycle(symbol=DEFAULT_SYMBOL, market_feed=feed)

    # Assert that the engine successfully populated its volatile memory ledger
    assert len(engine._order_groups) == 1

    # Retrieve the tracking record using the submitted order id to check fields mapping
    order_id = broker.submitted_orders[0].client_order_id
    assert order_id in engine._order_groups

    recorded_group = engine._order_groups[order_id]
    assert not recorded_group.is_terminal

# -----------------------------------------------------------------------------

def test_engine_cycle_raises_not_implemented_error_for_neutral_alpha(
    contract_registry,
    position_sizer,
) -> None:
    """Ensures a 0.0 alpha direction triggers an early closure exception."""
    intent = ExposureIntent(alpha_direction=0.0)
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

    with pytest.raises(NotImplementedError):
        engine.run_execution_cycle(symbol=DEFAULT_SYMBOL, market_feed=feed)

    assert len(broker.submitted_orders) == 0
    assert broker.snapshot_call_count == 1

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

# -----------------------------------------------------------------------------

def test_engine_handles_unsupported_broker_event_error() -> None:
    """Ensures that an unknown event category triggers an immediate execution halt."""
    bot = FakeBot()
    broker = FakeBrokerAdapter()
    registry = ContractRegistry(specifications={})
    sizer = create_position_sizer_factory()

    engine = AegisExecutionEngine(
        bot=bot,
        broker_adapter=broker,
        contract_registry=registry,
        position_sizer=sizer,
    )

    # Inject a corrupted or unhandled infrastructure event type wrapper
    corrupted_event = BrokerEvent(event_type="INVALID_TYPE", payload={})

    with pytest.raises(UnsupportedBrokerEventError):
        engine._process_broker_event(corrupted_event)

# -----------------------------------------------------------------------------

def test_engine_raises_duplicate_order_group_error_on_collision() -> None:
    """Ensures that registering an existing group ID triggers an immediate halt."""
    bot = FakeBot()
    broker = FakeBrokerAdapter()
    registry = ContractRegistry(specifications={})
    sizer = create_position_sizer_factory()

    engine = AegisExecutionEngine(
        bot=bot,
        broker_adapter=broker,
        contract_registry=registry,
        position_sizer=sizer,
    )

    # Pre-populate the volatile memory with a pre-existing group entry
    existing_order = create_order_factory()
    engine._register_order_group(existing_order)

    # Attempt to register the exact same order structure again to trigger collision
    with pytest.raises(DuplicateOrderGroupError):
        engine._register_order_group(existing_order)

# -----------------------------------------------------------------------------

def test_engine_reconciles_order_lifecycle_and_maintains_active_group() -> None:
    """Ensures parent order fulfillment transitions group to active state in RAM."""
    bot = FakeBot()
    broker = FakeBrokerAdapter()
    registry = create_contract_registry_factory()
    sizer = create_position_sizer_factory()

    engine = AegisExecutionEngine(
        bot=bot,
        broker_adapter=broker,
        contract_registry=registry,
        position_sizer=sizer,
    )

    # Seed the volatile execution registry with an active pending trade intent
    parent_order = create_order_factory()
    engine._register_order_group(parent_order)
    order_id = parent_order.client_order_id

    assert len(engine._order_groups) == 1
    current_stored_group = engine._order_groups[order_id]
    assert not current_stored_group.is_terminal

    # Synthesize a transaction lifecycle response marking execution fulfillment
    receipt = create_order_receipt_factory(
        group_id=order_id,
        client_order_id=order_id,
        state=OrderState.FILLED,
    )
    notification_event = BrokerEvent(
        event_type=EventType.ORDER_NOTIFICATION,
        payload=receipt,
    )

    # Route transmission through the main entry point dispatcher
    engine._process_broker_event(notification_event)

    # Assert that the group remains alive in RAM under the active exposure flag
    assert len(engine._order_groups) == 1
    assert not current_stored_group.is_terminal

# -----------------------------------------------------------------------------

def test_engine_reconciles_parent_rejection_and_evicts_group_cleanly() -> None:
    """Ensures parent rejection triggers immediate RAM eviction if no children exist."""
    bot = FakeBot()
    broker = FakeBrokerAdapter()
    registry = create_contract_registry_factory()
    sizer = create_position_sizer_factory()

    engine = AegisExecutionEngine(
        bot=bot,
        broker_adapter=broker,
        contract_registry=registry,
        position_sizer=sizer,
    )

    # Seed the volatile execution registry with an active pending trade intent
    parent_order = create_order_factory(stop_loss_price=None, take_profit_price=None)
    engine._register_order_group(parent_order)
    order_id = parent_order.client_order_id

    # Synthesize an infrastructure failure response marking rejection
    receipt = create_order_receipt_factory(
        group_id=order_id,
        client_order_id=order_id,
        state=OrderState.REJECTED,
    )
    notification_event = BrokerEvent(
        event_type=EventType.ORDER_NOTIFICATION,
        payload=receipt,
    )

    # Route transmission through the main entry point dispatcher
    engine._process_broker_event(notification_event)

    # Assert that the engine successfully evacuated the rejected group from RAM
    assert len(engine._order_groups) == 0

# -----------------------------------------------------------------------------

def test_engine_trade_notification_reconciliation_logic() -> None:
    """Verifies clearing receipts evaluate authorized unwinds vs external closures."""
    bot = FakeBot()
    broker = FakeBrokerAdapter()
    registry = create_contract_registry_factory()
    sizer = create_position_sizer_factory()

    # --- Scenario A: Nominal Closing Sequence (Child Fills -> Clearing Confirms) ---
    engine_a = AegisExecutionEngine(
        bot=bot, broker_adapter=broker, contract_registry=registry, position_sizer=sizer
    )
    # Inject prices to ensure the engine unfolds protective child sub-orders
    parent_a = create_order_factory(
        client_order_id='A1',
        stop_loss_price=Decimal('1.0750'),
        take_profit_price=Decimal('1.0950'),
    )
    engine_a._register_order_group(parent_a)
    group_a = engine_a._order_groups['A1']

    # Parent execution triggers active exposure
    engine_a._process_broker_event(BrokerEvent(
        event_type=EventType.ORDER_NOTIFICATION,
        payload=create_order_receipt_factory(
            group_id='A1', client_order_id='A1', state=OrderState.FILLED
        )
    ))

    # Child protection fills triggering closing sequester state
    engine_a._process_broker_event(BrokerEvent(
        event_type=EventType.ORDER_NOTIFICATION,
        payload=create_order_receipt_factory(
            group_id='A1', client_order_id='A1-SL', state=OrderState.FILLED
        )
    ))
    assert not group_a.is_terminal
    assert 'A1' in engine_a._order_groups

    # Brother protection gets canceled cleanly post matching
    engine_a._process_broker_event(BrokerEvent(
        event_type=EventType.ORDER_NOTIFICATION,
        payload=create_order_receipt_factory(
            group_id='A1', client_order_id='A1-TP', state=OrderState.CANCELED
        )
    ))

    # Clearing notification confirms inventory flat -> RAM evacuation triggered
    engine_a._process_broker_event(BrokerEvent(
        event_type=EventType.TRADE_NOTIFICATION,
        payload=create_trade_receipt_factory(group_id='A1', is_open=False)
    ))
    assert 'A1' not in engine_a._order_groups

    # --- Scenario B: Severe Rupture (Clandestine External Position Closure) ---
    engine_b = AegisExecutionEngine(
        bot=bot, broker_adapter=broker, contract_registry=registry, position_sizer=sizer
    )
    # Inject prices here as well to maintain structural consistency
    parent_b = create_order_factory(
        client_order_id='B1',
        stop_loss_price=Decimal('1.0750'),
        take_profit_price=Decimal('1.0950'),
    )
    engine_b._register_order_group(parent_b)

    # Parent execution triggers active exposure
    engine_b._process_broker_event(BrokerEvent(
        event_type=EventType.ORDER_NOTIFICATION,
        payload=create_order_receipt_factory(
            group_id='B1', client_order_id='B1', state=OrderState.FILLED
        )
    ))

    # Clearing notification arrives flat while group is ACTIVE (no child ever filled)
    engine_b._process_broker_event(BrokerEvent(
        event_type=EventType.TRADE_NOTIFICATION,
        payload=create_trade_receipt_factory(group_id='B1', is_open=False)
    ))

    # Assert the engine caught the platform bypass and flagged corruption parameters
    assert 'B1' in engine_b._order_groups

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
