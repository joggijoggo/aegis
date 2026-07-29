"""Aegis Framework - Strategy Intentions Contract Unit Tests.

Validates that strategy instances return pure alpha destination signals.
"""

from core.models import (
    ExposureIntent,
    MarketPricePoint,
)
from tests.strategies.mocks import MockAlphaStrategy

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_abstract_strategy_enforces_exposure_intent_return_contract() -> None:
    """Ensures strategy execution cycles return a structured intent DTO."""
    snapshot = MarketPricePoint(
        timestamp=None,
        mid_price=1.0850,
        bid=1.0849,
        ask=1.0851,
        current_atr=0.0020,
    )
    historical_closes = [1.0800] * 10

    strategy = MockAlphaStrategy(warm_up_bars=5)
    intent = strategy.on_bar_close(
        asset="EURUSD",
        price_snapshot=snapshot,
        historical_closes=historical_closes,
    )

    assert isinstance(intent, ExposureIntent)
    assert intent.alpha_direction == 1.0
    assert intent.stop_loss_ticks == 20.0

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
