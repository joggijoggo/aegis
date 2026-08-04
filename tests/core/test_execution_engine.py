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
    OrderReceipt,
    OrderStatus,
)
from core.position_sizer import PositionSizer
from tests.testutils import (
    BASE_TIMESTAMP,
    DEFAULT_SYMBOL,
    FakeBot,
    FakeBrokerAdapter,
    FakeMarketFeed,
    create_contract_specification_factory,
    create_market_context_factory,
    create_order_factory,
    create_position_sizer_factory,
)
from tests.testutils.factories import create_trade_receipt_factory

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
    assert recorded_group.group_id == order_id
    assert order_id in recorded_group.orders
    assert recorded_group.status == OrderStatus.PENDING

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

def test_engine_reconciles_order_lifecycle_and_evicts_group() -> None:
    """Ensures order receipts mutate volatile tracking records and clean RAM."""
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

    # Seed the volatile execution registry with an active pending trade intent
    parent_order = create_order_factory()
    engine._register_order_group(parent_order)
    order_id = parent_order.client_order_id

    assert len(engine._order_groups) == 1

    current_stored_group = engine._order_groups[order_id]
    assert current_stored_group.status == OrderStatus.PENDING

    # Synthesize a transaction lifecycle response marking execution fulfillment
    receipt = OrderReceipt(
        average_execution_price=Decimal("1.08500"),
        broker_order_id="BRK-12345",
        client_order_id=order_id,
        executed_quantity=Decimal("1.0"),
        group_id=order_id,
        reject_reason=None,
        status=OrderStatus.FILLED,
    )
    notification_event = BrokerEvent(
        event_type=EventType.ORDER_NOTIFICATION, payload=receipt
    )

    # Route transmission through the main entry point dispatcher
    engine._process_broker_event(notification_event)

    # Assert binary eviction rule successfully cleared the record from memory
    assert len(engine._order_groups) == 0

# -----------------------------------------------------------------------------

def test_engine_reconciles_trade_lifecycle_and_evicts_group() -> None:
    """Ensures trade clearing receipts evaluate closure and clean RAM."""
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

    # Seed the volatile execution registry with an active trading group entry
    parent_order = create_order_factory()
    engine._register_order_group(parent_order)
    group_id = parent_order.client_order_id

    assert len(engine._order_groups) == 1

    # Synthesize a trade notification clearing event marking final closure
    receipt = create_trade_receipt_factory(
        group_id=group_id,
        is_open=False,
    )
    notification_event = BrokerEvent(
        event_type=EventType.TRADE_NOTIFICATION,
        payload=receipt,
    )

    # Route transmission through the main entry point dispatcher
    engine._process_broker_event(notification_event)

    # Assert that the engine successfully evacuated the completed group from RAM
    assert len(engine._order_groups) == 0

# -----------------------------------------------------------------------------

def test_engine_register_order_group_unpacking_variants() -> None:
    """Verifies that order unpacking accurately maps variants of child brackets."""
    bot = FakeBot()
    broker = FakeBrokerAdapter()
    registry = ContractRegistry(specifications={})
    sizer = create_position_sizer_factory()

    # --- Scenario 1: Parent with full bracket protections (Nominal case) ---
    engine_full = AegisExecutionEngine(
        bot=bot,
        broker_adapter=broker,
        contract_registry=registry,
        position_sizer=sizer,
    )
    order_full = create_order_factory(
        client_order_id='ORD-FULL',
        stop_loss_price=Decimal('1.08000'),
        take_profit_price=Decimal('1.09500'),
    )
    engine_full._register_order_group(order_full)
    group_full = engine_full._order_groups['ORD-FULL']

    assert len(group_full.orders) == 3
    assert 'ORD-FULL' in group_full.orders
    assert 'ORD-FULL-SL' in group_full.orders
    assert 'ORD-FULL-TP' in group_full.orders

    # --- Scenario 2: Parent with Stop-Loss only ---
    engine_sl_only = AegisExecutionEngine(
        bot=bot,
        broker_adapter=broker,
        contract_registry=registry,
        position_sizer=sizer,
    )
    order_sl_only = create_order_factory(
        client_order_id='ORD-SL-ONLY',
        stop_loss_price=Decimal('1.08000'),
        take_profit_price=None,
    )
    engine_sl_only._register_order_group(order_sl_only)
    group_sl = engine_sl_only._order_groups['ORD-SL-ONLY']

    assert len(group_sl.orders) == 2
    assert 'ORD-SL-ONLY' in group_sl.orders
    assert 'ORD-SL-ONLY-SL' in group_sl.orders
    assert 'ORD-SL-ONLY-TP' not in group_sl.orders

    # --- Scenario 3: Parent with Take-Profit only (Asymmetric Risk Spec) ---
    engine_tp_only = AegisExecutionEngine(
        bot=bot,
        broker_adapter=broker,
        contract_registry=registry,
        position_sizer=sizer,
    )
    order_tp_only = create_order_factory(
        client_order_id='ORD-TP-ONLY',
        stop_loss_price=None,
        take_profit_price=Decimal('1.09500'),
    )
    engine_tp_only._register_order_group(order_tp_only)
    group_tp = engine_tp_only._order_groups['ORD-TP-ONLY']

    assert len(group_tp.orders) == 2
    assert 'ORD-TP-ONLY' in group_tp.orders
    assert 'ORD-TP-ONLY-SL' not in group_tp.orders
    assert 'ORD-TP-ONLY-TP' in group_tp.orders

    # --- Scenario 4: Parent with no protections at all (Bare execution) ---
    engine_bare = AegisExecutionEngine(
        bot=bot,
        broker_adapter=broker,
        contract_registry=registry,
        position_sizer=sizer,
    )
    order_bare = create_order_factory(
        client_order_id='ORD-BARE',
        stop_loss_price=None,
        take_profit_price=None,
    )
    engine_bare._register_order_group(order_bare)
    group_bare = engine_bare._order_groups['ORD-BARE']

    assert len(group_bare.orders) == 1
    assert 'ORD-BARE' in group_bare.orders
    assert 'ORD-BARE-SL' not in group_bare.orders
    assert 'ORD-BARE-TP' not in group_bare.orders

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
