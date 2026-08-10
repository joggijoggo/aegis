"""Aegis Framework - Explicit Contractual Component Mocks."""

from queue import Queue

from aegis.core.base_bot import BaseBot
from aegis.core.base_broker_adapter import BaseBrokerAdapter
from aegis.core.base_market_feed import BaseMarketFeed
from aegis.core.model import (
    AccountSnapshot,
    BrokerEvent,
    BrokerSnapshot,
    EventType,
    ExposureIntent,
    MarketContext,
    Order,
    OrderState,
    PositionLedgerSnapshot,
)
from aegis.strategy.base_strategy import AbstractStrategy
from tests.testutil import (
    create_account_snapshot_factory,
    create_order_receipt_factory,
    create_position_ledger_snapshot_factory,
)

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

    def __init__(
        self,
        account_snapshot: AccountSnapshot | None = None,
        position_ledger: PositionLedgerSnapshot | None = None
    ):
        """Initializes the fake broker gateway with a static ledger snapshot."""
        self.submitted_orders: list[Order] = []
        self.snapshot_call_count = 0  # Call counter for execution verification
        self._account_snapshot = account_snapshot or create_account_snapshot_factory()
        self._position_ledger = position_ledger or create_position_ledger_snapshot_factory()
        self._pending_events: Queue = Queue()

# -----------------------------------------------------------------------------

    def _get_account_snapshot(self) -> AccountSnapshot:
        """Gets the current trading account snapshot."""
        return self._account_snapshot

# -----------------------------------------------------------------------------

    def _get_position_ledger_snapshot(self) -> PositionLedgerSnapshot:
        """Gets the current position ledger snapshot from the fake venue ledger."""
        return self._position_ledger

# -----------------------------------------------------------------------------

    def get_broker_snapshot(self) -> BrokerSnapshot:
        """Retrieves the unified temporal snapshot of account metrics and exposures."""
        self.snapshot_call_count += 1 # Increment the atomic verification tracker.
        return BrokerSnapshot(
            account=self._get_account_snapshot(),
            position_ledger=self._get_position_ledger_snapshot(),
        )

# -----------------------------------------------------------------------------

    def cancel_order(self, order: Order) -> None:
        pass

# -----------------------------------------------------------------------------

    def close_position(self, order: Order) -> None:
        pass

# -----------------------------------------------------------------------------

    def submit_order(self, order: Order) -> None:
        """Submits the execution order request to the fake venue ledger.

        Args:
            order: The order request.
        """
        self.submitted_orders.append(order)

        fake_receipt = create_order_receipt_factory(
            average_execution_price=order.price,
            client_order_id=order.client_order_id,
            executed_quantity=order.quantity,
            group_id=order.client_order_id,
            state=OrderState.PENDING,
        )
        broker_event = BrokerEvent(
            event_type=EventType.ORDER_NOTIFICATION,
            payload=fake_receipt,
        )
        self._pending_events.put(broker_event)

# -----------------------------------------------------------------------------

    def has_pending_events(self) -> bool:
        """Indicates whether unread broker events are available."""
        return not self._pending_events.empty()

# -----------------------------------------------------------------------------

    def poll_event(self) -> BrokerEvent:
        """Returns the next pending broker event.

        Returns:
            The retrieved broker event.
        """
        return self._pending_events.get()

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

class FakeStrategy(AbstractStrategy):
    """Fake trading strategy."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        exposure_intent: ExposureIntent | None = None,
        warm_up_period: int = 0,
    ) -> None:
        """Initializes the fake strategy settings."""
        super().__init__(warm_up_period=warm_up_period)
        self._exposure_intent = exposure_intent or ExposureIntent(1.0, 20.0)

# -----------------------------------------------------------------------------

    def _evaluate(
        self,
        market_context: MarketContext,
        historical_values: list[float],
    ) -> ExposureIntent:
        """Executes the strategy calculation logic."""
        return self._exposure_intent

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
