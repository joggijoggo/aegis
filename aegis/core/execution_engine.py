"""Aegis Framework - Execution Engine.

Orchestrates execution cycles by consuming market feeds, driving strategy bot
evaluations, and routing risk-sized orders to the broker gateway.
"""

from decimal import Decimal
import logging

from aegis.core.base_bot import BaseBot
from aegis.core.base_broker_adapter import BaseBrokerAdapter
from aegis.core.base_market_feed import BaseMarketFeed
from aegis.core.caching import HistoricalBuffer
from aegis.core.contract_registry import ContractRegistry
from aegis.core.execution_tracker import ExecutionTracker
from aegis.core.position_sizer import PositionSizer

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

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
        self._tracker = ExecutionTracker()
        self._buffers: dict[str, HistoricalBuffer] = {}

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
        logger.info('Starting engine execution cycles...')
        cycle_counter = 0

        if symbol not in self._buffers:
            capacity = self._bot.warm_up_period
            self._buffers[symbol] = HistoricalBuffer(max_size=capacity)

        buffer = self._buffers[symbol]

        try:
            while True:
                cycle_counter += 1
                logger.info('')
                logger.info('%s New Cycle (#%d) %s', '-'*20, cycle_counter, '-'*20)

                market_context = next(market_feed)
                logger.info(
                    'Received prices %s: mid=%s',
                    market_context.prices.timestamp,
                    market_context.prices.mid_price,
                )
                buffer.append(value=market_context.prices.mid_price)

                broker_snapshot = self._broker_adapter.get_broker_snapshot()

                # Flush and process asynchronous broker updates before market evaluation
                logger.info('Processing broker events...')
                while self._broker_adapter.has_pending_events():
                    broker_event = self._broker_adapter.poll_event()
                    self._tracker.process_broker_event(broker_event)
                logger.info('Broker events processed')

                logger.info('Evaluating bot...')
                exposure_intent = self._bot.evaluate(
                    market_context=market_context,
                    historical_values=buffer.to_list(),
                )
                logger.info(
                    'Bot exposure intent: %s',
                    'FLAT' if exposure_intent.is_flat() else (
                        'EXIT' if exposure_intent.is_exit() else 'ENTRY'
                    )
                )

                bot_id = 'BOT_ID' # TODO: Retrieve it from bot.

                if exposure_intent.is_flat():
                    pass # Nothing to do.
                elif exposure_intent.is_exit():
                    if not self._tracker.has_active_execution(bot_id):
                        pass # Nothing to do.
                    else:
                        self._tracker.terminate_execution(
                            bot_id=bot_id,
                            broker_adapter=self._broker_adapter,
                        )
                elif exposure_intent.is_entry():
                    if self._tracker.has_active_execution(bot_id):
                        pass # TODO: handle EDGING.
                    else:
                        contract_specification = (
                            self._contract_registry.get_specification(symbol)
                        )

                        order = self._position_sizer.create_order(
                            exposure_intent=exposure_intent,
                            risk_percent=self._risk_percent,
                            contract_specification=contract_specification,
                            account_snapshot=broker_snapshot.account,
                            market_context=market_context,
                        )

                        # Record the tracking container prior to infrastructure transmission.
                        self._tracker.register_order(bot_id=bot_id, order=order)

                        logger.info('Submitting order "%s" ...', order.client_order_id)
                        self._broker_adapter.submit_order(order)
                        logger.info('Order submitted')

        except StopIteration:
            logger.info('Cycle loop stopped')

        logger.info('Engine execution cycles completed (%d cycles)', cycle_counter)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
