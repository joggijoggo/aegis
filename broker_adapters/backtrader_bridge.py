"""Aegis Framework - Backtrader Synchronization Bridge.

Orchestrates thread-safe execution synchronization between the core domain engine and Cerebro.
"""

from queue import Queue
import threading
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
        self._market_queue: Queue = Queue()
        self._broker_queue: Queue = Queue()
        self._lock = threading.RLock()  # Reentrant lock guarding concurrent execution boundaries
        self._strategy = None
        self._is_completed = False
        # Barrier to block infra thread until engine is in loop cycle
        self._start_event = threading.Event()

        self._cv = threading.Condition()
        self._ready_to_advance = False

# -----------------------------------------------------------------------------

    def advance_time(self) -> None:
        """Signals the background execution loop to progress by a single increment."""
        with self._cv:
            self._ready_to_advance = True
            self._cv.notify_all()

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

    def get_lock(self) -> threading.RLock:
        """Returns the structural execution synchronization lock for atomic thread isolation.

        Returns:
            The active reentrant thread lock instance.
        """
        return self._lock

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

    def signal_engine_is_ready(self) -> None:
        """Signals that the domain thread (engine) is ready."""
        self._start_event.set()

# -----------------------------------------------------------------------------

    def submit_event(self, event_type: EventType, data: Any) -> None:
        """Dispatches external framework updates and coordinates temporal positioning.

        Args:
            event_type: The core classification used to route the update.
            data: The raw infrastructure object under evaluation.
        """
        if self._is_completed:
            return

        if event_type == EventType.MARKET_TICK:
            # Reset the state variable BEFORE locking or queueing
            with self._cv:
                self._ready_to_advance = False

            # Push to the queue OUTSIDE the lock to prevent re-entrant deadlocks
            self._market_queue.put(data)

            # Block until the engine explicitly signals that time has advanced
            with self._cv:
                while not self._ready_to_advance:
                    self._cv.wait()

            with self._lock:
                pass
        else:
            self._broker_queue.put((event_type, data))

# -----------------------------------------------------------------------------

    def wait_engine_is_ready(self) -> None:
        """Block until the engine thread is ready."""
        self._start_event.wait()

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
