"""Aegis Framework - Backtrader Synchronization Bridge.

Orchestrates thread-safe execution synchronization between the core domain engine and Cerebro.
"""

from queue import Queue
from typing import Any

import backtrader as bt

from core.exceptions import AegisError
from core.models.enums import EventType

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class BridgeAlreadyBoundError(AegisError):
    """Bridge strategy re-assignment attempt."""

# -----------------------------------------------------------------------------

class BridgeUnboundError(AegisError):
    """Bridge access before strategy binding completion."""

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class BacktraderBridge:
    """Synchronizes execution timing and dispatches events between Aegis and Backtrader.

    Provides a centralized interface to freeze simulation loops and route market ticks
    or broker notifications into separate queues.
    """

# -----------------------------------------------------------------------------

    def __init__(self) -> None:
        """Initializes the bridge synchronization queues and tracking states."""
        self._outbound_queue: Queue = Queue(maxsize=1)
        self._market_queue: Queue = Queue()
        self._broker_queue: Queue = Queue()
        self._strategy = None
        self._is_completed = False

# -----------------------------------------------------------------------------

    def advance_time(self) -> None:
        """Signals the background execution loop to progress by a single increment."""
        self._outbound_queue.put(None)

# -----------------------------------------------------------------------------

    def bind_strategy(self, strategy: bt.Strategy) -> None:
        """Binds the active Backtrader strategy instance to the bridge.

        Args:
            strategy: The active simulation strategy instance providing execution hooks.

        Raises:
            BridgeAlreadyBoundError: A strategy instance is already bound.
        """
        if self._strategy is not None:
            raise BridgeAlreadyBoundError('A strategy instance is already bound to this bridge.')

        self._strategy = strategy

# -----------------------------------------------------------------------------

    def get_broker_queue(self) -> Queue:
        """Returns the data queue for broker transaction notifications."""
        return self._broker_queue

# -----------------------------------------------------------------------------

    def get_market_queue(self) -> Queue:
        """Returns the data queue for market price updates."""
        return self._market_queue

# -----------------------------------------------------------------------------

    def is_simulation_completed(self) -> bool:
        """Indicates if the background execution cycle is finished."""
        return self._is_completed

# -----------------------------------------------------------------------------

    def stop_simulation(self) -> None:
        """Flags the historical simulation loop as terminated."""
        self._is_completed = True

# -----------------------------------------------------------------------------

    @property
    def strategy(self) -> bt.Strategy:
        """The bound active Backtrader strategy instance.

        Returns:
            The active strategy instance.

        Raises:
            BridgeUnboundError: The strategy instance is not bound.
        """
        if self._strategy is None:
            raise BridgeUnboundError('The strategy instance is not bound to the bridge.')

        return self._strategy

# -----------------------------------------------------------------------------

    def submit_event(self, event_type: EventType, data: Any) -> None:
        """Dispatches external framework updates and coordinates temporal positioning.

        Args:
            event_type: The core classification used to route the update.
            data: The raw infrastructure object under evaluation.
        """
        if event_type == EventType.MARKET_TICK:
            self._market_queue.put(data)
            self._outbound_queue.get()
        else:
            self._broker_queue.put((event_type, data))

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
