"""Aegis Framework - Broker Port Interfacing Layer.

Defines the outbound interface contracts enforcing broker-agnostic order routing.
"""

from abc import ABC
from abc import abstractmethod
from typing import Any

from core.models import InstrumentSpecification
from core.models import OrderType
from core.models import TransactionSide

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class AbstractBrokerBridge(ABC):
    """Structural port enforcing absolute boundary order routing constraints."""

# -----------------------------------------------------------------------------

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: TransactionSide,
        order_type: OrderType,
        volume_lots: float,
        stop_loss_price: float,
        take_profit_price: float
    ) -> dict[str, Any]:
        """Routes transaction payloads using structural absolute prices levels."""
        pass

# -----------------------------------------------------------------------------

    @abstractmethod
    def get_portfolio_snapshot(self) -> dict[str, Any]:
        """Fetches unified financial metrics records parameters from the broker."""
        pass

# -----------------------------------------------------------------------------

    @abstractmethod
    def get_instrument_specification(self, symbol: str) -> InstrumentSpecification:
        """Fetches contract specifications for a specific financial instrument."""
        pass

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
