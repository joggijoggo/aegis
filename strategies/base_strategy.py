"""Aegis Framework - Core Strategy Lifecycle Layer.

Defines the abstract base class enforcing execution loops and warm-up anchors.
"""

from abc import ABC
from abc import abstractmethod

from brokers.base_broker import AbstractBrokerBridge
from core.models import MarketPricePoint

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class AbstractStrategy(ABC):
    """Base template enforcing technical data loading and order routing loops."""

# -----------------------------------------------------------------------------

    def __init__(self, broker_bridge: AbstractBrokerBridge, warm_up_bars: int = 200):
        """Initializes the structural lifecycle tracker and broker port anchors.

        Args:
            broker_bridge (AbstractBrokerBridge): Connected execution gateway node.
            warm_up_bars (int): Minimal history length required to clear lookups.
        """
        self.broker = broker_bridge
        self.warm_up_bars = warm_up_bars
        self.is_warmed_up = False

# -----------------------------------------------------------------------------

    def on_bar_close(
        self,
        asset: str,
        price_snapshot: MarketPricePoint,
        historical_closes: list[float]
    ) -> None:
        """Triggers operational evaluation cycles at terminal interval boundaries.

        Args:
            asset (str): Target currency pair symbol identity.
            price_snapshot (MarketPricePoint): Frozen immutable pricing bucket.
            historical_closes (list[float]): Available timeline collection space.
        """
        if len(historical_closes) < self.warm_up_bars:
            self.is_warmed_up = False
            return

        self.is_warmed_up = True
        self._on_bar_close(asset, price_snapshot, historical_closes)

# -----------------------------------------------------------------------------

    @abstractmethod
    def _on_bar_close(
        self,
        asset: str,
        price_snapshot: MarketPricePoint,
        historical_closes: list[float]
    ) -> None:
        """Core internal processing loop to be implemented by child strategies."""
        pass

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
