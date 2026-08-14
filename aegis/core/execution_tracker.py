"""Aegis Framework - Trading bot execution registry.

Tracks active transaction groups to isolate individual bot market exposure.
"""

from dataclasses import replace
import logging

from aegis.core.base_broker_adapter import BaseBrokerAdapter
from aegis.core.exception import (
    DanglingExecutionError,
    NettingRestrictionError,
    UnsupportedBrokerEventError,
    UntrackedOrderException,
)
from aegis.core.model import (
    BrokerEvent,
    EventType,
    Order,
    OrderReceipt,
    OrderType,
    TradeReceipt,
)
from aegis.core.order_group import OrderGroup
from aegis.core.telemetry import TelemetryEmitter

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class ExecutionTracker(TelemetryEmitter):
    """Memory ledger tracking active order groups indexed by bot identifier."""

# -----------------------------------------------------------------------------

    def __init__(self) -> None:
        """Initialize an empty execution tracking ledger."""
        super().__init__()

        self._executions: dict[str, OrderGroup] = {}
        self._order_id_to_bot_id: dict[str, str] = {}

# -----------------------------------------------------------------------------

    def _clear_execution_context(self, bot_id: str) -> None:
        """Purge all structural tracking references from internal RAM structures.

        Args:
            bot_id: The unique identifier of the target trading bot.
        """
        # Reverse lookup since order group does not expose its order.
        keys_to_remove = [
            order_id
            for order_id, mapped_bot_id in self._order_id_to_bot_id.items()
            if mapped_bot_id == bot_id
        ]

        for order_id in keys_to_remove:
            self._order_id_to_bot_id.pop(order_id, None)

        self._executions.pop(bot_id, None)

# -----------------------------------------------------------------------------

    def has_active_execution(self, bot_id: str) -> bool:
        """Check if the specified bot has an active execution context.

        Args:
            bot_id: The unique identifier of the trading bot.

        Returns:
            True if an active execution exists, False otherwise.
        """
        return bot_id in self._executions

# -----------------------------------------------------------------------------

    def process_broker_event(self, broker_event: BrokerEvent) -> None:
        """Process an incoming broker event to update or clear execution states.

        Args:
            broker_event: The structural broker notification to evaluate.
        """
        valid_event_type = [EventType.ORDER_NOTIFICATION, EventType.TRADE_NOTIFICATION]

        if broker_event.event_type not in valid_event_type:
            raise UnsupportedBrokerEventError(
                f"Received unhandled or corrupted event type: {broker_event.event_type}"
            )

        receipt = broker_event.payload
        client_order_id = receipt.group_id

        if client_order_id not in self._order_id_to_bot_id:
            raise UntrackedOrderException(
                f"Broker event mismatch: order identity '{client_order_id}' is untracked."
            )

        bot_id = self._order_id_to_bot_id[client_order_id]
        order_group = self._executions[bot_id]
        prev_state = order_group.state

        if broker_event.event_type == EventType.ORDER_NOTIFICATION:
            assert isinstance(receipt, OrderReceipt)
            order_group.notify_order_change(receipt)
        elif broker_event.event_type == EventType.TRADE_NOTIFICATION:
            assert isinstance(receipt, TradeReceipt)
            order_group.notify_trade_change(receipt)

        logger.debug(
            'Order Group (%s) state: %s, position_size: %f',
            client_order_id,
            order_group.state,
            order_group.ledger.position_size,
        )

        if prev_state != order_group.state:
            logger.info(
                'Order group went from "%s" to "%s" (%s)',
                prev_state,
                order_group.state,
                client_order_id,
            )

        if order_group.is_terminal():
            self._clear_execution_context(bot_id)

# -----------------------------------------------------------------------------

    def register_order(self, bot_id: str, order: Order) -> None:
        """Register an initial order to instantiate an active execution group.

        Args:
            bot_id: The unique identifier of the trading bot.
            order: The initial order anchoring the execution.
        """
        if self.has_active_execution(bot_id):
            raise NettingRestrictionError(
                f'Netting rule restriction prevents bot "{bot_id}" '
                f'from establishing concurrent executions.'
            )

        orders: list[Order] = [order]

        child_side = order.side.reverse()
        child_base = replace(
            order,
            side=child_side,
            stop_loss_price=None,
            take_profit_price=None,
        )

        if order.stop_loss_price is not None:
            sl_order = replace(
                child_base,
                client_order_id=f'{order.client_order_id}-SL',
                order_type=OrderType.STOP,
                price=order.stop_loss_price,
            )
            orders.append(sl_order)

        if order.take_profit_price is not None:
            tp_order = replace(
                child_base,
                client_order_id=f'{order.client_order_id}-TP',
                order_type=OrderType.LIMIT,
                price=order.take_profit_price,
            )
            orders.append(tp_order)

        order_group = OrderGroup(
            parent_id=order.client_order_id,
            orders=orders,
        )

        for bracket_order in orders:
            self._order_id_to_bot_id[bracket_order.client_order_id] = bot_id

        order_group.register_listener(self.emit)
        self._executions[bot_id] = order_group

        logger.info('Order group registered (parent: %s)', order.client_order_id)

# -----------------------------------------------------------------------------

    def terminate_execution(self, bot_id: str, broker_adapter: BaseBrokerAdapter) -> None:
        """Force immediate market liquidation or cancellation for a targeted bot.

        Args:
            bot_id: The unique identifier of the target trading bot.
            broker_adapter: The infrastructure adapter handling network commands.
        """
        if not self.has_active_execution(bot_id):
            raise UntrackedOrderException(
                f"Termination failure: bot '{bot_id}' has no active "
                f"execution group registered in memory."
            )

        logger.info('Bot "%s" wants to terminate its execution', bot_id)

        order_group = self._executions[bot_id]
        parent_order = order_group.get_parent_order()

        if order_group.is_cancelable():
            logger.debug('Canceling position (%s)', parent_order.client_order_id)
            broker_adapter.cancel_order(parent_order)
        elif order_group.is_closable():
            logger.debug('Position is closable')
            exit_order = replace(
                parent_order,
                client_order_id=f'{parent_order.client_order_id}-XT',
                side=parent_order.side.reverse(),
                stop_loss_price=None,
                take_profit_price=None,
            )

            self._order_id_to_bot_id[exit_order.client_order_id] = bot_id
            order_group.attach_exit_order(exit_order)
            broker_adapter.close_position(exit_order)
        elif order_group.is_terminal():
            raise DanglingExecutionError(
                f"Termination failure: bot '{bot_id}' execution group "
                f"is already terminal but was not evicted from memory."
            )
        else:
            logger.debug('Position is neither cancelable, nor closable')
            # Active asynchronous transitional phase (CLOSING, REJECTING).
            # Network commands are already processing. Do not touch RAM or network.
            pass

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
