"""Aegis Framework - Passive Telemetry Ledger Accumulation.

Provides chronological in-memory storage arrays designed to capture and index
heterogeneous domain objects broadcast during live or backtest executions.
"""

from typing import (
    Any,
    Type,
    TypeVar,
)

# -----------------------------------------------------------------------------

T = TypeVar('T')

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class SessionHistory:
    """Instance-based storage repository tracking flat domain records."""

# -----------------------------------------------------------------------------

    def __init__(self) -> None:
        """Initializes an isolated local storage array."""
        self._storage: list[Any] = []

# -----------------------------------------------------------------------------

    def receive(self, record: Any) -> None:
        """Stores an incoming domain record into the local repository.

        Args:
            record: The raw business entity instance to save.
        """
        self._storage.append(record)

# -----------------------------------------------------------------------------

    def get_records(self, record_class: Type[T]) -> list[T]:
        """Retrieves all stored entries matching a specific domain class.

        Args:
            record_class: The expected business model type.

        Returns:
            A list of filtered domain records.
        """
        return [item for item in self._storage if isinstance(item, record_class)]

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
