"""Aegis Framework - Backtrader Broker Adapter Unit Tests.

Verifies bracket pricing conversions, market routing layers, and contract parameters.
"""

from unittest.mock import MagicMock

import pytest

from brokers.backtrader_adapter import BacktraderBrokerAdapter
from core.models import InstrumentSpecification
from core.models import OrderType
from core.models import TransactionSide
from core.registry import InstrumentRegistry

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

_TEST_SPECS = {
    "EURUSD": InstrumentSpecification(
        base_spread_ticks=0.6,
        tick_size=0.0001,
        volatility_factor=0.1,
        lot_size=100000,
    ),
}

TEST_REGISTRY = InstrumentRegistry(specifications=_TEST_SPECS)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_backtrader_adapter_fetches_instrument_specifications():
    """Verify that the outbound adapter routes registry lookups cleanly."""
    mock_bt_strategy = MagicMock()

    adapter = BacktraderBrokerAdapter(
        bt_strategy=mock_bt_strategy,
        instrument_registry=TEST_REGISTRY,
    )

    assert (
        adapter.get_instrument_specification(symbol="EURUSD") is _TEST_SPECS["EURUSD"]
    )

    with pytest.raises(ValueError, match="is missing from central instrument registry"):
        adapter.get_instrument_specification(symbol="UNKNOWN")

# -----------------------------------------------------------------------------

def test_backtrader_adapter_fetches_portfolio_balances_snapshot():
    """Validates financial tracking indirection routing balances snapshots."""
    mock_bt_strategy = MagicMock()
    mock_bt_strategy.broker.get_cash.return_value = 5000.0
    mock_bt_strategy.broker.get_value.return_value = 5250.0

    adapter = BacktraderBrokerAdapter(
        bt_strategy=mock_bt_strategy,
        instrument_registry=TEST_REGISTRY,
    )

    snapshot = adapter.get_portfolio_snapshot()
    assert snapshot["balance"] == 5000.0
    assert snapshot["equity"] == 5250.0

# -----------------------------------------------------------------------------

def test_backtrader_adapter_routes_absolute_bracket_prices_for_long():
    """Validates absolute pricing translation loops for LONG bracket orders."""
    mock_bt_strategy = MagicMock()
    mock_bt_strategy.data.close = 1.1000

    adapter = BacktraderBrokerAdapter(
        bt_strategy=mock_bt_strategy,
        instrument_registry=TEST_REGISTRY,
    )

    receipt = adapter.place_order(
        symbol="EURUSD",
        side=TransactionSide.LONG,
        order_type=OrderType.MARKET,
        volume_lots=1.0,
        stop_loss_price=1.0980,
        take_profit_price=1.1040,
    )

    assert receipt["status"] == "SUBMITTED"
    assert receipt["symbol"] == "EURUSD"

    mock_bt_strategy.buy_bracket.assert_called_once_with(
        price=1.1000,
        stopprice=1.0980,
        limitprice=1.1040,
        size=100000,
    )

# -----------------------------------------------------------------------------

def test_backtrader_adapter_routes_absolute_bracket_prices_for_short():
    """Validates absolute pricing translation loops for SHORT bracket orders."""
    mock_bt_strategy = MagicMock()
    mock_bt_strategy.data.close = 1.1000

    mock_bt_strategy.broker.get_cash.return_value = 10000.0
    mock_bt_strategy.broker.get_value.return_value = 10000.0

    adapter = BacktraderBrokerAdapter(
        bt_strategy=mock_bt_strategy,
        instrument_registry=TEST_REGISTRY,
    )

    receipt = adapter.place_order(
        symbol="EURUSD",
        side=TransactionSide.SHORT,
        order_type=OrderType.MARKET,
        volume_lots=1.0,
        stop_loss_price=1.1020,
        take_profit_price=1.0960,
    )

    assert receipt["status"] == "SUBMITTED"
    assert receipt["symbol"] == "EURUSD"

    mock_bt_strategy.sell_bracket.assert_called_once_with(
        price=1.1000,
        stopprice=1.1020,
        limitprice=1.0960,
        size=100000,
    )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
