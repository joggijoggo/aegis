"""Aegis Framework - Multi-Timeframe Structural Aggregators.

Handles live, forward-bias-free aggregation of lower-bound ticks into macro
timeframe candles without look-ahead leakages.
"""

from datetime import datetime
from typing import Any

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class TimeframeAggregator:
    """Handles live, forward-bias-free aggregation of macro timeframe candles."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        base_frame_minutes: int = 15,
        macro_definitions: list[str] = None
    ):
        """Initializes the multi-timeframe structural aggregation node.

        Args:
            base_frame_minutes (int): Step delta baseline size.
            macro_definitions (list[str]): List of high timeframes to build.
        """
        self.base_frame_minutes = base_frame_minutes
        self.macro_definitions = macro_definitions or ["4h", "1d"]
        self.buffers: dict[str, dict[str, list[dict[str, Any]]]] = {}
        self.completed_bars: dict[str, dict[str, list[dict[str, Any]]]] = {}

# -----------------------------------------------------------------------------

    def process_tick(
        self,
        asset: str,
        utc_timestamp: datetime,
        base_ohlc: dict[str, float]
    ) -> dict[str, bool]:
        """Ingests a base bar and updates ongoing macro structural builders.

        Args:
            asset (str): Target currency pair symbol.
            utc_timestamp (datetime): Safe absolute timeline anchor location.
            base_ohlc (dict[str, float]): Pure baseline pricing parameters.

        Returns:
            dict[str, bool]: Map tracking closed high timeframe boundaries.
        """
        if asset not in self.buffers:
            self.buffers[asset] = {tf: [] for tf in self.macro_definitions}
            self.completed_bars[asset] = {
                tf: [] for tf in self.macro_definitions
            }

        closed_flags = {tf: False for tf in self.macro_definitions}

        for tf in self.macro_definitions:
            is_closed = False
            if tf == "4h" and utc_timestamp.hour % 4 == 0 and utc_timestamp.minute == 0:
                is_closed = True
            elif tf == "1d" and utc_timestamp.hour == 0 and utc_timestamp.minute == 0:
                is_closed = True

            # Append the current incoming tick to the building segment first
            self.buffers[asset][tf].append({
                "timestamp": utc_timestamp,
                **base_ohlc
            })

            if is_closed and len(self.buffers[asset][tf]) > 0:
                closed_flags[tf] = True
                collapsed = self._collapse_buffer(self.buffers[asset][tf])
                self.completed_bars[asset][tf].append(collapsed)
                self.buffers[asset][tf] = []

        return closed_flags

# -----------------------------------------------------------------------------

    def get_completed_bars(
        self,
        asset: str,
        timeframe: str
    ) -> list[dict[str, Any]]:
        """Extracts delivered complete macro historical bars.

        Args:
            asset (str): Target currency pair symbol.
            timeframe (str): High timeframe string key identifier.

        Returns:
            list[dict[str, Any]]: Sequence of finalized bar entries.
        """
        if asset in self.completed_bars and timeframe in self.completed_bars[asset]:
            return self.completed_bars[asset][timeframe]
        return []

# -----------------------------------------------------------------------------

    def _collapse_buffer(
        self,
        buffer: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Collapses accumulated lower ticks into a single macro record.

        Args:
            buffer (list[dict[str, Any]]): Slices of fine base tick records.

        Returns:
            dict[str, Any]: Consolidated higher bar structure payload.
        """
        return {
            "timestamp": buffer[-1]["timestamp"],
            "open": buffer[0]["open"],
            "high": max(b["high"] for b in buffer),
            "low": min(b["low"] for b in buffer),
            "close": buffer[-1]["close"],
            "volume": sum(b["volume"] for b in buffer)
        }

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
