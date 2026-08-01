"""Aegis Framework - Contract Specification Registry.

Stores and distributes microstructural contract parameters for transaction
sizing and prudential margin verification.
"""

from core.exceptions import ContractNotFoundError
from core.models import ContractSpecification

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class ContractRegistry:
    """Central repository storing structural market exchange contract rules."""

# -----------------------------------------------------------------------------

    def __init__(self, specifications: dict[str, ContractSpecification]):
        """Initializes the registry mapping symbols to their specifications.

        Args:
            specifications: Source structural contract parameters indexed by symbol.
        """
        self._specifications = specifications

# -----------------------------------------------------------------------------

    def get_specification(self, symbol: str) -> ContractSpecification:
        """Extracts the contract rules for a designated financial asset.

        Args:
            symbol: Target financial instrument identifier.
        """
        if symbol not in self._specifications:
            raise ContractNotFoundError(
                'Financial contract specification parameters not found '
                f'for symbol: {symbol}'
            )

        return self._specifications[symbol]

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
