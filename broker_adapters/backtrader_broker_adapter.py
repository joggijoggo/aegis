"""Aegis Framework - Backtrader Broker Adapter.

Provides the infrastructure adapter to interface with the Backtrader broker component.
"""

from decimal import Decimal
from typing import (
    Any,
    Tuple,
)

import backtrader as bt

from broker_adapters.backtrader_bridge import BacktraderBridge
from broker_adapters.base_broker_adapter import BaseBrokerAdapter
from core.exceptions import AegisError
from core.models import (
    AccountSnapshot,
    BrokerEvent,
    BrokerSnapshot,
    EventType,
    Order,
    OrderReceipt,
    OrderSide,
    OrderState,
    OrderType,
    Position,
    PositionLedgerSnapshot,
    PositionSide,
    TimeInForce,
    TradeReceipt,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class AssetSymbolNotFoundError(AegisError):
    """The requested financial asset symbol is not loaded in the Cerebro environment."""

# -----------------------------------------------------------------------------

class BrokerConfigurationError(AegisError):
    """The underlying broker infrastructure parameters or commission schemes are misconfigured."""

# -----------------------------------------------------------------------------

class InvalidOrderQuantityError(AegisError):
    """Execution order volume is zero or negative at the adapter boundary."""

# -----------------------------------------------------------------------------

class InvalidProtectionPriceError(AegisError):
    """The provided stop loss or take profit price trigger is negative or zero."""

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class BacktraderBrokerAdapter(BaseBrokerAdapter):
    """Broker adapter implementing the core transactional interface for Backtrader.

    Manages order routing and account synchronization through the central bridge.
    """

# -----------------------------------------------------------------------------

    def __init__(self, bridge: BacktraderBridge) -> None:
        """Initializes the broker adapter and hooks the synchronization reference.

        Args:
            bridge: The central synchronization bridge.
        """
        self._bridge = bridge
        self._broker_queue = bridge.get_broker_queue()
        self._next_trade_id: int = 1 # Starts at 1 to avoid None clashing.
        self._trade_id_to_group_mapping: dict[int, str] = {}

# -----------------------------------------------------------------------------

    def _compute_portfolio_metrics(self, strategy: bt.Strategy) -> Tuple[Decimal, Decimal]:
        """Iterates over active positions to extract true locked margin and spot acquisition costs.

        Strictly aligned with the behavioral overrides of Backtrader v1.9.78.123.

        Args:
            strategy: The active runtime Backtrader strategy instance.

        Returns:
            A tuple containing the total locked margin and total spot acquisition cost.
        """
        total_locked_margin = Decimal("0.0")
        total_spot_acquisition_cost = Decimal("0.0")

        # Dynamically retrieve the underlying broker engine from the active strategy instance
        broker: bt.Broker = strategy.broker

        for data, position in strategy.positions.items():
            if position.size == 0:
                continue

            comminfo = broker.getcommissioninfo(data)
            is_stocklike = getattr(comminfo, '_stocklike', False) or getattr(comminfo.p, 'stocklike', False)

            # Law 4: Leverage collateral requirement remains anchored to historical entry cost level
            margin_per_unit = comminfo.get_margin(position.price)

            # String-based decimal transformation pipeline to eradicate mantissa drift
            abs_size = Decimal(str(abs(float(position.size))))
            entry_price = Decimal(str(position.price))

            # Regime 1: Authentic Future contract (stocklike=False)
            if not is_stocklike:
                if margin_per_unit is not None:
                    total_locked_margin += abs_size * Decimal(str(margin_per_unit))

            # Regime 4: Authentic Forex Gearing Leverage (stocklike=True + active automargin or leverage > 1)
            elif getattr(comminfo.p, 'automargin', False) or getattr(comminfo.p, 'leverage', 1.0) > 1.0:
                if margin_per_unit is not None:
                    total_locked_margin += abs_size * Decimal(str(margin_per_unit))

            # Regime 2 & 3: Spot Stock Cash OR Forex Fixed Margin (Overridden into spot cash mechanics)
            else:
                # Law 3: stocklike=True silently nullifies margin params, enforcing full cash depletion
                total_spot_acquisition_cost += abs_size * entry_price

        return total_locked_margin, total_spot_acquisition_cost

# -----------------------------------------------------------------------------

    def _get_account_snapshot(self) -> AccountSnapshot:
        """Returns the current financial state of the account.

        Reconstructs the true portfolio core balance by resolving the multi-asset
        invariant equation matrix.

        Returns:
            The normalized, decimal-validated AccountSnapshot domain record.
        """
        strategy: bt.Strategy = self._bridge.strategy
        broker: bt.Broker = strategy.broker

        # Law 1: Backtrader's cash ledger represents strictly the residual available free margin
        raw_balance = float(broker.get_cash())
        raw_equity = float(broker.get_value())

        available_margin = Decimal(str(raw_balance))
        equity = Decimal(str(raw_equity))

        # Specialized SRP routine invocation tracking active contract matrix boundaries
        locked_margin, spot_acquisition_cost = self._compute_portfolio_metrics(strategy=strategy)

        # Resolution of the Invariant Universal Accounting Equation Matrix
        balance = available_margin + locked_margin + spot_acquisition_cost

        return AccountSnapshot(
            currency="USD",
            balance=balance,
            equity=equity,
            available_margin=available_margin,
        )

# -----------------------------------------------------------------------------

    def _get_position_ledger_snapshot(self) -> PositionLedgerSnapshot:
        """Retrieves the immutable ledger of all currently active market exposures from Backtrader.

        Returns:
            PositionLedgerSnapshot instance containing open positions indexed by ticket_id.
        """
        strategy = self._bridge.strategy
        active_records: dict[str, Position] = {}

        # ---------------------------------------------------------------------
        # MICROSTRUCTURAL DESIGN NOTE:
        # Theoretically, Backtrader's native broker ('bt.brokers.BackBroker')
        # only supports strict 'Netting' semantics. It executes algebraic fusion
        # on trade sizes per data feed, making the simultaneous coexistence of
        # separate LONG and SHORT positions on the exact same feed impossible.
        #
        # POTENTIAL WORKAROUNDS FOR HEDGING STRATEGIES:
        # 1. Data Feed Duplication: Inject the same market data multiple times
        #    into Cerebro under unique names (e.g., 'EURUSD_1', 'EURUSD_2').
        #    Backtrader treats them as distinct assets, allocating isolated
        #    'bt.Position' states to each, which this ledger natively captures
        #    as unique 'ticket_id' keys matching the feed names.
        # 2. Custom Broker Extension: Override the core broker by subclassing
        #    'bt.BrokerBase' to substitute the data-mapped dictionary with an
        #    open ticket collection ledger structure.
        # ---------------------------------------------------------------------
        for data, position in strategy.positions.items():
            if position.size == 0:
                continue

            symbol = str(data._name)

            # Map math polarity to core domain execution directions
            if position.size > 0:
                side = PositionSide.LONG
            else:
                side = PositionSide.SHORT

            # Strict type mutation pipeline: float -> str -> Decimal
            quantity = Decimal(str(abs(float(position.size))))
            entry_price = Decimal(str(float(position.price)))

            # In standard netting configurations, ticket_id mirrors the asset symbol
            active_records[symbol] = Position(
                symbol=symbol,
                ticket_id=f'BACKTRADER-{symbol}',
                side=side,
                quantity=quantity,
                entry_price=entry_price,
            )

        return PositionLedgerSnapshot(records=active_records)

# -----------------------------------------------------------------------------

    def _parse_order_status(self, raw_status: int) -> OrderState:
        """Maps Backtrader infrastructure order statuses to core domain enums.

        Args:
            raw_status: Integer representation of Backtrader order states.

        Returns:
            The corresponding core OrderState enumeration value.
        """
        mapping = {
            bt.Order.Created: OrderState.PENDING,
            bt.Order.Submitted: OrderState.PENDING,
            bt.Order.Accepted: OrderState.PENDING,
            bt.Order.Partial: OrderState.PARTIALLY_FILLED,
            bt.Order.Completed: OrderState.FILLED,
            bt.Order.Canceled: OrderState.CANCELED,
            bt.Order.Expired: OrderState.CANCELED,
            bt.Order.Margin: OrderState.REJECTED,
            bt.Order.Rejected: OrderState.REJECTED,
        }
        return mapping.get(raw_status, OrderState.REJECTED)

# -----------------------------------------------------------------------------

    def _resolve_data_feed(self, symbol: str) -> bt.feed.DataBase:
        """Finds and returns the explicit Backtrader data feed instance for a given symbol.

        Args:
            symbol: Target financial asset identifier.

        Returns:
            The matched infrastructure data feed instance.

        Raises:
            AssetSymbolNotFoundError: The requested financial symbol is not loaded in Cerebro.
        """
        for data in self._bridge.strategy.datas:
            if data._name == symbol:
                return data

        raise AssetSymbolNotFoundError(
            f"Requested asset symbol '{symbol}' is not available "
            "within the active Cerebro infrastructure environment."
        )

# -----------------------------------------------------------------------------

    def _route_transaction(self, order: Order, data: bt.feed.DataBase, size: float) -> None:
        """Routes explicit execution streams with dynamic parent-child link tracking.

        Args:
            order: The generic domain order specification.
            data: The target infrastructure data feed instance.
            size: The validated float volume.

        Raises:
            BridgeUnboundError: The strategy instance is not bound.
        """
        strategy = self._bridge.strategy
        sl_price = float(order.stop_loss_price) if order.stop_loss_price is not None else None
        tp_price = float(order.take_profit_price) if order.take_profit_price is not None else None

        # Hard enforcement: protect the platform against executing unprotected trades silently
        if sl_price is not None and sl_price <= 0.0:
            raise InvalidProtectionPriceError(
                f"Invalid Stop Loss price: {sl_price}. Protection bounds must be strictly positive."
            )
        if tp_price is not None and tp_price <= 0.0:
            raise InvalidProtectionPriceError(
                f"Invalid Take Profit price: {tp_price}. Protection bounds must be strictly positive."
            )

        if order.side == OrderSide.BUY:
            entry_op = strategy.buy
            child_op = strategy.sell
        else:
            entry_op = strategy.sell
            child_op = strategy.buy

        has_sl = sl_price is not None
        has_tp = tp_price is not None
        has_children = has_sl or has_tp

        # Capture and map the unique sequence anchor for the manual bracket cycle
        current_trade_id = self._next_trade_id
        self._trade_id_to_group_mapping[current_trade_id] = order.client_order_id
        self._next_trade_id += 1

        parent = entry_op(
            data=data,
            size=size,
            exectype=bt.Order.Market,
            valid=None,
            transmit=not has_children,
            client_order_id=order.client_order_id,
            tradeid=current_trade_id,
        )

        if has_sl:
            transmit_sl = not has_tp
            child_op(
                data=data,
                size=size,
                exectype=bt.Order.Stop,
                price=sl_price,
                valid=None,
                parent=parent,
                transmit=transmit_sl,
                client_order_id=f"{order.client_order_id}-SL",
                tradeid=current_trade_id,
            )

        if has_tp:
            child_op(
                data=data,
                size=size,
                exectype=bt.Order.Limit,
                price=tp_price,
                valid=None,
                parent=parent,
                transmit=True,
                client_order_id=f"{order.client_order_id}-TP",
                tradeid=current_trade_id,
            )

# -----------------------------------------------------------------------------

    def _translate_to_broker_event(self, event_type: EventType, raw_data: Any) -> BrokerEvent:
        """Translates raw infrastructure notifications into core domain events.

        Args:
            event_type: The core classification used to route the update.
            raw_data: The raw infrastructure notification instance (bt.Order or bt.Trade).

        Returns:
            The translated broker event record containing validated decimal payloads.
        """
        payload: OrderReceipt | TradeReceipt = {}

        if event_type == EventType.ORDER_NOTIFICATION:
            raw_order: bt.Order = raw_data

            # Preserving the raw id to know exactly which child bracket is hit
            raw_client_id = raw_order.info['client_order_id']

            # Extract and clean group_id from trailing bracket suffixes
            group_id = raw_client_id
            if group_id.endswith('-SL') or group_id.endswith('-TP'):
                group_id = group_id[:-3]

            state = self._parse_order_status(raw_order.status)

            # Tight type mutation pipeline: float -> str -> Decimal
            executed_size = Decimal(str(float(raw_order.executed.size)))
            executed_price = Decimal(str(float(raw_order.executed.price)))

            # Instantiate a real domain record instead of a raw dictionary
            payload = OrderReceipt(
                average_execution_price=executed_price,
                broker_order_id=str(raw_order.ref),
                client_order_id=raw_client_id,
                executed_quantity=executed_size,
                group_id=group_id,
                reject_reason=None,
                state=state,
            )
        elif event_type == EventType.TRADE_NOTIFICATION:
            raw_trade: bt.Trade = raw_data

            # Leverage native dict KeyLookup to fail-fast upon untracked trade elements
            group_id = self._trade_id_to_group_mapping[raw_trade.tradeid]

            # Tight type mutation pipeline: float -> str -> Decimal
            realized_pnl = Decimal(str(float(raw_trade.pnl)))
            commission = Decimal(str(float(raw_trade.commission)))

            # Instantiate a real domain TradeReceipt record instead of a dict
            payload = TradeReceipt(
                broker_trade_id=str(raw_trade.ref),
                commission=commission,
                group_id=group_id,
                is_open=bool(raw_trade.isopen),
                realized_pnl=realized_pnl,
                symbol=str(raw_trade.data._name),
            )

        return BrokerEvent(
            event_type=event_type,
            payload=payload,
        )

# -----------------------------------------------------------------------------

    def get_broker_snapshot(self) -> BrokerSnapshot:
        """Retrieves the unified temporal snapshot of account metrics and market exposures."""
        return BrokerSnapshot(
            account=self._get_account_snapshot(),
            position_ledger=self._get_position_ledger_snapshot(),
        )

# -----------------------------------------------------------------------------

    def has_pending_events(self) -> bool:
        """Indicates whether unread broker events are available."""
        return not self._broker_queue.empty()

# -----------------------------------------------------------------------------

    def poll_event(self) -> BrokerEvent:
        """Returns the next pending broker event.

        Returns:
            The retrieved broker event.
        """
        event_type, raw_data = self._broker_queue.get()
        return self._translate_to_broker_event(event_type, raw_data)

# -----------------------------------------------------------------------------

    def submit_order(self, order: Order) -> None:
        """Submits an execution request to the Backtrader platform.

        Args:
            order: The execution order request containing trade specifications.

        Raises:
            AssetSymbolNotFoundError: The requested financial symbol is not loaded in Cerebro.
            BridgeUnboundError: The strategy instance is not bound.
            InvalidOrderQuantityError: The execution volume is non-positive.
        """
        # print(f'\n{order}\n')

        raw_quantity = float(order.quantity)
        if raw_quantity <= 0.0:
            raise InvalidOrderQuantityError(
                f"Invalid order quantity processed by the adapter: {raw_quantity}. "
                "Execution volume must be strictly positive."
            )

        if order.order_type != OrderType.MARKET:
            raise NotImplementedError('Only MARKET orders are supported.')

        if order.time_in_force != TimeInForce.GTC:
            raise NotImplementedError(
                f"TimeInForce policy '{order.time_in_force}' is not supported due "
                "to microstructure timezone alignment constraints. Use GTC."
            )

        target_data = self._resolve_data_feed(order.symbol)

        # Enforce atomic reentrant protection to block Cerebro from executing
        # cycles or check_submitted routines during bracket chain creation.
        with self._bridge.get_lock():
            self._route_transaction(order, target_data, raw_quantity)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
