"""Aegis Framework - Explicit Contractual Component Mocks."""

from bots.base_bot import BaseBot
from broker_adapters.base_broker_adapter import BaseBrokerAdapter
from core.models import (
    AccountSnapshot,
    ExposureIntent,
    MarketContext,
    Order,
    OrderReceipt,
    OrderStatus,
)
from market_feeds.base_market_feed import BaseMarketFeed
from tests.testutils.factories import create_account_snapshot_factory

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class FakeBot(BaseBot):
    """Fake trading bot."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        exposure_intent: ExposureIntent | None = None,
        warm_up: int = 10,
    ):
        """Initializes the fake trading bot with static execution behaviors."""
        self._exposure_intent = exposure_intent or ExposureIntent(1.0, 50.0, 100.0)
        self._warm_up_period = warm_up

# -----------------------------------------------------------------------------

    def evaluate(
        self,
        market_context: MarketContext,
        historical_values: list[float],
    ) -> ExposureIntent:
        """Evaluates market context to return the pre-set exposure intention."""
        return self._exposure_intent

# -----------------------------------------------------------------------------

    @property
    def warm_up_period(self) -> int:
        """Gets the minimum historical data length required for evaluation."""
        return self._warm_up_period

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class FakeBrokerAdapter(BaseBrokerAdapter):
    """Fake broker gateway."""

# -----------------------------------------------------------------------------

    def __init__(self, account_snapshot: AccountSnapshot | None = None):
        """Initializes the fake broker gateway with a static ledger snapshot."""
        self.submitted_orders: list[Order] = []
        self._account_snapshot = account_snapshot or create_account_snapshot_factory()

# -----------------------------------------------------------------------------

    def get_account_snapshot(self) -> AccountSnapshot:
        """Gets the current trading account snapshot."""
        return self._account_snapshot

# -----------------------------------------------------------------------------

    def submit_order(self, order: Order) -> OrderReceipt:
        """Submits the execution order request to the fake venue ledger."""
        self.submitted_orders.append(order)
        return OrderReceipt(
            broker_order_id=f'BRK-FAKE-{len(self.submitted_orders)}',
            client_order_id=order.client_order_id,
            status=OrderStatus.FILLED,
            average_execution_price=order.price,
        )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class FakeMarketFeed(BaseMarketFeed):
    """Fake market data feed."""

# -----------------------------------------------------------------------------

    def __init__(self, market_contexts: list[MarketContext]):
        """Initializes the fake market feed stream with a fixed data series."""
        self._iterator = iter(market_contexts)

# -----------------------------------------------------------------------------

    def __next__(self) -> MarketContext:
        """Gets the next sequential market state context."""
        return next(self._iterator)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
