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
    BrokerEvent,
    Order,
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
    def submit_order(self, order: Order) -> None:
        """Submits the order to the broker..

        Args:
            order: The order request.
        """
        pass

# -----------------------------------------------------------------------------

    @abstractmethod
    def has_pending_events(self) -> bool:
        """Indicates whether unread broker events are available."""
        pass

# -----------------------------------------------------------------------------

    @abstractmethod
    def poll_event(self) -> BrokerEvent:
        """Returns the next pending broker event.

        Returns:
            The retrieved broker event.
        """
        pass

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
