"""Aegis Framework - Hexagonal Broker Port Layer.

Defines the core outbound abstract port for broker agnosticism.
"""

from abc import ABC
from abc import abstractmethod
from typing import Any

from core.models import OrderType
from core.models import TransactionSide

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class AbstractBrokerBridge(ABC):
    """Hexagonal outbound port enforcing unified interface for all broker engines."""

# -----------------------------------------------------------------------------

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: TransactionSide,
        order_type: OrderType,
        volume_lots: float,
        stop_loss_pips: float | None = None,
        take_profit_pips: float | None = None
    ) -> dict[str, Any]:
        """Routes an execution contract request to the target matching engine.

        Args:
            symbol (str): Target currency pair tracking identifier.
            side (TransactionSide): Enforced transaction direction enum.
            order_type (OrderType): Enforced execution constraint type enum.
            volume_lots (float): Lot size exposure allocation.
            stop_loss_pips (float | None): Optional protective stop distance.
            take_profit_pips (float | None): Optional target limit distance.

        Returns:
            dict[str, Any]: Standardized execution receipt parameters.
        """
        pass

# -----------------------------------------------------------------------------

    @abstractmethod
    def get_portfolio_snapshot(self) -> dict[str, Any]:
        """Fetches dynamic localized financial balances and open position nodes.

        Returns:
            dict[str, Any]: Structure mapping cash, equity, and active trades.
        """
        pass

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
