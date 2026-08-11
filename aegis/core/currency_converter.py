"""Aegis Framework - Currency Translation Utility.

Manages spot exchange rates to convert monetary amounts between different
currency denominations.
"""

from decimal import Decimal
import logging

from aegis.core.exception import MissingExchangeRateError

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class CurrencyConverter:
    """Converts financial amounts between multiple currency denominations."""

# -----------------------------------------------------------------------------

    def __init__(self):
        """Initializes the converter with an empty tracking memory."""
        self._rates: dict[str, Decimal] = {}

# -----------------------------------------------------------------------------

    def update_rate(self, pair: str, rate: Decimal):
        """Updates or injects a live currency exchange spot rate.

        Args:
            pair: Target currency cross identifier.
            rate: Current exchange rate price valuation.
        """
        self._rates[pair] = rate

# -----------------------------------------------------------------------------

    def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
    ) -> Decimal:
        """Translates a financial amount between two distinct currencies.

        Args:
            amount: Monetary value to translate.
            from_currency: Source currency identifier.
            to_currency: Target currency identifier.
        """
        if from_currency == to_currency:
            return amount

        direct_pair = f'{from_currency}{to_currency}'
        if direct_pair in self._rates:
            return amount * self._rates[direct_pair]

        inverse_pair = f'{to_currency}{from_currency}'
        if inverse_pair in self._rates:
            return amount / self._rates[inverse_pair]

        raise MissingExchangeRateError(
            f'Missing exchange rate translation vector '
            f'for currency cross: {from_currency}/{to_currency}'
        )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
