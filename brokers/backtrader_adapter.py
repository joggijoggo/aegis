"""Aegis Framework - Backtrader Broker Adapter Layer.

Implements the outbound port adapter translating pips metrics to absolute prices.
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
        stop_loss_pips: float | None = None,
        take_profit_pips: float | None = None
    ) -> dict[str, Any]:
        """Routes an order request directly to Backtrader matching bracket engines.

        Args:
            symbol (str): Target currency pair tracking identifier.
            side (TransactionSide): Enforced transaction direction enum.
            order_type (OrderType): Enforced execution constraint type enum.
            volume_lots (float): Lot size exposure allocation.
            stop_loss_pips (float | None): Optional protective stop distance.
            take_profit_pips (float | None): Optional target limit distance.

        Returns:
            dict[str, Any]: Standardized execution receipt parameters.

        Raises:
            NotImplementedError: If any bracket protection parameter is missing.
            ValueError: If the target asset symbol is not registered.
        """
        if stop_loss_pips is None or take_profit_pips is None:
            raise NotImplementedError(
                "Aegis Backtrader adapter requires both stop_loss_pips and "
                "take_profit_pips parameters to enforce strict bracket routing."
            )

        if symbol not in self._instrument_specs:
            raise ValueError(
                f"Asset identity '{symbol}' is missing from instrument registry."
            )

        # Secure attribute extraction leveraging static dataclass dot notation
        instrument_spec = self._instrument_specs[symbol]
        pip_size = instrument_spec.pip_size
        size_units = int(volume_lots * instrument_spec.lot_size)

        entry_price = float(self.strategy.data.close)

        if side == TransactionSide.LONG:
            stop_price = entry_price - (stop_loss_pips * pip_size)
            limit_price = entry_price + (take_profit_pips * pip_size)
            self.strategy.buy_bracket(
                price=entry_price,
                stopprice=stop_price,
                limitprice=limit_price,
                size=size_units
            )
        else:
            stop_price = entry_price + (stop_loss_pips * pip_size)
            limit_price = entry_price - (take_profit_pips * pip_size)
            self.strategy.sell_bracket(
                price=entry_price,
                stopprice=stop_price,
                limitprice=limit_price,
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

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
