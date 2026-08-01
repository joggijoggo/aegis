"""Aegis Framework - Core Broker Event Record.

Defines the transactional wrapper used for asynchronous notifications.
"""

from dataclasses import dataclass
from typing import Any

from core.models.enums import EventType

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

@dataclass(frozen=True)
class BrokerEvent:
    """Immutable record capturing broker notifications."""
    event_type: EventType
    payload: Any

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
