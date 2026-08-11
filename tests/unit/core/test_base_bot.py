"""Aegis Framework - Base Trading Bot Conformity Tests.

Verifies abstract base contract enforcement, instantiation restrictions, and
subclass implementation requirements for system trading algorithms.
"""

import pytest

from aegis.core.base_bot import BaseBot
from aegis.core.model import (
    ExposureIntent,
    MarketContext,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_base_bot_abstract_enforcement() -> None:
    """Verifies BaseBot cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseBot()  # type: ignore

# -----------------------------------------------------------------------------

def test_base_bot_nominal_implementation() -> None:
    """Verifies a compliant subclass instantiates and executes contract rules."""
    class ValidBot(BaseBot):

        @property
        def warm_up_period(self) -> int:
            return 14

        def evaluate(
            self,
            market_context: MarketContext,
            historical_values: list[float],
        ) -> ExposureIntent:
            return ExposureIntent(
                alpha_direction=0.5,
                stop_loss_ticks=20.0,
                take_profit_ticks=40.0,
            )

    bot = ValidBot()
    assert bot.warm_up_period == 14
    assert isinstance(bot, BaseBot)

# -----------------------------------------------------------------------------

def test_base_bot_subclass_requirements() -> None:
    """Verifies subclass raises TypeError if abstract methods are missing."""
    class IncompleteBot(BaseBot):
        pass

    with pytest.raises(TypeError):
        IncompleteBot()  # type: ignore

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
