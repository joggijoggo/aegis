"""Aegis Framework - Shared Pytest Environment Fixtures."""

import pytest

from core.contract_registry import ContractRegistry
from core.currency_converter import CurrencyConverter
from core.position_sizer import PositionSizer
from tests.testutils.constants import DEFAULT_SYMBOL
from tests.testutils.factories import (
    create_contract_specification_factory,
    create_currency_converter_factory,
    create_position_sizer_factory,
)

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
    """Pre-populated currency converter locked to a unit exchange rate.

    Returns:
        A standardized CurrencyConverter shared fixture instance.
    """
    return create_currency_converter_factory()

# -----------------------------------------------------------------------------

@pytest.fixture
def position_sizer(currency_converter: CurrencyConverter) -> PositionSizer:  # pylint: disable=redefined-outer-name
    """Configured position sizer execution service.

    Args:
        currency_converter: The resolved currency translation service fixture.

    Returns:
        A configured PositionSizer execution service shared fixture instance.
    """
    return create_position_sizer_factory(currency_converter=currency_converter)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
