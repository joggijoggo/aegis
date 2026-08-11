import datetime

import backtrader as bt

from tests.dependency.backtrader.bbroker_confrontation.strategy import (
    LifecycleMonitoringStrategy,
)

class ConfrontationMemoryDataFeed(bt.feed.DataBase):
    """Deterministic 4-bar historical pricing stream compliant with Backtrader's metaclass copying."""

    def __init__(self) -> None:
        """Initializes baseline line arrays and structural internal states."""
        super().__init__()
        self._records = [
            # [Timestamp, Open, High, Low, Close, Volume, OpenInterest]
            [datetime.datetime(2026, 8, 1, 12, 0), 1.0000, 1.0100, 0.9900, 1.0100, 1000.0, 0.0], # Bar 1
            [datetime.datetime(2026, 8, 1, 12, 1), 1.0100, 1.0500, 1.0100, 1.0400, 1000.0, 0.0], # Bar 2
            [datetime.datetime(2026, 8, 1, 12, 2), 1.0400, 1.0800, 1.0300, 1.0700, 1000.0, 0.0], # Bar 3
            [datetime.datetime(2026, 8, 1, 12, 3), 1.0700, 1.1000, 1.0600, 1.0900, 1000.0, 0.0], # Bar 4
        ]
        self._idx = 0

    def _load(self) -> bool:
        """Loads the next row elements into the active lines matrix via explicit [0] indexation."""
        if self._idx >= len(self._records):
            return False

        row = self._records[self._idx]
        self._idx += 1

        # CRITICAL MICROSTRUCTURAL FIX:
        # Array lines must be mutated using explicit indexation [0] for the current bar slot.
        # Direct raw property assignment triggers descriptor logic and causes a TypeError.
        self.lines.datetime[0] = bt.date2num(row[0])
        self.lines.open[0] = row[1]
        self.lines.high[0] = row[2]
        self.lines.low[0] = row[3]
        self.lines.close[0] = row[4]
        self.lines.volume[0] = row[5]
        self.lines.openinterest[0] = row[6]

        return True


def run_isolated_cerebro(scheme_cls: type[bt.CommissionInfo]) -> dict:
    """Helper function initializing and running Cerebro for a given commission scheme."""
    cerebro = bt.Cerebro()
    cerebro.addstrategy(LifecycleMonitoringStrategy)

    feed = ConfrontationMemoryDataFeed()
    cerebro.adddata(feed, name="EURUSD")

    cerebro.broker.set_cash(10000.0)
    cerebro.broker.addcommissioninfo(scheme_cls(), name="EURUSD")

    strategies = cerebro.run()
    # Cerebro returns a list of executing strategies. Extract index 0 to get telemetry.
    return strategies[0].telemetry
