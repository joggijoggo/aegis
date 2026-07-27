"""Aegis Framework - Backtrader Strategy Inbound Ingestion Bridge.

Connects Backtrader lifecycle event loops directly to Aegis strategy brains.
"""

from typing import Any

import backtrader as bt

from brokers.backtrader_adapter import BacktraderBrokerAdapter
from core.models import MarketPricePoint

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class BacktraderStrategyBridge(bt.Strategy):
    """Inbound orchestration bridge translating timeline ticks to Aegis models."""

# -----------------------------------------------------------------------------

    def __init__(self, aegis_bot: Any):
        """Initializes the event broker bridge linking active quantitative nodes.

        Args:
            aegis_bot (Any): Target instance of an Aegis abstract strategy bot.
        """
        self.aegis_bot = aegis_bot

        # Extract instrument specs stored into the initial broker to preserve context
        specs_ref = getattr(self.aegis_bot.broker, "_instrument_specs", {})

        # Hot-wire the hexagonal architecture loop by binding production adapter
        self.aegis_bot.broker = BacktraderBrokerAdapter(
            bt_strategy=self,
            instrument_specs=specs_ref,
        )

# -----------------------------------------------------------------------------

    def next(self) -> None:
        """Evaluates ongoing terminal intervals ticks released by Cerebro loops."""
        # 1. Capture exact timeline timestamp parameters from Backtrader line tracking
        current_dt = self.data.datetime.datetime(0)
        mid_price = float(self.data.close[0])

        # 2. Simulate standard asset pricing matrix offsets parameters
        # Note: Will leverage dynamic IGFrictionEngine linkage during Jalon 5 expansion
        bid_price = mid_price - 0.0001
        ask_price = mid_price + 0.0001

        # 3. Dynamic sliding window extraction layer routing for warm-up buffers
        current_buffer_size = len(self)
        historical_closes = self.data.close.get(size=current_buffer_size)

        # 4. Instantiation of unified immutable market models containers snapshot
        price_snapshot = MarketPricePoint(
            timestamp=current_dt,
            mid_price=mid_price,
            bid=bid_price,
            ask=ask_price,
            current_atr=0.0010,
        )

        # 5. Route structured parameters packets to the Aegis decision loop
        self.aegis_bot.on_bar_close(
            asset="EURUSD",
            price_snapshot=price_snapshot,
            historical_closes=historical_closes,
        )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
