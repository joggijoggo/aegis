"""Aegis Framework - Broker Port Interfacing Layer.

Defines the outbound interface contracts enforcing broker-agnostic order routing.
"""

from abc import (
    ABC,
    abstractmethod,
)

from core.models import (
    InstrumentSpecification,
    OrderReceipt,
    OrderSide,
    OrderType,
    PortfolioSnapshot,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class AbstractBrokerBridge(ABC):
    """Structural port enforcing absolute boundary order routing constraints."""

# -----------------------------------------------------------------------------

    @abstractmethod
    def get_instrument_specification(self, symbol: str) -> InstrumentSpecification:
        """Fetches contract specifications for a specific financial instrument.

        Args:
            symbol: Targeted financial instrument ticker identity.

        Returns:
            Immutable market constants matching the financial instrument contract.
        """
        pass

# -----------------------------------------------------------------------------

    @abstractmethod
    def get_portfolio_snapshot(self) -> PortfolioSnapshot:
        """Fetches unified financial metrics records parameters from the broker.

        Returns:
            Immutable financial snapshot capturing the current ledger state.
        """
        pass

# -----------------------------------------------------------------------------

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        volume_lots: float,
        stop_loss_price: float,
        take_profit_price: float,
    ) -> OrderReceipt:
        """Routes transaction payloads using structural absolute prices levels.

        Args:
            symbol: Target financial instrument symbol tracking identifier.
            side: Physical execution routing action flag (BUY or SELL).
            order_type: Execution type specifying immediate (MARKET) or
                conditional (LIMIT) fulfillment.
            volume_lots: Transaction size expressed in standardized contracts lots.
            stop_loss_price: Absolute trigger price for liquidation protection.
            take_profit_price: Absolute trigger price for profit monetization.

        Returns:
            Immutable receipt acknowledging transaction request transmission.
        """
        pass

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
