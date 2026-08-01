"""Aegis Framework - Backtrader Broker Adapter.

Provides the infrastructure adapter to interface with the Backtrader broker component.
"""

from decimal import Decimal
from typing import Any

from broker_adapters.backtrader_bridge import BacktraderBridge
from broker_adapters.base_broker_adapter import BaseBrokerAdapter
from core.models import (
    AccountSnapshot,
    BrokerEvent,
    EventType,
    Order,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class BacktraderBrokerAdapter(BaseBrokerAdapter):
    """Broker adapter implementing the core transactional interface for Backtrader.

    Manages order routing and account synchronization through the central bridge.
    """

# -----------------------------------------------------------------------------

    def __init__(self, bridge: BacktraderBridge) -> None:
        """Initializes the broker adapter and hooks the synchronization reference.

        Args:
            bridge: The central synchronization bridge.
        """
        self._bridge = bridge
        self._broker_queue = bridge.get_broker_queue()

# -----------------------------------------------------------------------------

    def _translate_to_broker_event(self, event_type: EventType, raw_data: Any) -> BrokerEvent:
        """Translates raw infrastructure notifications into core domain events.

        Args:
            event_type: The core classification used to route the update.
            raw_data: The raw infrastructure notification instance.

        Returns:
            The translated broker event record.
        """
        # Microstructural translation wrapper placeholder
        return BrokerEvent(
            event_type=event_type,
            payload=raw_data,
        )

# -----------------------------------------------------------------------------

    def get_account_snapshot(self) -> AccountSnapshot:
        """Returns the current financial state of the account.

        Returns:
            The account metrics snapshot.
        """
        strategy = self._bridge.strategy

        raw_balance = float(strategy.broker.get_cash())
        raw_equity = float(strategy.broker.get_value())

        raw_available_margin = raw_equity # TODO: subtract locked margin for open positions

        return AccountSnapshot(
            currency='USD',  # TODO: extract dynamically from environment
            balance=Decimal(str(raw_balance)),
            equity=Decimal(str(raw_equity)),
            available_margin=Decimal(str(raw_available_margin)),
        )

# -----------------------------------------------------------------------------

    def has_pending_events(self) -> bool:
        """Indicates whether unread broker events are available."""
        return not self._broker_queue.empty()

# -----------------------------------------------------------------------------

    def poll_event(self) -> BrokerEvent:
        """Returns the next pending broker event.

        Returns:
            The retrieved broker event.
        """
        event_type, raw_data = self._broker_queue.get()
        return self._translate_to_broker_event(event_type, raw_data)

# -----------------------------------------------------------------------------

    def submit_order(self, order: Order) -> None:
        """Submits an execution request to the Backtrader platform.

        Args:
            order: The order request.
        """
        # Passive placeholder behavior for the baseline DummyBot execution context
        pass

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
