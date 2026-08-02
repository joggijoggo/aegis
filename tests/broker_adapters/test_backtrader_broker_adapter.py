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
    BrokerConfigurationError,
    InvalidOrderQuantityError,
    InvalidProtectionPriceError,
)
from core.models import (
    AccountSnapshot,
    BrokerEvent,
    EventType,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionLedger,
    PositionSide,
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

    # Inject an empty positions mapping to simulate a portfolio clear of exposure
    mock_strategy.positions = {}
    mock_bridge.strategy = mock_strategy

    adapter = BacktraderBrokerAdapter(bridge=mock_bridge)
    snapshot = adapter.get_account_snapshot()

    assert isinstance(snapshot, AccountSnapshot)
    assert snapshot.currency == 'USD'
    assert snapshot.balance == Decimal('10000.50')
    assert snapshot.equity == Decimal('10500.75')
    assert snapshot.available_margin == Decimal('10000.50')

# -----------------------------------------------------------------------------

def test_backtrader_broker_adapter_account_snapshot_margin_deduction() -> None:
    """Verifies that get_account_snapshot anchors available_margin to cash minus locked margin."""
    # 1. Setup Cerebro with an authentic strategy and a custom commission scheme
    cerebro = bt.Cerebro()

    class DummyStrategy(bt.Strategy):
        """Minimalistic concrete strategy container mapping active positions."""
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)

    cerebro.addstrategy(DummyStrategy)

    class DummyDataFeed(bt.feed.DataBase):
        """Minimalistic concrete data feed for structural alignment."""
        params = (('name', ''),)
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self._name = self.p.name

    data_eurusd = DummyDataFeed(name="EURUSD")
    data_flat = DummyDataFeed(name="USDJPY")

    cerebro.adddata(data_eurusd)
    cerebro.adddata(data_flat)

    # Configure a fixed cash balance on the core broker engine
    cerebro.broker.set_cash(10000.0)

    # Configure a realistic margin requirement rule for our Forex asset
    # To avoid automargin side-effects, we force a flat margin fee of 30.0 units per lot.
    cerebro.broker.setcommission(commission=0.0, margin=30.0, mult=1.0, name="EURUSD")

    strategies = cerebro.run()
    strategy = strategies[0]

    # 2. Setup the framework synchronization components
    bridge = BacktraderBridge()
    adapter = BacktraderBrokerAdapter(bridge=bridge)

    # 3. Forge a real active position of 2 lots (size=2) at a specific execution level
    position_active = bt.Position()
    position_active.size = 2
    position_active.price = 1.08500

    position_flat = bt.Position()
    position_flat.size = 0
    position_flat.price = 0.0

    # Inject the exposure record directly into the broker mapping layer
    strategy.broker.positions = {
        data_eurusd: position_active,
        data_flat: position_flat,
    }
    bridge.bind_strategy(strategy)

    # 4. Execute the account snapshot mapping translation
    snapshot = adapter.get_account_snapshot()

    # 5. Assertions verifying the microstructure tracking rule (Available Margin = Cash - Margin)
    # Total Cash = 10000.0
    # Locked Margin = 2 contracts * 30.0 margin fee per unit (via get_margin) = 60.0
    # Expected Available Margin = 10000.0 - 60.0 = 9940.0
    assert snapshot.currency == "USD"
    assert snapshot.balance == Decimal("10000")
    assert snapshot.equity == Decimal("10000")
    assert snapshot.available_margin == Decimal("9940")

# -----------------------------------------------------------------------------

def test_backtrader_broker_adapter_account_snapshot_unconfigured_margin_raises_error() -> None:
    """Verifies that get_account_snapshot catches unconfigured margin boundaries on futures."""
    # 1. Setup Cerebro with a standard strategy and a raw unconfigured asset stream
    cerebro = bt.Cerebro()

    class DummyStrategy(bt.Strategy):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)

    cerebro.addstrategy(DummyStrategy)

    class DummyDataFeed(bt.feed.DataBase):
        params = (('name', ''),)
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self._name = self.p.name

    data_eurusd = DummyDataFeed(name="EURUSD")
    cerebro.adddata(data_eurusd)

    # We do NOT set commissions or margins here, simulating a configuration omission debt
    cerebro.broker.set_cash(10000.0)

    strategies = cerebro.run()
    strategy = strategies[0]

    # 2. Setup infrastructure synchronization adapters
    bridge = BacktraderBridge()
    adapter = BacktraderBrokerAdapter(bridge=bridge)

    # 3. Forge a real active position to force loop execution pathing
    position_active = bt.Position()
    position_active.size = 1
    position_active.price = 1.08500

    # Inject the exposure record directly into the broker mapping layer
    strategy.broker.positions = {
        data_eurusd: position_active,
    }
    bridge.bind_strategy(strategy)

    # 4. Target Execution Path:
    # BEFORE THE FIX: This will throw TypeError because margin_per_unit is None.
    # AFTER THE FIX: This will throw our custom BrokerConfigurationError.
    with pytest.raises(BrokerConfigurationError) as exc_info:
        adapter.get_account_snapshot()

    # Verify that the custom exception carries clear diagnostic messaging
    assert "Microstructural Misconfiguration Detected" in str(exc_info.value)
    assert "EURUSD" in str(exc_info.value)

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

def test_backtrader_broker_adapter_event_polling_and_fifo_flow() -> None:
    """Verifies end-to-end event queue polling, state checks, and FIFO ordering."""
    broker_queue: Queue = Queue()
    bridge_mock = MagicMock(spec=BacktraderBridge)
    bridge_mock.get_broker_queue.return_value = broker_queue

    adapter = BacktraderBrokerAdapter(bridge=bridge_mock)

    assert adapter.has_pending_events() is False

    # 1. Mock an incoming order event without restrictive specs
    mock_order = MagicMock()
    mock_order.ref = 101
    mock_order.status = bt.Order.Completed
    mock_order.client_order_id = "ORDER-A"
    mock_order.executed = MagicMock()
    mock_order.executed.size.__float__.return_value = 10.0
    mock_order.executed.price.__float__.return_value = 1.2000

    # 2. Mock an incoming trade event without restrictive specs
    mock_trade = MagicMock()
    mock_trade.ref = 202
    mock_trade.isopen = True
    mock_trade.pnl.__float__.return_value = 50.0
    mock_trade.commission.__float__.return_value = 1.0

    mock_data = MagicMock()
    mock_data._name = "EURUSD"
    mock_trade.data = mock_data

    # Push raw items into the queue exactly like BacktraderProxyStrategy would do
    broker_queue.put((EventType.ORDER_NOTIFICATION, mock_order))
    broker_queue.put((EventType.TRADE_NOTIFICATION, mock_trade))

    assert adapter.has_pending_events() is True

    # Poll first event (Order) and verify structural unpacking
    first_event = adapter.poll_event()
    assert isinstance(first_event, BrokerEvent)
    assert first_event.event_type == EventType.ORDER_NOTIFICATION
    assert first_event.payload['broker_order_id'] == "101"
    assert first_event.payload['client_order_id'] == "ORDER-A"
    assert first_event.payload['executed_quantity'] == Decimal("10.0")
    assert adapter.has_pending_events() is True

    # Poll second event (Trade) and verify structural unpacking
    second_event = adapter.poll_event()
    assert second_event.event_type == EventType.TRADE_NOTIFICATION
    assert second_event.payload['broker_trade_id'] == "202"
    assert second_event.payload['realized_pnl'] == Decimal("50.0")

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

def test_backtrader_broker_adapter_order_clearing_parsing() -> None:
    """Verifies infrastructure order state transformations and decimal conversions."""
    bridge_mock = MagicMock(spec=BacktraderBridge)
    adapter = BacktraderBrokerAdapter(bridge=bridge_mock)

    # 1. Test standard filled scenario with bracket suffix and floating-point conversion
    mock_order_filled = MagicMock()
    mock_order_filled.ref = 42
    mock_order_filled.status = bt.Order.Completed
    mock_order_filled.client_order_id = "AEGIS-101-SL"

    # Secure the nested executed attributes with explicit conversion values
    mock_order_filled.executed = MagicMock()
    mock_order_filled.executed.size.__float__.return_value = 100.0
    mock_order_filled.executed.price.__float__.return_value = 1.1250

    event_filled = adapter._translate_to_broker_event(
        EventType.ORDER_NOTIFICATION, mock_order_filled
    )

    assert event_filled.event_type == EventType.ORDER_NOTIFICATION
    assert isinstance(event_filled.payload, dict)
    assert event_filled.payload['broker_order_id'] == "42"
    assert event_filled.payload['client_order_id'] == "AEGIS-101"
    assert event_filled.payload['status'] == OrderStatus.FILLED
    assert event_filled.payload['executed_quantity'] == Decimal("100.0")
    assert event_filled.payload['execution_price'] == Decimal("1.125")

    # 2. Test protective edge case: completely empty/absent client_order_id and margin rejection
    mock_order_rejected = MagicMock()
    mock_order_rejected.ref = 43
    mock_order_rejected.status = bt.Order.Margin
    del mock_order_rejected.client_order_id  # Force fallback on getattr(..., '')

    mock_order_rejected.executed = MagicMock()
    mock_order_rejected.executed.size.__float__.return_value = 0.0
    mock_order_rejected.executed.price.__float__.return_value = 0.0

    event_rejected = adapter._translate_to_broker_event(
        EventType.ORDER_NOTIFICATION, mock_order_rejected
    )

    assert event_rejected.payload['client_order_id'] == ""
    assert event_rejected.payload['status'] == OrderStatus.REJECTED
    assert event_rejected.payload['executed_quantity'] == Decimal("0.0")
    assert event_rejected.payload['execution_price'] == Decimal("0.0")

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
    ledger = adapter.get_position_ledger()

    # 7. Assertions verifying mathematical and directional translations
    assert isinstance(ledger, PositionLedger)
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

def test_backtrader_broker_adapter_trade_clearing_parsing() -> None:
    """Verifies microstructure trade event parsing and floating point containment."""
    bridge_mock = MagicMock(spec=BacktraderBridge)
    adapter = BacktraderBrokerAdapter(bridge=bridge_mock)

    # Remove spec restriction to allow dynamic attributes instantiation
    mock_trade = MagicMock()
    mock_trade.ref = 777
    mock_trade.isopen = False

    # Secure the float casting pipeline on native parameters
    mock_trade.pnl.__float__.return_value = 150.75
    mock_trade.commission.__float__.return_value = 2.50

    # Configure the financial asset symbol string extraction cleanly
    mock_data = MagicMock()
    mock_data._name = "EURUSD"
    mock_trade.data = mock_data

    event_trade = adapter._translate_to_broker_event(
        EventType.TRADE_NOTIFICATION, mock_trade
    )

    assert event_trade.event_type == EventType.TRADE_NOTIFICATION
    assert isinstance(event_trade.payload, dict)
    assert event_trade.payload['broker_trade_id'] == "777"
    assert event_trade.payload['symbol'] == "EURUSD"
    assert event_trade.payload['realized_pnl'] == Decimal("150.75")
    assert event_trade.payload['commission'] == Decimal("2.5")
    assert event_trade.payload['is_open'] is False

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
