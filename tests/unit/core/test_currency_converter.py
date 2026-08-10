"""Aegis Framework - Currency Converter Unit Tests.

Verifies deterministic monetary conversion behaviors including identity skips,
direct scaling, inverse scaling, and precise exception routing.
"""

from decimal import Decimal

import pytest

from aegis.core.currency_converter import CurrencyConverter
from aegis.core.exception import MissingExchangeRateError

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_converter_executes_direct_conversion_vector() -> None:
    """Validates direct conversion scaling calculations."""
    converter = CurrencyConverter()
    converter.update_rate(pair='EURUSD', rate=Decimal('1.0850'))

    result = converter.convert(
        amount=Decimal('100.00'),
        from_currency='EUR',
        to_currency='USD',
    )

    assert result == Decimal('108.5000')

# -----------------------------------------------------------------------------

def test_converter_executes_inverse_conversion_vector() -> None:
    """Validates inverse conversion division mechanics."""
    converter = CurrencyConverter()
    converter.update_rate(pair='EURUSD', rate=Decimal('1.0850'))

    result = converter.convert(
        amount=Decimal('108.50'),
        from_currency='USD',
        to_currency='EUR',
    )

    assert result == Decimal('100.00')

# -----------------------------------------------------------------------------

def test_converter_raises_missing_exchange_rate_error() -> None:
    """Validates exchange vector missing exception mapping."""
    converter = CurrencyConverter()

    with pytest.raises(MissingExchangeRateError):
        converter.convert(
            amount=Decimal('100.00'),
            from_currency='GBP',
            to_currency='JPY',
        )

# -----------------------------------------------------------------------------

def test_converter_skips_calculation_for_identical_currencies() -> None:
    """Validates short-circuit mapping for matching currency inputs."""
    converter = CurrencyConverter()
    amount = Decimal('100.00')

    result = converter.convert(
        amount=amount,
        from_currency='EUR',
        to_currency='EUR',
    )

    assert result == amount

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
