"""Aegis Framework - Contract Registry Unit Tests.

Verifies the storage, extraction, and exception routing behaviors of the
microstructural contract parameters repository.
"""

import pytest

from aegis.core.contract_registry import ContractRegistry
from aegis.core.exception import ContractNotFoundError
from tests.testutil import (
    DEFAULT_SYMBOL,
    create_contract_specification_factory,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_registry_raises_contract_not_found_error_for_missing_symbol() -> None:
    """Ensures extracting an unregistered symbol triggers a domain error."""
    registry = ContractRegistry(specifications={})

    with pytest.raises(ContractNotFoundError):
        registry.get_specification(symbol='UNKNOWN')

# -----------------------------------------------------------------------------

def test_registry_stores_and_extracts_contract_specification() -> None:
    """Ensures a contract specification can be stored and retrieved by symbol."""
    spec = create_contract_specification_factory()
    registry = ContractRegistry(specifications={DEFAULT_SYMBOL: spec})
    result = registry.get_specification(symbol=DEFAULT_SYMBOL)

    assert result == spec
    assert result.quote_currency == 'USD'
    assert result.contract_multiplier == spec.contract_multiplier

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
