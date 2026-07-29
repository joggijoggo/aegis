"""Aegis Framework - Technical Strategies Testing Mocks.

Provides reusable stateless strategy mocks for decoupled unit testing.
"""

from core.models import (
    ExposureIntent,
    MarketContext,
)
from strategies.base_strategy import AbstractStrategy

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class MockAlphaStrategy(AbstractStrategy):
    """Minimal evaluation strategy implementation to verify return bindings."""

    def _evaluate(
        self,
        market_context: MarketContext,
        historical_values: list[float],
    ) -> ExposureIntent:
        """Enforces a static bullish intent return for test validation."""
        return ExposureIntent(alpha_direction=1.0, stop_loss_ticks=20.0)

# -----------------------------------------------------------------------------

class MockAnomalousStrategy(AbstractStrategy):
    """Corrupted strategy implementation to trigger contract boundaries check."""

    def _evaluate(
        self,
        market_context: MarketContext,
        historical_values: list[float],
    ) -> ExposureIntent:
        """Returns an out of bounds conviction to test fail-safe guards."""
        return ExposureIntent(alpha_direction=1.5)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
