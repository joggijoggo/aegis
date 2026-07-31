"""Aegis Framework - Shared Pytest Environment Fixtures."""

from decimal import Decimal
import pytest

from core.contract_registry import ContractRegistry
from core.currency_converter import CurrencyConverter
from core.position_sizer import PositionSizer
from tests.testutils.constants import DEFAULT_SYMBOL
from tests.testutils.factories import create_contract_specification_factory

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

@pytest.fixture
def contract_registry() -> ContractRegistry:
    """Pre-populated contract specification registry."""
    default_spec = create_contract_specification_factory()
    return ContractRegistry(specifications={DEFAULT_SYMBOL: default_spec})

# -----------------------------------------------------------------------------

@pytest.fixture
def currency_converter() -> CurrencyConverter:
    """Pre-populated currency converter locked to a unit exchange rate."""
    converter = CurrencyConverter()
    converter.update_rate(pair='EURUSD', rate=Decimal('1.00'))
    converter.update_rate(pair='USDEUR', rate=Decimal('1.00'))
    return converter

# -----------------------------------------------------------------------------

@pytest.fixture
def position_sizer(currency_converter) -> PositionSizer:  # pylint: disable=redefined-outer-name
    """Configured position sizer execution service."""
    return PositionSizer(currency_converter=currency_converter)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
