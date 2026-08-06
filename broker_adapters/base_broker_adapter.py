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
    BrokerSnapshot,
    Order,
    PositionLedgerSnapshot,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class BaseBrokerAdapter(ABC):
    """Interface for broker interactions."""

# -----------------------------------------------------------------------------

    @abstractmethod
    def _get_account_snapshot(self) -> AccountSnapshot:
        """Gets the current account snapshot.

        Returns:
            The current account snapshot.

        Raises:
            BrokerConnectionError: Broker connection failure.
        """
        pass

# -----------------------------------------------------------------------------

    @abstractmethod
    def _get_position_ledger_snapshot(self) -> PositionLedgerSnapshot:
        """Retrieves the immutable ledger of all currently active market exposures.

        Returns:
            PositionLedgerSnapshot instance containing open positions indexed by ticket_id.
        """
        pass

# -----------------------------------------------------------------------------

    @abstractmethod
    def cancel_order(self, order: Order) -> None:
        """Cancel a working order in the market.

        Args:
            order: The target order to cancel.
        """
        pass

# -----------------------------------------------------------------------------

    @abstractmethod
    def close_position(self, order: Order) -> None:
        """Close the market position associated with the given order.

        Args:
            order: The parent order that initiated the position.
        """
        pass

# -----------------------------------------------------------------------------

    @abstractmethod
    def get_broker_snapshot(self) -> BrokerSnapshot:
        """Retrieves the unified temporal snapshot of account metrics and market exposures.

        Returns:
            A frozen BrokerSnapshot containing account and ledger snapshots.
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
