"""Aegis Framework - Backtrader Strategy Proxy.

Provides the infrastructure strategy proxy that intercepts Backtrader lifecycle hooks.
"""

import logging

import backtrader as bt

from aegis.core.model import EventType

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class BacktraderProxyStrategy(bt.Strategy):
    """Infrastructure strategy proxy mapping Backtrader execution hooks to Aegis."""

    params = (
        ('bridge', None),
    )

# -----------------------------------------------------------------------------

    def __init__(self, *args, **kwargs) -> None:
        """Initializes the proxy strategy and extracts the synchronization bridge."""
        super().__init__(*args, **kwargs)
        self._bridge = self.p.bridge

# -----------------------------------------------------------------------------

    def next(self) -> None:
        """Intercepts the current historical data update and submits it to the bridge."""
        self._bridge.submit_event(EventType.MARKET_TICK, self.data)

# -----------------------------------------------------------------------------

    def notify_order(self, order: bt.Order) -> None:
        """Intercepts framework order state changes and submits them to the bridge.

        Args:
            order: The raw infrastructure order instance undergoing a state update.
        """
        self._bridge.submit_event(EventType.ORDER_NOTIFICATION, order)

# -----------------------------------------------------------------------------

    def notify_trade(self, trade: bt.Trade) -> None:
        """Intercepts framework trade updates and submits them to the bridge.

        Args:
            trade: The raw infrastructure trade update record.
        """
        self._bridge.submit_event(EventType.TRADE_NOTIFICATION, trade)

# -----------------------------------------------------------------------------

    def start(self) -> None:
        """Executes the framework startup hook and submits the instance reference."""
        self._bridge.bind_strategy(self)
        # Freeze the infra thread until the engine is ready.
        self._bridge.wait_engine_is_ready()

# -----------------------------------------------------------------------------

    def stop(self) -> None:
        """Intercepts the framework teardown hook and signals the bridge."""
        self._bridge.stop_simulation()

        # Inject a poison pill into the market queue to instantly unblock
        # the domain engine thread and prevent termination deadlocks.
        self._bridge.get_market_queue().put(None)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
