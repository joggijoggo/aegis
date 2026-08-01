"""Aegis Framework - Execution Engine.

Orchestrates execution cycles by consuming market feeds, driving strategy bot
evaluations, and routing risk-sized orders to the broker gateway.
"""

from decimal import Decimal

from bots.base_bot import BaseBot
from broker_adapters.base_broker_adapter import BaseBrokerAdapter
from core.caching import HistoricalBuffer
from core.contract_registry import ContractRegistry
from core.models import BrokerEvent
from core.position_sizer import PositionSizer
from market_feeds.base_market_feed import BaseMarketFeed

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class AegisExecutionEngine:
    """Core orchestrator synchronizing market data ingestion and trading logic."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        bot: BaseBot,
        broker_adapter: BaseBrokerAdapter,
        contract_registry: ContractRegistry,
        position_sizer: PositionSizer,
    ):
        """Initializes the execution engine.

        Args:
            bot: Trading strategy instance executing evaluation logic.
            broker_adapter: Infrastructure bridge mapping orders to the venue.
            contract_registry: Repository storing contract specifications.
            position_sizer: Component generating risk-sized execution orders.
        """
        self._bot = bot
        self._broker_adapter = broker_adapter
        self._contract_registry = contract_registry
        self._position_sizer = position_sizer
        self._risk_percent = Decimal('0.01')
        self._buffers: dict[str, HistoricalBuffer] = {}

# -----------------------------------------------------------------------------

    def _process_broker_event(self, broker_event: BrokerEvent) -> None:
        """Processes an unread asynchronous broker event notification.

        Args:
            broker_event: The incoming framework event update instance.
        """
        # TODO: update internal tracking ledger with execution notifications
        pass

# -----------------------------------------------------------------------------

    def run_execution_cycle(
        self,
        symbol: str,
        market_feed: BaseMarketFeed,
    ) -> None:
        """Runs a complete execution cycle over the provided market feed.

        Args:
            symbol: Target financial instrument identifier.
            market_feed: Input market data source.
        """
        if symbol not in self._buffers:
            capacity = self._bot.warm_up_period
            self._buffers[symbol] = HistoricalBuffer(max_size=capacity)

        buffer = self._buffers[symbol]

        try:
            while True:
                # Flush and process asynchronous broker updates before market evaluation
                while self._broker_adapter.has_pending_events():
                    broker_event = self._broker_adapter.poll_event()
                    self._process_broker_event(broker_event)

                market_context = next(market_feed)
                buffer.append(value=market_context.prices.mid_price)

                exposure_intent = self._bot.evaluate(
                    market_context=market_context,
                    historical_values=buffer.to_list(),
                )

                if exposure_intent.alpha_direction is None:
                    continue

                if exposure_intent.alpha_direction == 0.0:
                    raise NotImplementedError('Close position')

                contract_specification = (
                    self._contract_registry.get_specification(symbol)
                )
                account_snapshot = self._broker_adapter.get_account_snapshot()

                order = self._position_sizer.create_order(
                    exposure_intent=exposure_intent,
                    risk_percent=self._risk_percent,
                    contract_specification=contract_specification,
                    account_snapshot=account_snapshot,
                    market_context=market_context,
                )

                self._broker_adapter.submit_order(order)
        except StopIteration:
            pass

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
