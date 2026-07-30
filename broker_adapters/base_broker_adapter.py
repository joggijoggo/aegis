"""Aegis Framework - Broker Adapter Foundations.

Defines the core behavioral interface for account metrics retrieval and financial
order execution across external broker gateways.
"""

from abc import (
    ABC,
    abstractmethod,
)

from core.models import (
    AccountSnapshot,
    Order,
    OrderReceipt,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class BaseBrokerAdapter(ABC):
    """Interface for broker interactions."""

# -----------------------------------------------------------------------------

    @abstractmethod
    def get_account_snapshot(self) -> AccountSnapshot:
        """Gets the current account snapshot.

        Returns:
            The current account snapshot.

        Raises:
            BrokerConnectionError: Broker connection failure.
        """
        pass

# -----------------------------------------------------------------------------

    @abstractmethod
    def submit_order(self, order: Order) -> OrderReceipt:
        """Submits the order to the broker.

        Args:
            order: The execution order details.

        Returns:
            The execution order receipt.

        Raises:
            BrokerConnectionError: Broker connection failure.
        """
        pass

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
