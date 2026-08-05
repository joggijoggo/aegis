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
    OrderReceipt,
    OrderSide,
    OrderState,
    OrderType,
    PositionLedgerSnapshot,
    PositionSide,
    TimeInForce,
    TradeReceipt,
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

    # Inject an empty positions mapping to simulate a portfolio clear of exposure
    mock_strategy.positions = {}
    mock_bridge.strategy = mock_strategy

    adapter = BacktraderBrokerAdapter(bridge=mock_bridge)
    snapshot = adapter._get_account_snapshot()

    assert isinstance(snapshot, AccountSnapshot)
    assert snapshot.currency == 'USD'
    assert snapshot.balance == Decimal('10000.50')
    assert snapshot.equity == Decimal('10500.75')
    assert snapshot.available_margin == Decimal('10000.50')

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
    start_tradeid = adapter._next_trade_id

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
        data=mock_data,
        size=1.0,
        exectype=bt.Order.Market,
        valid=None,
        transmit=False,
        client_order_id='AEGIS-MISSING-SL',
        tradeid=start_tradeid,
    )
    # Child Take Profit is the last link and must release the atomic block
    mock_strategy.sell.assert_called_once_with(
        data=mock_data,
        size=1.0,
        exectype=bt.Order.Limit,
        price=1.1400,
        valid=None,
        parent=mock_parent_order,
        transmit=True,
        client_order_id='AEGIS-MISSING-SL-TP',
        tradeid=start_tradeid,
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
    start_tradeid = adapter._next_trade_id

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
        data=mock_data,
        size=1.0,
        exectype=bt.Order.Market,
        valid=None,
        transmit=False,
        client_order_id='AEGIS-MISSING-TP',
        tradeid=start_tradeid,
    )
    # Child Stop Loss is the last link and must release the atomic block
    mock_strategy.sell.assert_called_once_with(
        data=mock_data,
        size=1.0,
        exectype=bt.Order.Stop,
        price=1.1200,
        valid=None,
        parent=mock_parent_order,
        transmit=True,
        client_order_id='AEGIS-MISSING-TP-SL',
        tradeid=start_tradeid,
    )

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
    start_tradeid = adapter._next_trade_id

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
        data=mock_data,
        size=1.0,
        exectype=bt.Order.Market,
        valid=None,
        transmit=False,
        client_order_id='AEGIS-ASYM',
        tradeid=start_tradeid,
    )
    mock_strategy.sell.assert_called_once_with(
        data=mock_data,
        size=1.0,
        exectype=bt.Order.Stop,
        price=1.1200,
        valid=None,
        parent=mock_parent_order,
        transmit=True,
        client_order_id='AEGIS-ASYM-SL',
        tradeid=start_tradeid,
    )

# -----------------------------------------------------------------------------
def test_backtrader_broker_adapter_polling_fifo_flow_for_orders() -> None:
    """Verifies queue polling and structural unpacking for order events."""
    broker_queue: Queue = Queue()
    bridge_mock = MagicMock(spec=BacktraderBridge)
    bridge_mock.get_broker_queue.return_value = broker_queue

    adapter = BacktraderBrokerAdapter(bridge=bridge_mock)

    assert adapter.has_pending_events() is False

    mock_order = MagicMock()
    mock_order.ref = 101
    mock_order.status = bt.Order.Completed
    mock_order.info = { 'client_order_id': 'ORDER-A' }
    mock_order.executed = MagicMock()
    mock_order.executed.size.__float__.return_value = 10.0
    mock_order.executed.price.__float__.return_value = 1.2000

    broker_queue.put((EventType.ORDER_NOTIFICATION, mock_order))
    assert adapter.has_pending_events() is True

    event = adapter.poll_event()
    assert isinstance(event, BrokerEvent)
    assert event.event_type == EventType.ORDER_NOTIFICATION
    assert event.payload.broker_order_id == '101'
    assert event.payload.client_order_id == 'ORDER-A'
    assert event.payload.executed_quantity == Decimal('10.0')
    assert adapter.has_pending_events() is False

# -----------------------------------------------------------------------------

def test_backtrader_broker_adapter_polling_fifo_flow_for_trades() -> None:
    """Verifies queue polling and structural unpacking for trade events."""
    broker_queue: Queue = Queue()
    bridge_mock = MagicMock(spec=BacktraderBridge)
    bridge_mock.get_broker_queue.return_value = broker_queue

    adapter = BacktraderBrokerAdapter(bridge=bridge_mock)

    assert adapter.has_pending_events() is False

    # Pre-populate the sequence mapping to satisfy the strict dict key lookup
    adapter._trade_id_to_group_mapping[42] = 'AEGIS-101'

    # Mock an incoming trade event with its nested order history mapping
    mock_order = MagicMock()
    mock_order.client_order_id = 'AEGIS-101-SL'

    mock_trade = MagicMock()
    mock_trade.ref = 202
    mock_trade.tradeid = 42
    mock_trade.isopen = True
    mock_trade.pnl.__float__.return_value = 50.0
    mock_trade.commission.__float__.return_value = 1.0
    mock_trade.orders = [mock_order]

    mock_data = MagicMock()
    mock_data._name = 'EURUSD'
    mock_trade.data = mock_data

    broker_queue.put((EventType.TRADE_NOTIFICATION, mock_trade))
    assert adapter.has_pending_events() is True

    event = adapter.poll_event()
    assert isinstance(event, BrokerEvent)
    assert event.event_type == EventType.TRADE_NOTIFICATION

    # Updated to validate explicit object attribute accessors
    assert isinstance(event.payload, TradeReceipt)
    assert event.payload.broker_trade_id == '202'
    assert event.payload.group_id == 'AEGIS-101'
    assert event.payload.realized_pnl == Decimal('50.0')
    assert adapter.has_pending_events() is False

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
    start_tradeid = adapter._next_trade_id

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
        data=mock_data,
        size=1.5,
        exectype=bt.Order.Market,
        valid=None,
        transmit=True,
        client_order_id='AEGIS-MKT',
        tradeid=start_tradeid,
    )

# -----------------------------------------------------------------------------

def test_backtrader_broker_adapter_order_clearing_parsing() -> None:
    """Verifies infrastructure order state transformations and decimal conversions."""
    bridge_mock = MagicMock(spec=BacktraderBridge)
    adapter = BacktraderBrokerAdapter(bridge=bridge_mock)

    # 1. Test standard filled scenario with bracket suffix and structural mappings
    mock_order_filled = MagicMock()
    mock_order_filled.ref = 42
    mock_order_filled.status = bt.Order.Completed
    mock_order_filled.info = { 'client_order_id': 'AEGIS-101-SL' }

    # Secure the nested executed attributes with explicit conversion values
    mock_order_filled.executed = MagicMock()
    mock_order_filled.executed.size.__float__.return_value = 100.0
    mock_order_filled.executed.price.__float__.return_value = 1.1250

    event_filled = adapter._translate_to_broker_event(
        EventType.ORDER_NOTIFICATION, mock_order_filled
    )

    assert event_filled.event_type == EventType.ORDER_NOTIFICATION
    assert isinstance(event_filled.payload, OrderReceipt)

    # Assert specific object attribute properties instead of raw dictionaries
    assert event_filled.payload.average_execution_price == Decimal('1.1250')
    assert event_filled.payload.broker_order_id == '42'
    assert event_filled.payload.client_order_id == 'AEGIS-101-SL'
    assert event_filled.payload.executed_quantity == Decimal('100.0')
    assert event_filled.payload.group_id == 'AEGIS-101'
    assert event_filled.payload.reject_reason is None
    assert event_filled.payload.state == OrderState.FILLED

# -----------------------------------------------------------------------------

def test_backtrader_broker_adapter_position_ledger_parsing() -> None:
    """Verifies that get_position_ledger correctly decodes and converts backtrader positions."""
    class DummyDataFeed(bt.feed.DataBase):
        """Minimalistic concrete data feed for structural alignment."""
        # Standard Backtrader parameters infrastructure declaration
        params = (('name', ''),)

        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            # Backtrader assigns params values to self.p or self.params automatically
            self._name = self.p.name

    class DummyStrategy(bt.Strategy):
        """Minimalistic concrete strategy container mapping active positions."""
        def __init__(self) -> None:
            super().__init__()

    # 1. Setup Cerebro to instantiate an authentic strategy legally
    cerebro = bt.Cerebro()
    cerebro.addstrategy(DummyStrategy)

    # 2. Inject raw named data feeds into Cerebro
    data_eurusd = DummyDataFeed(name="EURUSD")
    data_gbpusd = DummyDataFeed(name="GBPUSD")
    data_flat = DummyDataFeed(name="USDJPY")

    cerebro.adddata(data_eurusd)
    cerebro.adddata(data_gbpusd)
    cerebro.adddata(data_flat)

    # Run cerebro minimalistically to extract the fully initialized strategy object
    strategies = cerebro.run()
    strategy = strategies[0]

    # 3. Setup the framework synchronization bridge and adapter
    bridge = BacktraderBridge()
    adapter = BacktraderBrokerAdapter(bridge=bridge)

    # 4. Forge real Backtrader position instances
    position_long = bt.Position()
    position_long.size = 100000
    position_long.price = 1.08500

    position_short = bt.Position()
    position_short.size = -50000
    position_short.price = 1.27400

    position_flat = bt.Position()
    position_flat.size = 0
    position_flat.price = 0.0

    # 5. Bypass the strategy read-only property barrier by writing directly
    #    into Backtrader's underlying broker position mapping container.
    strategy.broker.positions = {
        data_eurusd: position_long,
        data_gbpusd: position_short,
        data_flat: position_flat,
    }
    bridge.bind_strategy(strategy)

    # 6. Execute the ledger parsing extraction
    ledger = adapter._get_position_ledger_snapshot()

    # 7. Assertions verifying mathematical and directional translations
    assert isinstance(ledger, PositionLedgerSnapshot)
    assert len(ledger.records) == 2  # USDJPY (flat) must be filtered out natively

    # Validate LONG position extraction under prefix constraints
    position_aegis_long = ledger.records["EURUSD"]
    assert position_aegis_long.symbol == "EURUSD"
    assert position_aegis_long.ticket_id == "BACKTRADER-EURUSD"
    assert position_aegis_long.side == PositionSide.LONG
    assert position_aegis_long.quantity == Decimal("100000")
    assert position_aegis_long.entry_price == Decimal("1.085")

    # Validate SHORT position extraction under absolute volume constraints
    position_aegis_short = ledger.records["GBPUSD"]
    assert position_aegis_short.symbol == "GBPUSD"
    assert position_aegis_short.ticket_id == "BACKTRADER-GBPUSD"
    assert position_aegis_short.side == PositionSide.SHORT
    assert position_aegis_short.quantity == Decimal("50000")  # Magnitude is absolute
    assert position_aegis_short.entry_price == Decimal("1.274")

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
    start_tradeid = adapter._next_trade_id

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
        data=mock_data,
        size=2.5,
        exectype=bt.Order.Market,
        valid=None,
        transmit=False,
        client_order_id='AEGIS-SELL-BRK',
        tradeid=start_tradeid,
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
            client_order_id='AEGIS-SELL-BRK-SL',
            tradeid=start_tradeid,
        ),
        call(
            data=mock_data,
            size=2.5,
            exectype=bt.Order.Limit,
            price=1.1150,
            valid=None,
            parent=mock_parent_order,
            transmit=True,
            client_order_id='AEGIS-SELL-BRK-TP',
            tradeid=start_tradeid,
        )
    ]
    mock_strategy.buy.assert_has_calls(expected_child_calls, any_order=False)

# -----------------------------------------------------------------------------

def test_backtrader_broker_adapter_trade_clearing_parsing() -> None:
    """Verifies infrastructure trade notification clearing and asset mappings."""
    bridge_mock = MagicMock(spec=BacktraderBridge)
    adapter = BacktraderBrokerAdapter(bridge=bridge_mock)

    # 1. Bind an explicit tracking sequence mapping to satisfy the dictionary lookup
    adapter._trade_id_to_group_mapping[42] = 'AEGIS-202'

    # 2. Mock a native closed trade lifecycle notification instance
    mock_trade = MagicMock()
    mock_trade.ref = 88
    mock_trade.tradeid = 42
    mock_trade.isopen = False
    mock_trade.pnl.__float__.return_value = 250.50
    mock_trade.commission.__float__.return_value = 2.50

    mock_data = MagicMock()
    mock_data._name = 'GBPUSD'
    mock_trade.data = mock_data

    event = adapter._translate_to_broker_event(
        EventType.TRADE_NOTIFICATION, mock_trade
    )

    # 3. Assert correct mapping transformation towards the domain contract layout
    assert event.event_type == EventType.TRADE_NOTIFICATION
    assert isinstance(event.payload, TradeReceipt)
    assert event.payload.broker_trade_id == '88'
    assert event.payload.commission == Decimal('2.5')
    assert event.payload.group_id == 'AEGIS-202'
    assert event.payload.is_open is False
    assert event.payload.realized_pnl == Decimal('250.5')
    assert event.payload.symbol == 'GBPUSD'

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

# -----------------------------------------------------------------------------

def test_backtrader_broker_adapter_translation_extraction_fallback_bug() -> None:
    """Demonstrates the empty group_id bug when client_order_id resides in info."""
    class StubBacktraderExecutionRecord:
        """Manual deterministic structure replicating a raw Backtrader executed block."""
        def __init__(self) -> None:
            self.size: float = 0.1
            self.price: float = 1.112

    class StubBacktraderOrder:
        """Manual rigid stub mimicking a raw Backtrader Order payload without metaclasses."""
        def __init__(self) -> None:
            self.status: int = 1  # Submitted state
            self.ref: int = 1
            self.executed = StubBacktraderExecutionRecord()
            # Mirroring the real runtime metadata dictionary structure
            self.info = {'client_order_id': 'AEGIS-EXPECTED-GROUP-ID'}

    bridge_mock = MagicMock()
    adapter = BacktraderBrokerAdapter(bridge=bridge_mock)

    # Simulate an authentic Backtrader order structure
    raw_order = StubBacktraderOrder()

    # Invoke the translation boundary
    event = adapter._translate_to_broker_event(
        event_type=EventType.ORDER_NOTIFICATION,
        raw_data=raw_order,
    )

    # Test that we extract the id from the `.info` instead of the raw order.
    receipt = event.payload
    assert receipt.group_id == 'AEGIS-EXPECTED-GROUP-ID'
    assert receipt.client_order_id == 'AEGIS-EXPECTED-GROUP-ID'

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
