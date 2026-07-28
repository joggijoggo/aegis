"""Aegis Framework - Instrument Registry Model.

Centralizes market contract definitions and enforces fail-fast catalog lookups.
"""

from types import MappingProxyType

from core.models import InstrumentSpecification

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class InstrumentRegistry:
    """Central repository storing immutable asset configurations."""

# -----------------------------------------------------------------------------

    def __init__(self, specifications: dict[str, InstrumentSpecification]):
        """Initializes the registry carrying a snapshot copy of market profiles.

        Args:
            specifications (dict[str, InstrumentSpecification]): Mapping profile.
        """
        self._specifications = MappingProxyType(dict(specifications))

# -----------------------------------------------------------------------------

    def get_specification(self, symbol: str) -> InstrumentSpecification:
        """Retrieves targeted contract metadata or triggers a fail-fast runtime error.

        Args:
            symbol (str): Target trading symbol identifier.

        Returns:
            InstrumentSpecification: Typed contract parameters snapshot.

        Raises:
            ValueError: If the asset target identification is missing or invalid.
        """
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError(
                f"Invalid symbol identity query: '{symbol}'. Must be a non-empty string."
            )

        if symbol not in self._specifications:
            raise ValueError(
                f"Asset '{symbol}' is missing from central instrument registry."
            )

        return self._specifications[symbol]

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
