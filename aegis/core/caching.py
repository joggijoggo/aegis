"""Aegis Framework - Internal Memory Caching Structures.

Provides performance-optimized sliding window buffers for historical data.
"""

from collections import deque
import logging

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class HistoricalBuffer:
    """Fixed-size rolling buffer for historical series data."""

# -----------------------------------------------------------------------------

    def __init__(self, max_size: int) -> None:
        """Initializes the buffer with a maximum capacity.

        Args:
            max_size: Maximum number of elements allowed in the buffer.
        """
        if max_size < 0:
            raise ValueError("Buffer maximum size must be greater than or equal to zero.")

        self._buffer: deque[float] = deque(maxlen=max_size)

# -----------------------------------------------------------------------------

    def __len__(self) -> int:
        """Returns the current number of elements stored in the buffer.

        Returns:
            The discrete count of active entries.
        """
        return len(self._buffer)

# -----------------------------------------------------------------------------

    def append(self, value: float) -> None:
        """Appends a new value to the buffer.

        Args:
            value: The numerical value to store.
        """
        self._buffer.append(float(value))

# -----------------------------------------------------------------------------

    def to_list(self) -> list[float]:
        """Converts the buffer to a standard list.

        Returns:
            The ordered list of stored values.
        """
        return list(self._buffer)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
