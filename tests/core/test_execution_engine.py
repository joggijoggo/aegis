"""Aegis Framework - Execution Engine Unit Tests.

Validates core engine orchestration mechanics, transaction lifecycle dispatching,
and contextual order generation workflows.
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from core.execution_engine import AegisExecutionEngine
from core.models import (
    ExposureIntent,
    MarketContext,
    MarketPricePoint,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_engine_cycle_executes_order_on_valid_intent() -> None:
    """Ensures a valid bot alpha direction triggers full sizer routing."""
    mock_bot = MagicMock()
    mock_bot.warm_up_period = 10
    mock_adapter = MagicMock()
    mock_registry = MagicMock()
    mock_sizer = MagicMock()

    engine = AegisExecutionEngine(
        bot=mock_bot,
        broker_adapter=mock_adapter,
        contract_registry=mock_registry,
        position_sizer=mock_sizer,
    )

    prices = MagicMock(spec=MarketPricePoint)
    prices.mid_price = 1.08500
    context = MagicMock(spec=MarketContext)
    context.prices = prices
    market_feed = iter([context])

    intent = ExposureIntent(
        alpha_direction=1.0,
        stop_loss_ticks=500,
        take_profit_ticks=1000,
    )
    mock_bot.evaluate.return_value = intent

    spec = MagicMock()
    mock_registry.get_specification.return_value = spec
    snapshot = MagicMock()
    mock_adapter.get_account_snapshot.return_value = snapshot

    mock_order = MagicMock()
    mock_sizer.create_order.return_value = mock_order

    engine.run_execution_cycle(symbol='EURUSD', market_feed=market_feed)

    mock_registry.get_specification.assert_called_once_with('EURUSD')
    mock_adapter.get_account_snapshot.assert_called_once()
    mock_sizer.create_order.assert_called_once_with(
        exposure_intent=intent,
        risk_percent=Decimal('0.01'),
        contract_specification=spec,
        account_snapshot=snapshot,
        market_context=context,
    )
    mock_adapter.execute_order.assert_called_once_with(mock_order)

# -----------------------------------------------------------------------------

def test_engine_cycle_raises_not_implemented_error_for_neutral_alpha() -> None:
    """Ensures a 0.0 alpha direction triggers an early closure exception."""
    mock_bot = MagicMock()
    mock_bot.warm_up_period = 10
    mock_adapter = MagicMock()
    mock_registry = MagicMock()
    mock_sizer = MagicMock()

    engine = AegisExecutionEngine(
        bot=mock_bot,
        broker_adapter=mock_adapter,
        contract_registry=mock_registry,
        position_sizer=mock_sizer,
    )

    prices = MagicMock(spec=MarketPricePoint)
    prices.mid_price = 1.08500
    context = MagicMock(spec=MarketContext)
    context.prices = prices
    market_feed = iter([context])

    intent = ExposureIntent(
        alpha_direction=0.0,
        stop_loss_ticks=500,
        take_profit_ticks=1000,
    )
    mock_bot.evaluate.return_value = intent

    with pytest.raises(NotImplementedError):
        engine.run_execution_cycle(symbol='EURUSD', market_feed=market_feed)

    mock_registry.get_specification.assert_not_called()
    mock_adapter.get_account_snapshot.assert_not_called()
    mock_sizer.create_order.assert_not_called()

# -----------------------------------------------------------------------------

def test_engine_cycle_skips_processing_on_none_intent() -> None:
    """Ensures an absent alpha signal skips downstream infrastructure routing."""
    mock_bot = MagicMock()
    mock_bot.warm_up_period = 10
    mock_adapter = MagicMock()
    mock_registry = MagicMock()
    mock_sizer = MagicMock()

    engine = AegisExecutionEngine(
        bot=mock_bot,
        broker_adapter=mock_adapter,
        contract_registry=mock_registry,
        position_sizer=mock_sizer,
    )

    prices = MagicMock(spec=MarketPricePoint)
    prices.mid_price = 1.08500
    context = MagicMock(spec=MarketContext)
    context.prices = prices
    market_feed = iter([context])

    intent = ExposureIntent(
        alpha_direction=None,
        stop_loss_ticks=500,
        take_profit_ticks=1000,
    )
    mock_bot.evaluate.return_value = intent

    engine.run_execution_cycle(symbol='EURUSD', market_feed=market_feed)

    mock_registry.get_specification.assert_not_called()
    mock_adapter.get_account_snapshot.assert_not_called()
    mock_sizer.create_order.assert_not_called()

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
