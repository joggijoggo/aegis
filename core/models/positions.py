"""Aegis Framework - Position Domain Model.

Defines the core immutable data structures representing active market risk exposures.
"""

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from core.models.enums import PositionSide

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

@dataclass(frozen=True)
class Position:
    """Active financial exposure open on a specific market instrument.

    Attributes:
        symbol: Financial instrument market identifier (e.g., 'EURUSD').
        ticket_id: Unique broker transaction tracking key (e.g., 'dealId' or trade reference).
        side: Exposure direction (PositionSide.LONG or PositionSide.SHORT).
        quantity: Strictly positive net trade volume.
        entry_price: Volume-weighted average entry price.
    """
    symbol: str
    ticket_id: str
    side: PositionSide
    quantity: Decimal
    entry_price: Decimal

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

@dataclass(frozen=True)
class PositionLedger:
    """Immutable registry of active market exposures.

    Attributes:
        records: Read-only mapping of open positions indexed by their unique ticket_id.
    """
    records: Mapping[str, Position]

    def __post_init__(self) -> None:
        """Enforces a read-only proxy view over the records dictionary."""
        object.__setattr__(self, 'records', MappingProxyType(dict(self.records)))

# -----------------------------------------------------------------------------

    def get_positions_by_symbol(self, symbol: str) -> list[Position]:
        """Filters and retrieves all active positions allocated to a specific asset.

        Args:
            symbol: Financial instrument market identifier.

        Returns:
            Sequence of active positions open for the requested asset.
        """
        return [p for p in self.records.values() if p.symbol == symbol]

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
