"""Aegis Framework - Backtrader Broker Adapter Unit Tests.

Verifies bracket order conversion from pips metrics to absolute execution prices.
"""

from unittest.mock import MagicMock

import pytest

from brokers.backtrader_adapter import BacktraderBrokerAdapter
from core.models import OrderType
from core.models import TransactionSide

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_backtrader_adapter_calculates_absolute_bracket_prices_for_short():
    """Validates absolute pricing translation loops for SHORT bracket orders."""
    # 1. Create a mock representation of Backtrader strategy component
    mock_bt_strategy = MagicMock()

    # Simulate a current market asset data structure layer matching line series contract
    mock_data = MagicMock()
    mock_data.close = MagicMock()
    mock_data.close.__float__.return_value = 1.1000
    mock_bt_strategy.data = mock_data

    # Simulate broker state indicators
    mock_bt_strategy.broker.get_cash.return_value = 10000.0
    mock_bt_strategy.broker.get_value.return_value = 10000.0

    # 2. Instantiate the port adapter anchoring the mock strategy
    adapter = BacktraderBrokerAdapter(bt_strategy=mock_bt_strategy)

    # 3. Trigger a SHORT order transaction payload request
    receipt = adapter.place_order(
        symbol="EURUSD",
        side=TransactionSide.SHORT,
        order_type=OrderType.MARKET,
        volume_lots=1.0,
        stop_loss_pips=20.0,
        take_profit_pips=40.0
    )

    # 4. Verify transaction tracking receipt output parameters
    assert receipt["status"] == "SUBMITTED"
    assert receipt["symbol"] == "EURUSD"

    # 5. Verify mathematical translation to absolute prices for a SHORT trade
    mock_bt_strategy.sell_bracket.assert_called_once_with(
        price=1.1000,
        stopprice=1.1020,
        limitprice=1.0960,
        size=100000  # 1.0 standard lot size multiplier anchor
    )

    # 6. Verify broker snapshot synchronization interface routing
    snapshot = adapter.get_portfolio_snapshot()
    assert snapshot["balance"] == 10000.0
    assert snapshot["equity"] == 10000.0

# -----------------------------------------------------------------------------

def test_backtrader_adapter_calculates_absolute_bracket_prices_for_long():
    """Validates absolute pricing translation loops for LONG bracket orders."""
    mock_bt_strategy = MagicMock()
    mock_data = MagicMock()
    mock_data.close = MagicMock()
    mock_data.close.__float__.return_value = 1.1000
    mock_bt_strategy.data = mock_data

    mock_bt_strategy.broker.get_cash.return_value = 10000.0
    mock_bt_strategy.broker.get_value.return_value = 10000.0

    adapter = BacktraderBrokerAdapter(bt_strategy=mock_bt_strategy)

    # Trigger a LONG order transaction payload request
    receipt = adapter.place_order(
        symbol="EURUSD",
        side=TransactionSide.LONG,
        order_type=OrderType.MARKET,
        volume_lots=1.0,
        stop_loss_pips=20.0,
        take_profit_pips=40.0
    )

    assert receipt["status"] == "SUBMITTED"
    assert receipt["symbol"] == "EURUSD"

    # Verify mathematical translation to absolute prices for a LONG trade
    mock_bt_strategy.buy_bracket.assert_called_once_with(
        price=1.1000,
        stopprice=1.0980,
        limitprice=1.1040,
        size=100000  # 1.0 standard lot size multiplier anchor
    )

# -----------------------------------------------------------------------------

def test_backtrader_adapter_raises_not_implemented_error_on_missing_parameters():
    """Validates that a NotImplementedError is raised if protection is missing."""
    mock_bt_strategy = MagicMock()
    adapter = BacktraderBrokerAdapter(bt_strategy=mock_bt_strategy)

    # Execute a payload routing request with missing protection limits
    with pytest.raises(NotImplementedError) as exc_info:
        adapter.place_order(
            symbol="EURUSD",
            side=TransactionSide.LONG,
            order_type=OrderType.MARKET,
            volume_lots=1.0,
            stop_loss_pips=None,
            take_profit_pips=40.0
        )

    assert "requires both stop_loss_pips and take_profit_pips" in str(exc_info.value)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
