"""Aegis Framework - Backtrader Strategy Inbound Ingestion Bridge.

Connects Backtrader lifecycle event loops directly to Aegis strategy brains.
"""

from typing import Any
from zoneinfo import ZoneInfo

import backtrader as bt

from brokers.backtrader_adapter import BacktraderBrokerAdapter
from core.frictions import DynamicFrictionEngine
from core.models import MarketPricePoint
from core.models import OrderEvent
from core.models import OrderStatus
from core.models import PositionCloseEvent
from core.models import TransactionSide
from core.registry import InstrumentRegistry

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class BacktraderStrategyBridge(bt.Strategy):
    """Inbound orchestration bridge translating timeline ticks to Aegis models."""

# -----------------------------------------------------------------------------

    def __init__(self, aegis_bot: Any, instrument_registry: InstrumentRegistry):
        """Initializes the event broker bridge linking active quantitative nodes.

        Args:
            aegis_bot (Any): Target instance of an Aegis abstract strategy bot.
            instrument_registry (InstrumentRegistry): Central domain repository.
        """
        self.aegis_bot = aegis_bot
        self.instrument_registry = instrument_registry

        # Hot-wire the hexagonal architecture loop by binding production adapter
        self.aegis_bot.broker = BacktraderBrokerAdapter(
            bt_strategy=self,
            instrument_registry=self.instrument_registry,
        )

        target_symbol = self.data._name
        spec = self.instrument_registry.get_specification(target_symbol)

        self.friction_engine = DynamicFrictionEngine(
            base_spread_ticks=spec.base_spread_ticks,
            tick_size=spec.tick_size,
            volatility_factor=spec.volatility_factor,
        )

# -----------------------------------------------------------------------------

    def next(self) -> None:
        """Evaluates ongoing terminal intervals ticks released by Cerebro loops."""
        # 1. Capture exact timeline timestamp parameters from Backtrader line tracking
        current_dt = self.data.datetime.datetime(0).replace(tzinfo=ZoneInfo("UTC"))
        mid_price = self.data.close[0]
        asset_symbol = self.data._name
        current_atr = self.data.atr[0]

        # 2. Simulate standard asset pricing matrix offsets parameters
        market_prices = self.friction_engine.get_market_prices(
            utc_time=current_dt,
            mid_price=mid_price,
            current_atr=current_atr,
        )

        # 3. Dynamic sliding window extraction layer routing for warm-up buffers
        current_buffer_size = len(self)
        historical_closes = self.data.close.get(size=current_buffer_size)

        # 4. Instantiation of unified immutable market models containers snapshot
        price_snapshot = MarketPricePoint(
            timestamp=current_dt,
            mid_price=mid_price,
            bid=market_prices.bid,
            ask=market_prices.ask,
            current_atr=current_atr,
            is_night_tariff=market_prices.is_night_tariff,
        )

        # 5. Route structured parameters packets to the Aegis decision loop
        self.aegis_bot.on_bar_close(
            asset=asset_symbol,
            price_snapshot=price_snapshot,
            historical_closes=historical_closes,
        )

# -----------------------------------------------------------------------------

    def notify_order(self, order: bt.Order) -> None:
        """Intercepts and routes asynchronous carnet order lifecycle changes.

        Args:
            order (bt.Order): Native Backtrader order instance tracking payload.
        """
        if order.status == bt.Order.Completed:
            status_enum = OrderStatus.COMPLETED
        elif order.status in (bt.Order.Rejected, bt.Order.Margin, bt.Order.Canceled):
            status_enum = OrderStatus.REJECTED
        else:
            return

        side_enum = TransactionSide.LONG if order.isbuy() else TransactionSide.SHORT
        event_dt = self.data.datetime.datetime(0)
        order_symbol = order.data._name

        event = OrderEvent(
            order_id=order.ref,
            symbol=order_symbol,
            status=status_enum,
            side=side_enum,
            executed_price=float(order.executed.price) if order.status == bt.Order.Completed else 0.0,
            executed_size=int(order.executed.size),
            timestamp=event_dt,
        )

        self.aegis_bot.order_events.append(event)

# -----------------------------------------------------------------------------

    def notify_trade(self, trade: bt.Trade) -> None:
        """Intercepts finalized trades to extract closed position performance logs.

        Args:
            trade (bt.Trade): Native Backtrader closed position tracking record.
        """
        # 1. Filter out transient open or partial execution intervals states
        if not trade.isclosed:
            return

        # 2. Map Backtrader internal metrics parameters to core domain enums
        side_enum = TransactionSide.LONG if trade.long else TransactionSide.SHORT

        # 3. Extract native temporal and structural ledger properties
        pnl_gross = float(trade.pnl)
        pnl_net = float(trade.pnlcomm)
        commission = float(trade.commission)
        bars_duration = int(trade.barlen)

        # 4. Safely convert Backtrader float timestamps to Python datetime objects
        t_entry = bt.num2date(trade.dtopen)
        t_exit = bt.num2date(trade.dtclose)
        trade_symbol = trade.data._name

        # 5. Construct the unified immutable position closure audit snapshot
        event = PositionCloseEvent(
            symbol=trade_symbol,
            side=side_enum,
            pnl_gross=pnl_gross,
            pnl_net=pnl_net,
            commission=commission,
            bars_duration=bars_duration,
            entry_timestamp=t_entry,
            exit_timestamp=t_exit,
        )

        self.aegis_bot.position_close_events.append(event)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
