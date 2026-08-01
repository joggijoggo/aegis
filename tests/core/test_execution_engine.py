"""Aegis Framework - Execution Engine Unit Tests.

Validates core engine orchestration mechanics, transaction lifecycle dispatching,
and contextual order generation workflows.
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from core.contract_registry import ContractRegistry
from core.execution_engine import AegisExecutionEngine
from core.models import (
    BrokerEvent,
    EventType,
    ExposureIntent,
    MarketContext,
    MarketPricePoint,
)
from core.position_sizer import PositionSizer
from tests.testutils import (
    BASE_TIMESTAMP,
    DEFAULT_SYMBOL,
    FakeBot,
    FakeBrokerAdapter,
    FakeMarketFeed,
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

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
