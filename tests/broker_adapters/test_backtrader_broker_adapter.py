"""Aegis Framework - Backtrader Broker Adapter Component Tests.

Validates accounting parsing, asynchronous queue polling, and notification mapping.
"""

from decimal import Decimal
from queue import Queue
from unittest.mock import call, MagicMock

import backtrader as bt
import pytest

from broker_adapters.backtrader_bridge import BacktraderBridge
from broker_adapters.backtrader_broker_adapter import (
    AssetSymbolNotFoundError,
    BacktraderBrokerAdapter,
    InvalidOrderQuantityError,
    InvalidProtectionPriceError,
)
from core.models import (
    AccountSnapshot,
    BrokerEvent,
    EventType,
    Order,
    OrderSide,
    OrderType,
    TimeInForce,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_backtrader_broker_adapter_account_snapshot() -> None:
    """Verifies precision parsing of float portfolio balances into decimals."""
    mock_bridge = MagicMock(spec=BacktraderBridge)

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

def test_backtrader_broker_adapter_asymmetric_bracket_transmission() -> None:
    """Verifies that an asymmetric bracket with only Stop Loss forces transmit to True on the child."""
    mock_bridge = MagicMock(spec=BacktraderBridge)
    mock_strategy = MagicMock()
    mock_parent_order = MagicMock()
    mock_strategy.buy.return_value = mock_parent_order

    mock_data = MagicMock(spec=bt.feed.DataBase)
    mock_data._name = 'EURUSD'
    mock_strategy.datas = [mock_data]
    mock_bridge.strategy = mock_strategy

    adapter = BacktraderBrokerAdapter(bridge=mock_bridge)

    mock_order = MagicMock(spec=Order)
    mock_order.quantity = Decimal('1.0')
    mock_order.symbol = 'EURUSD'
    mock_order.side = OrderSide.BUY
    mock_order.order_type = OrderType.MARKET
    mock_order.time_in_force = TimeInForce.GTC
    mock_order.stop_loss_price = Decimal('1.1200')
    mock_order.take_profit_price = None
    mock_order.client_order_id = 'AEGIS-ASYM'

    adapter.submit_order(mock_order)

    mock_strategy.buy.assert_called_once_with(
        data=mock_data, size=1.0, exectype=bt.Order.Market, valid=None, transmit=False, client_order_id='AEGIS-ASYM'
    )
    mock_strategy.sell.assert_called_once_with(
        data=mock_data, size=1.0, exectype=bt.Order.Stop, price=1.1200, valid=None, parent=mock_parent_order, transmit=True, client_order_id='AEGIS-ASYM-SL'
    )
# -----------------------------------------------------------------------------

def test_backtrader_broker_adapter_asymmetric_bracket_missing_take_profit() -> None:
    """Verifies that a bracket missing a Take Profit forces transmit to True on the Stop Loss child."""
    mock_bridge = MagicMock(spec=BacktraderBridge)
    mock_strategy = MagicMock()
    mock_parent_order = MagicMock()
    mock_strategy.buy.return_value = mock_parent_order

    mock_data = MagicMock(spec=bt.feed.DataBase)
    mock_data._name = 'EURUSD'
    mock_strategy.datas = [mock_data]
    mock_bridge.strategy = mock_strategy

    adapter = BacktraderBrokerAdapter(bridge=mock_bridge)

    mock_order = MagicMock(spec=Order)
    mock_order.quantity = Decimal('1.0')
    mock_order.symbol = 'EURUSD'
    mock_order.side = OrderSide.BUY
    mock_order.order_type = OrderType.MARKET
    mock_order.time_in_force = TimeInForce.GTC
    mock_order.stop_loss_price = Decimal('1.1200')
    mock_order.take_profit_price = None  # Missing Take Profit
    mock_order.client_order_id = 'AEGIS-MISSING-TP'

    adapter.submit_order(mock_order)

    # Parent must hold transmission to let the child stack
    mock_strategy.buy.assert_called_once_with(
        data=mock_data, size=1.0, exectype=bt.Order.Market, valid=None, transmit=False, client_order_id='AEGIS-MISSING-TP'
    )
    # Child Stop Loss is the last link and must release the atomic block
    mock_strategy.sell.assert_called_once_with(
        data=mock_data, size=1.0, exectype=bt.Order.Stop, price=1.1200, valid=None, parent=mock_parent_order, transmit=True, client_order_id='AEGIS-MISSING-TP-SL'
    )

# -----------------------------------------------------------------------------

def test_backtrader_broker_adapter_asymmetric_bracket_missing_stop_loss() -> None:
    """Verifies that a bracket missing a Stop Loss forces transmit to True on the Take Profit child."""
    mock_bridge = MagicMock(spec=BacktraderBridge)
    mock_strategy = MagicMock()
    mock_parent_order = MagicMock()
    mock_strategy.buy.return_value = mock_parent_order

    mock_data = MagicMock(spec=bt.feed.DataBase)
    mock_data._name = 'EURUSD'
    mock_strategy.datas = [mock_data]
    mock_bridge.strategy = mock_strategy

    adapter = BacktraderBrokerAdapter(bridge=mock_bridge)

    mock_order = MagicMock(spec=Order)
    mock_order.quantity = Decimal('1.0')
    mock_order.symbol = 'EURUSD'
    mock_order.side = OrderSide.BUY
    mock_order.order_type = OrderType.MARKET
    mock_order.time_in_force = TimeInForce.GTC
    mock_order.stop_loss_price = None  # Missing Stop Loss
    mock_order.take_profit_price = Decimal('1.1400')
    mock_order.client_order_id = 'AEGIS-MISSING-SL'

    adapter.submit_order(mock_order)

    # Parent must hold transmission to let the child stack
    mock_strategy.buy.assert_called_once_with(
        data=mock_data, size=1.0, exectype=bt.Order.Market, valid=None, transmit=False, client_order_id='AEGIS-MISSING-SL'
    )
    # Child Take Profit is the last link and must release the atomic block
    mock_strategy.sell.assert_called_once_with(
        data=mock_data, size=1.0, exectype=bt.Order.Limit, price=1.1400, valid=None, parent=mock_parent_order, transmit=True, client_order_id='AEGIS-MISSING-SL-TP'
    )

# -----------------------------------------------------------------------------

def test_backtrader_broker_adapter_asset_not_found_guard() -> None:
    """Verifies that an AssetSymbolNotFoundError is raised if the asset is missing from Cerebro."""
    mock_bridge = MagicMock(spec=BacktraderBridge)
    mock_strategy = MagicMock()
    mock_strategy.datas = []
    mock_bridge.strategy = mock_strategy

    adapter = BacktraderBrokerAdapter(bridge=mock_bridge)

    mock_order = MagicMock(spec=Order)
    mock_order.quantity = Decimal('1.0')
    mock_order.symbol = 'UNKNOWN'
    mock_order.order_type = OrderType.MARKET
    mock_order.time_in_force = TimeInForce.GTC

    with pytest.raises(AssetSymbolNotFoundError, match="Requested asset symbol 'UNKNOWN' is not available"):
        adapter.submit_order(mock_order)

# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "sl_val, tp_val, expected_msg",
    [
        (Decimal('0.0'), Decimal('1.1100'), "Invalid Stop Loss price"),
        (Decimal('1.1200'), Decimal('-0.5'), "Invalid Take Profit price"),
    ]
)
def test_backtrader_broker_adapter_invalid_bracket_prices_enforcement(
    sl_val: Decimal,
    tp_val: Decimal,
    expected_msg: str,
) -> None:
    """Verifies that non-positive protection prices trigger an immediate InvalidProtectionPriceError."""
    mock_bridge = MagicMock(spec=BacktraderBridge)
    mock_strategy = MagicMock()

    mock_data = MagicMock(spec=bt.feed.DataBase)
    mock_data._name = 'EURUSD'
    mock_strategy.datas = [mock_data]
    mock_bridge.strategy = mock_strategy

    adapter = BacktraderBrokerAdapter(bridge=mock_bridge)

    mock_order = MagicMock(spec=Order)
    mock_order.quantity = Decimal('1.0')
    mock_order.symbol = 'EURUSD'
    mock_order.order_type = OrderType.MARKET
    mock_order.time_in_force = TimeInForce.GTC
    mock_order.stop_loss_price = sl_val
    mock_order.take_profit_price = tp_val

    with pytest.raises(InvalidProtectionPriceError, match=expected_msg):
        adapter.submit_order(mock_order)

# -----------------------------------------------------------------------------

def test_backtrader_broker_adapter_invalid_quantity_enforcement() -> None:
    """Verifies that an immediate InvalidOrderQuantityError is raised for non-positive volumes."""
    mock_bridge = MagicMock(spec=BacktraderBridge)
    adapter = BacktraderBrokerAdapter(bridge=mock_bridge)

    mock_order = MagicMock(spec=Order)
    mock_order.quantity = Decimal('0.0')
    mock_order.order_type = OrderType.MARKET
    mock_order.time_in_force = TimeInForce.GTC

    with pytest.raises(InvalidOrderQuantityError, match="Execution volume must be strictly positive"):
        adapter.submit_order(mock_order)

# -----------------------------------------------------------------------------

def test_backtrader_broker_adapter_market_order_submission() -> None:
    """Verifies that submit_order routes standard MARKET orders dynamically via function pointers."""
    mock_bridge = MagicMock(spec=BacktraderBridge)
    mock_strategy = MagicMock()
    mock_data = MagicMock(spec=bt.feed.DataBase)
    mock_data._name = 'EURUSD'
    mock_strategy.datas = [mock_data]
    mock_bridge.strategy = mock_strategy

    adapter = BacktraderBrokerAdapter(bridge=mock_bridge)

    mock_order = MagicMock(spec=Order)
    mock_order.quantity = Decimal('1.5')
    mock_order.symbol = 'EURUSD'
    mock_order.side = OrderSide.BUY
    mock_order.order_type = OrderType.MARKET
    mock_order.time_in_force = TimeInForce.GTC
    mock_order.stop_loss_price = None
    mock_order.take_profit_price = None
    mock_order.client_order_id = 'AEGIS-MKT'

    adapter.submit_order(mock_order)

    mock_strategy.buy.assert_called_once_with(
        data=mock_data, size=1.5, exectype=bt.Order.Market, valid=None, transmit=True, client_order_id='AEGIS-MKT'
    )

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

# -----------------------------------------------------------------------------

def test_backtrader_broker_adapter_symmetric_sell_bracket_routing() -> None:
    """Verifies that a full SELL bracket routes correctly via function pointers and links children."""
    mock_bridge = MagicMock(spec=BacktraderBridge)
    mock_strategy = MagicMock()
    mock_parent_order = MagicMock()
    mock_strategy.sell.return_value = mock_parent_order

    mock_data = MagicMock(spec=bt.feed.DataBase)
    mock_data._name = 'EURUSD'
    mock_strategy.datas = [mock_data]
    mock_bridge.strategy = mock_strategy

    adapter = BacktraderBrokerAdapter(bridge=mock_bridge)

    mock_order = MagicMock(spec=Order)
    mock_order.quantity = Decimal('2.5')
    mock_order.symbol = 'EURUSD'
    mock_order.side = OrderSide.SELL
    mock_order.order_type = OrderType.MARKET
    mock_order.time_in_force = TimeInForce.GTC
    mock_order.stop_loss_price = Decimal('1.1350')
    mock_order.take_profit_price = Decimal('1.1150')
    mock_order.client_order_id = 'AEGIS-SELL-BRK'

    adapter.submit_order(mock_order)

    mock_strategy.sell.assert_called_once_with(
        data=mock_data, size=2.5, exectype=bt.Order.Market, valid=None, transmit=False, client_order_id='AEGIS-SELL-BRK'
    )

    expected_child_calls = [
        call(
            data=mock_data,
            size=2.5,
            exectype=bt.Order.Stop,
            price=1.1350,
            valid=None,
            parent=mock_parent_order,
            transmit=False,
            client_order_id='AEGIS-SELL-BRK-SL'
        ),
        call(
            data=mock_data,
            size=2.5,
            exectype=bt.Order.Limit,
            price=1.1150,
            valid=None,
            parent=mock_parent_order,
            transmit=True,
            client_order_id='AEGIS-SELL-BRK-TP'
        )
    ]
    mock_strategy.buy.assert_has_calls(expected_child_calls, any_order=False)

# -----------------------------------------------------------------------------

def test_backtrader_broker_adapter_unsupported_policies() -> None:
    """Verifies that unsupported OrderTypes and TimeInForce trigger NotImplementedError."""
    mock_bridge = MagicMock(spec=BacktraderBridge)
    adapter = BacktraderBrokerAdapter(bridge=mock_bridge)

    mock_order_type = MagicMock(spec=Order)
    mock_order_type.quantity = Decimal('1.0')
    mock_order_type.order_type = OrderType.LIMIT
    mock_order_type.time_in_force = TimeInForce.GTC

    with pytest.raises(NotImplementedError, match="Only MARKET orders are supported"):
        adapter.submit_order(mock_order_type)

    mock_order_tif = MagicMock(spec=Order)
    mock_order_tif.quantity = Decimal('1.0')
    mock_order_tif.order_type = OrderType.MARKET
    mock_order_tif.time_in_force = TimeInForce.DAY

    with pytest.raises(NotImplementedError, match="TimeInForce policy 'TimeInForce.DAY' is not supported"):
        adapter.submit_order(mock_order_tif)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
