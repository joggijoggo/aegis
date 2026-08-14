"""Aegis Framework - Distribution layer for broadcasting framework events."""

from typing import (
    Any,
    Callable,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class TelemetryEmitter:
    """Core domain component enabling decoupled metrics transmission."""

# -----------------------------------------------------------------------------

    def __init__(self) -> None:
        """Initializes the emitter with an empty routing matrix."""
        self._listeners: list[Callable[[Any], None]] = []

# -----------------------------------------------------------------------------

    def register_listener(self, callback: Callable[[Any], None]) -> None:
        """Attaches an external functional data receiver to the broadcast stream.

        Args:
            callback: The functional destination handler triggered upon emission.
        """
        self._listeners.append(callback)

# -----------------------------------------------------------------------------

    def emit(self, record: Any) -> None:
        """Broadcasts an immutable domain record to all attached receivers.

        Args:
            record: The raw domain object under distribution.
        """
        for callback in self._listeners:
            callback(record)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
