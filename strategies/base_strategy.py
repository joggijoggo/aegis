"""Aegis Framework - Core Strategy Lifecycle Layer.

Defines the abstract base class enforcing execution loops and warm-up anchors.
"""

from abc import ABC
from abc import abstractmethod
from typing import Any

from brokers.base_broker import AbstractBrokerBridge
from core.models import InstrumentSpecification
from core.models import MarketPricePoint
from core.models import OrderType
from core.models import TransactionSide

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class AbstractStrategy(ABC):
    """Base template enforcing technical data loading and order routing loops."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        broker_bridge: AbstractBrokerBridge,
        instrument_specs: dict[str, InstrumentSpecification],
        warm_up_bars: int = 200
    ):
        """Initializes the structural lifecycle tracker and asset parameters mapping.

        Args:
            broker_bridge (AbstractBrokerBridge): Connected execution gateway node.
            instrument_specs (dict): Mapping of active asset parameters.
            warm_up_bars (int): Minimal history length required to clear lookups.
        """
        self.broker = broker_bridge
        self.instrument_specs = instrument_specs
        self.warm_up_bars = warm_up_bars
        self.is_warmed_up = False

# -----------------------------------------------------------------------------

    def on_bar_close(
        self,
        asset: str,
        price_snapshot: MarketPricePoint,
        historical_closes: list[float]
    ) -> None:
        """Triggers operational evaluation cycles at terminal interval boundaries.

        Args:
            asset (str): Target currency pair symbol identity.
            price_snapshot (MarketPricePoint): Frozen immutable pricing bucket.
            historical_closes (list[float]): Available timeline collection space.
        """
        if len(historical_closes) < self.warm_up_bars:
            self.is_warmed_up = False
            return

        self.is_warmed_up = True
        self._on_bar_close(asset, price_snapshot, historical_closes)

# -----------------------------------------------------------------------------

    def place_bracket_order(
        self,
        symbol: str,
        side: TransactionSide,
        order_type: OrderType,
        volume_lots: float,
        current_price: float,
        stop_loss_pips: float,
        take_profit_pips: float
    ) -> dict[str, Any]:
        """Translates relative pips boundaries into absolute prices before routing.

        Args:
            symbol (str): Target asset tracking identifier.
            side (TransactionSide): Enforced execution direction enum.
            order_type (OrderType): Enforced execution constraint type enum.
            volume_lots (float): Lot size exposure allocation.
            current_price (float): Active market baseline execution price.
            stop_loss_pips (float): Protective stop distance in pips.
            take_profit_pips (float): Target limit distance in pips.

        Returns:
            dict[str, Any]: Standardized execution receipt parameters.

        Raises:
            ValueError: If the target asset symbol is not registered.
        """
        if symbol not in self.instrument_specs:
            raise ValueError(
                f"Asset identity '{symbol}' is missing from instrument registry."
            )

        spec = self.instrument_specs[symbol]

        if side == TransactionSide.LONG:
            stop_price = current_price - (stop_loss_pips * spec.pip_size)
            limit_price = current_price + (take_profit_pips * spec.pip_size)
        else:
            stop_price = current_price + (stop_loss_pips * spec.pip_size)
            limit_price = current_price - (take_profit_pips * spec.pip_size)

        return self.broker.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            volume_lots=volume_lots,
            stop_loss_price=stop_price,
            take_profit_price=limit_price
        )

# -----------------------------------------------------------------------------

    @abstractmethod
    def _on_bar_close(
        self,
        asset: str,
        price_snapshot: MarketPricePoint,
        historical_closes: list[float]
    ) -> None:
        """Core internal processing loop to be implemented by child strategies."""
        pass

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
