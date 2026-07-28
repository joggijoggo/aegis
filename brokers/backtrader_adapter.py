"""Aegis Framework - Backtrader Broker Adapter Layer.

Implements the outbound port adapter routing absolute bracket orders.
"""

from typing import Any

from brokers.base_broker import AbstractBrokerBridge
from core.models import InstrumentSpecification
from core.models import OrderType
from core.models import TransactionSide

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class BacktraderBrokerAdapter(AbstractBrokerBridge):
    """Outbound adapter connecting Aegis strategies to Backtrader engines."""

# -----------------------------------------------------------------------------

    def __init__(self, bt_strategy: Any, instrument_specs: dict[str, InstrumentSpecification]):
        """Initializes the adapter anchored to an active Backtrader strategy.

        Args:
            bt_strategy (Any): Active instance of a bt.Strategy object.
            instrument_specs (dict[str, InstrumentSpecification]): Enforced parameters.
        """
        self.strategy = bt_strategy
        self._instrument_specs = instrument_specs

# -----------------------------------------------------------------------------

    def place_order(
        self,
        symbol: str,
        side: TransactionSide,
        order_type: OrderType,
        volume_lots: float,
        stop_loss_price: float,
        take_profit_price: float
    ) -> dict[str, Any]:
        """Routes an order request directly to Backtrader using absolute prices.

        Args:
            symbol (str): Target currency pair tracking identifier.
            side (TransactionSide): Enforced transaction direction enum.
            order_type (OrderType): Enforced execution constraint type enum.
            volume_lots (float): Lot size exposure allocation.
            stop_loss_price (float): Absolute protective stop execution level.
            take_profit_price (float): Absolute target limit execution level.

        Returns:
            dict[str, Any]: Standardized execution receipt parameters.
        """
        entry_price = self.strategy.data.close
        spec = self.get_instrument_specification(symbol)
        size_units = int(volume_lots * spec.lot_size)

        if side == TransactionSide.LONG:
            self.strategy.buy_bracket(
                price=entry_price,
                stopprice=stop_loss_price,
                limitprice=take_profit_price,
                size=size_units
            )
        else:
            self.strategy.sell_bracket(
                price=entry_price,
                stopprice=stop_loss_price,
                limitprice=take_profit_price,
                size=size_units
            )

        return {
            "status": "SUBMITTED",
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "volume_lots": volume_lots
        }

# -----------------------------------------------------------------------------

    def get_portfolio_snapshot(self) -> dict[str, Any]:
        """Fetches dynamic financial balances directly from Backtrader broker.

        Returns:
            dict[str, Any]: Structure mapping cash, equity, and active trades.
        """
        return {
            "balance": float(self.strategy.broker.get_cash()),
            "equity": float(self.strategy.broker.get_value())
        }

# -----------------------------------------------------------------------------

    def get_instrument_specification(self, symbol: str) -> InstrumentSpecification:
        """Fetches contract specifications from the local backtest registry.

        Args:
            symbol (str): Target financial asset symbol tracking identifier.

        Returns:
            InstrumentSpecification: Typed immutable contract specifications.

        Raises:
            ValueError: If the target asset symbol is not registered.
        """
        if symbol not in self._instrument_specs:
            raise ValueError(
                f"Asset identity '{symbol}' is missing from instrument registry."
            )
        return self._instrument_specs[symbol]

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
