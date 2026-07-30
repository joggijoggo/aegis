"""Aegis Framework - Trading Bots Testing Mocks.

Provides reusable stateless trading bot mocks for decoupled unit testing.
"""

from decimal import Decimal

from bots.base_bot import BaseBot
from core.models import (
    ExposureIntent,
    MarketContext,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class DummyBot(BaseBot):
    """Compliant stateless bot implementation for structural testing."""

    @property
    def warm_up_period(self) -> int:
        """Gets the configured historical window duration requirements."""
        return 14

    def evaluate(
        self,
        market_context: MarketContext,
        historical_values: list[float],
    ) -> ExposureIntent:
        """Evaluates incoming streaming contexts to yield static exposures."""
        return ExposureIntent(alpha_direction=Decimal("1.0"))

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
