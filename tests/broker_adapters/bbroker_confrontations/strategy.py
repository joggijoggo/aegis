import backtrader as bt

class LifecycleMonitoringStrategy(bt.Strategy):
    """Synchronous strategy executing an open-to-close loop and capturing broker states."""

    def __init__(self) -> None:
        """Initializes sequential step tracking and metrics logging dictionary buffers."""
        self.step = 0
        # Telemetry maps: step_id -> (cash, value, positions)
        self.telemetry = {}

    def next(self) -> None:
        """Processes the historical bar sequence step-by-step and records low-level metrics."""
        self.step += 1

        # BAR 1: Emit Market Buy order. It will execute at Bar 2 Open.
        if self.step == 1:
            self.buy(size=1.0)

        # BAR 3: Emit Market Sell order to close lines. It will execute at Bar 4 Open.
        elif self.step == 3:
            self.close()

        # Capture low-level broker metrics live at the end of each bar processing
        current_cash = self.broker.get_cash()
        current_value = self.broker.get_value()

        # Store active size magnitude for validation check
        position_size = 0.0
        if self.data in self.broker.positions:
            position_size = self.broker.positions[self.data].size

        self.telemetry[self.step] = {
            'cash': current_cash,
            'value': current_value,
            'size': position_size
        }
