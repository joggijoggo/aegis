"""Aegis Framework - Trading bot execution registry.

Tracks active transaction groups to isolate individual bot market exposure.
"""

from dataclasses import replace

from core.exceptions import NettingRestrictionError
from core.models import (
    Order,
    OrderSide,
    OrderType,
)
from core.order_group import OrderGroup

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class ExecutionTracker:
    """Memory ledger tracking active order groups indexed by bot identifier."""

# -----------------------------------------------------------------------------

    def __init__(self) -> None:
        """Initialize an empty execution tracking ledger."""
        self._executions: dict[str, OrderGroup] = {}

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

        child_side = OrderSide.SELL if order.side == OrderSide.BUY else OrderSide.BUY
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

        self._executions[bot_id] = order_group

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
