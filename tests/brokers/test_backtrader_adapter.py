"""Aegis Framework - Backtrader Broker Adapter Unit Tests.

Verifies bracket order conversion from pips metrics to absolute execution prices.
"""

from unittest.mock import MagicMock

import pytest

from brokers.backtrader_adapter import BacktraderBrokerAdapter
from core.models import InstrumentSpecification
from core.models import OrderType
from core.models import TransactionSide

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_backtrader_adapter_calculates_absolute_bracket_prices_for_short():
    """Validates absolute pricing translation loops for SHORT bracket orders."""
    mock_bt_strategy = MagicMock()
    mock_data = MagicMock()
    mock_data.close = MagicMock()
    mock_data.close.__float__.return_value = 1.1000
    mock_bt_strategy.data = mock_data

    mock_bt_strategy.broker.get_cash.return_value = 10000.0
    mock_bt_strategy.broker.get_value.return_value = 10000.0

    registry: dict[str, InstrumentSpecification] = {
        "EURUSD": InstrumentSpecification(pip_size=0.0001, lot_size=100000)
    }

    adapter = BacktraderBrokerAdapter(
        bt_strategy=mock_bt_strategy,
        instrument_specs=registry,
    )

    receipt = adapter.place_order(
        symbol="EURUSD",
        side=TransactionSide.SHORT,
        order_type=OrderType.MARKET,
        volume_lots=1.0,
        stop_loss_pips=20.0,
        take_profit_pips=40.0
    )

    assert receipt["status"] == "SUBMITTED"
    assert receipt["symbol"] == "EURUSD"

    mock_bt_strategy.sell_bracket.assert_called_once_with(
        price=1.1000,
        stopprice=1.1020,
        limitprice=1.0960,
        size=100000  # 1.0 standard lot size multiplier anchor
    )

    snapshot = adapter.get_portfolio_snapshot()
    assert snapshot["balance"] == 10000.0
    assert snapshot["equity"] == 10000.0


# -----------------------------------------------------------------------------

def test_backtrader_adapter_accepts_dynamic_custom_assets_injection():
    """Validates that users can dynamically register custom assets like AUDJPY."""
    mock_bt_strategy = MagicMock()
    mock_data = MagicMock()
    mock_data.close = MagicMock()
    mock_data.close.__float__.return_value = 95.50
    mock_bt_strategy.data = mock_data

    registry: dict[str, InstrumentSpecification] = {
        "AUDJPY": InstrumentSpecification(pip_size=0.01, lot_size=100000)
    }

    adapter = BacktraderBrokerAdapter(
        bt_strategy=mock_bt_strategy,
        instrument_specs=registry,
    )

    adapter.place_order(
        symbol="AUDJPY",
        side=TransactionSide.LONG,
        order_type=OrderType.MARKET,
        volume_lots=1.5,
        stop_loss_pips=30.0,
        take_profit_pips=60.0
    )

    mock_bt_strategy.buy_bracket.assert_called_once_with(
        price=95.50,
        stopprice=95.20,
        limitprice=96.10,
        size=150000
    )


# -----------------------------------------------------------------------------

def test_backtrader_adapter_raises_error_on_unregistered_asset_symbol():
    """Validates that a ValueError is raised if the instrument is missing."""
    mock_bt_strategy = MagicMock()
    registry: dict[str, InstrumentSpecification] = {}

    adapter = BacktraderBrokerAdapter(
        bt_strategy=mock_bt_strategy,
        instrument_specs=registry,
    )

    with pytest.raises(ValueError) as exc_info:
        adapter.place_order(
            symbol="UNKNOWN",
            side=TransactionSide.LONG,
            order_type=OrderType.MARKET,
            volume_lots=1.0,
            stop_loss_pips=20.0,
            take_profit_pips=40.0
        )

    assert "missing from instrument registry" in str(exc_info.value)


# -----------------------------------------------------------------------------

def test_backtrader_adapter_raises_not_implemented_error_on_missing_parameters():
    """Validates that a NotImplementedError is raised if protection is missing."""
    mock_bt_strategy = MagicMock()
    registry: dict[str, InstrumentSpecification] = {}

    adapter = BacktraderBrokerAdapter(
        bt_strategy=mock_bt_strategy,
        instrument_specs=registry,
    )

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
