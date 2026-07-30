"""Aegis Framework - Contract Registry Unit Tests.

Verifies the storage, extraction, and exception routing behaviors of the
microstructural contract parameters repository.
"""

from decimal import Decimal
import pytest

from core.contract_registry import ContractRegistry
from core.exceptions import ContractNotFoundError
from core.models import ContractSpecification

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_registry_stores_and_extracts_contract_specification() -> None:
    """Ensures a contract specification can be stored and retrieved by symbol."""
    spec = ContractSpecification(
        symbol='EURUSD',
        base_spread_ticks=Decimal('2.0'),
        contract_multiplier=Decimal('100000'),
        base_currency='EUR',
        quote_currency='USD',
        contract_step=Decimal('0.01'),
        margin_requirement=Decimal('0.0333'),
        min_contract_size=Decimal('0.1'),
        tick_size=Decimal('0.00001'),
    )

    registry = ContractRegistry(specifications={'EURUSD': spec})
    result = registry.get_specification(symbol='EURUSD')

    assert result == spec
    assert result.quote_currency == 'USD'
    assert result.contract_multiplier == Decimal('100000')

# -----------------------------------------------------------------------------

def test_registry_raises_contract_not_found_error_for_missing_symbol() -> None:
    """Ensures extracting an unregistered symbol triggers a domain error."""
    registry = ContractRegistry(specifications={})

    with pytest.raises(ContractNotFoundError):
        registry.get_specification(symbol='UNKNOWN')

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
