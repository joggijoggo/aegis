"""Aegis Framework - Order Group Invariant Authority.

Maintains structural integrity and execution alignment for contingent trading lifecycles.
"""

from decimal import Decimal
import logging

from aegis.core.clearing_ledger import ClearingLedger
from aegis.core.exception import (
    ClearingCorruptionError,
    CorruptedOrderGroupError,
    NettingRestrictionError,
    UntrackedOrderException,
)
from aegis.core.model import (
    Order,
    OrderGroupState,
    OrderReceipt,
    OrderSide,
    OrderState,
    TradeReceipt,
)
from aegis.core.telemetry import TelemetryEmitter

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class OrderGroup(TelemetryEmitter):
    """Operational entity enforcing structural alignment over contingent orders."""

    # Anticipative state weight mapping to filter network packet ordering faults
    _STATE_WEIGHTS: dict[OrderState, int] = {
        OrderState.PENDING: 0,
        # TODO: Add OrderState.PARTIALLY_FILLED: 1, once incremental fills are integrated
        OrderState.FILLED: 2,
        OrderState.CANCELED: 2,
        # TODO: Add OrderState.EXPIRED: 2, once time-in-force are integrated.
        OrderState.REJECTED: 2,
    }

    # Guardrails targeting unhandled microstructural infrastructure states
    _UNSUPPORTED_STATES = {OrderState.PARTIALLY_FILLED, OrderState.EXPIRED}

# -----------------------------------------------------------------------------

    def __init__(self, parent_id: str, orders: list[Order]):
        """Initializes the order group aggregate and maps its tracking ledger.

        Args:
            parent_id: Unique internal identifier of the execution entry order.
            orders: Collection of all contingent orders belonging to this transaction.
        """
        super().__init__()

        self._parent_id: str = parent_id
        self._exit_order_id: str | None = None

        self._clearing_closed: bool | None = None
        self._ledger = ClearingLedger()
        self._is_corrupted: bool = False

        self._orders: dict[str, Order] = {}
        self._order_states: dict[str, OrderState] = {}

        for order in orders:
            self._orders[order.client_order_id] = order
            self._order_states[order.client_order_id] = OrderState.PENDING

        if self._parent_id not in self._orders:
            raise ValueError(
                f'Initialization failed: parent order \'{self._parent_id}\' '
                f'is missing from the provided orders collection.'
            )

# -----------------------------------------------------------------------------

    def attach_exit_order(self, exit_order: Order) -> None:
        """Binds the liquidation order instance to the group execution context.

        Args:
            exit_order: The order instance used to close the position.

        Raises:
            NettingRestrictionError: When an exit order is already attached.
            ValueError: When the exit order ID conflicts with an existing order.
        """
        if self._exit_order_id is not None:
            raise NettingRestrictionError(
                f'An exit order ({self._exit_order_id} is already registered '
                f'for group "{self._parent_id}".'
            )

        # Double checks.
        if exit_order.client_order_id in self._orders:
            raise ValueError(
                f'Order ID "{exit_order.client_order_id}" conflicts '
                f'with an existing order in group.'
            )

        self._exit_order_id = exit_order.client_order_id
        self._orders[exit_order.client_order_id] = exit_order
        self._order_states[exit_order.client_order_id] = OrderState.PENDING

# -----------------------------------------------------------------------------

    def get_parent_order(self) -> Order:
        """Retrieves the root execution order anchoring this tracking group.

        Returns:
            The parent domain order instance.
        """
        return self._orders[self._parent_id]

# -----------------------------------------------------------------------------

    def is_cancelable(self) -> bool:
        """Checks whether the order group can be canceled.

        Returns:
            True if the group is cancelable, False otherwise.
        """
        return self.state == OrderGroupState.PENDING

# -----------------------------------------------------------------------------

    def is_closable(self) -> bool:
        """Determines whether the established market exposure can be liquidated.

        Returns:
            True if the group is closable, False otherwise.
        """
        # Hard intention lock preventing concurrent double-liquidation
        if self._exit_order_id is not None:
            return False

        # Physical volume lock protecting against flat exposure clearance
        if self._ledger.position_size == Decimal('0.0'):
            return False

        # Exclude states that are already closing, aborting, dead, or corrupted.
        if self.state not in (OrderGroupState.PENDING, OrderGroupState.ACTIVE):
            return False

        # DEFENSIVE GUARD: Prevents double-liquidation if clearing closes ahead
        # of the book during race conditions (e.g., residual 0.01 fills on
        # canceled orders). Preserved for defense-in-depth even if upstream
        # corruption checks make this appear unreachable via public API.
        if self._clearing_closed is True:  # pragma: no cover
            return False

        # Nominal active path: book confirms matching and clearing has not signaled closure.
        if self.state == OrderGroupState.ACTIVE:
            return True

        # HISTORICAL FALLBACK: Mathematically unreachable due to state machine invariants.
        # If the position is non-flat, the state can never resolve to PENDING.
        # Preserved as a final defense-in-depth barrier against ghost orders
        # (clearing opens exposure while parent book status is delayed).
        return self._clearing_closed is False  # pragma: no cover

# -----------------------------------------------------------------------------

    def is_over_hedged(self) -> bool:
        """Evaluates whether the group suffers from unmanaged market exposure.

        Returns:
            True if exposure is active but matching closing volume is insufficient,
            False otherwise.
        """
        position = self._ledger.position_size

        if position == Decimal('0.0'):
            return False

        required_side = OrderSide.SELL if position > Decimal('0.0') else OrderSide.BUY
        pending_volume = Decimal('0.0')

        # Aggregate working volumes facing exposure with a single filtered condition
        for order_id, order_state in self._order_states.items():
            if (
                order_id != self._parent_id
                and order_state == OrderState.PENDING
                and self._orders[order_id].side == required_side
            ):
                pending_volume += self._orders[order_id].quantity

        # Strict inequality allows bidirectional bracket orders (SL and TP) to
        # coexist at PENDING state during nominal cruise phase without triggering.
        return pending_volume < abs(position)

# -----------------------------------------------------------------------------

    def is_terminal(self) -> bool:
        """Determines if the group execution cycle is completely dead or closed."""
        return self.state.is_terminal

# -----------------------------------------------------------------------------

    @property
    def ledger(self) -> ClearingLedger:
        """Retrieves the clearing ledger tracking physical volume balances."""
        return self._ledger

# -----------------------------------------------------------------------------

    def notify_order_change(self, order_receipt: OrderReceipt) -> None:
        """Ingests an infrastructure execution receipt to update the contingent group state.

        Args:
            order_receipt: The incoming broker order execution receipt payload.

        Raises:
            ClearingCorruptionError: when an execution fill lacks pricing data.
            CorruptedOrderGroupError: when the order group state is corrupted.
            UntrackedOrderException: when the receipt order id does not belong to the group.
        """
        logger.debug(
            'Received order receipt "%s" (%s)',
            order_receipt.state,
            order_receipt.client_order_id,
        )

        self.emit(order_receipt)

        if self._is_corrupted:
            raise CorruptedOrderGroupError(
                f'Action denied: order group "{self._parent_id}" is corrupted.'
            )

        if order_receipt.state in self._UNSUPPORTED_STATES:
            self._is_corrupted = True
            raise NotImplementedError(
                f"Order state {order_receipt.state} is not supported in the current framework."
            )

        if order_receipt.client_order_id not in self._orders:
            raise UntrackedOrderException(
                f'Order "{order_receipt.client_order_id}" not found '
                f'in group "{self._parent_id}".'
            )

        current_state = self._order_states[order_receipt.client_order_id]
        incoming_weight = self._STATE_WEIGHTS[order_receipt.state]
        current_weight = self._STATE_WEIGHTS[current_state]

        # Silently drop network duplicates or late out-of-order packets
        if incoming_weight <= current_weight:
            # TODO: log or warn.
            return

        self._order_states[order_receipt.client_order_id] = order_receipt.state

        if order_receipt.executed_quantity > 0:
            if order_receipt.average_execution_price is None:
                raise ClearingCorruptionError(
                    f'order "{order_receipt.client_order_id}" reported an '
                    f'execution volume of {order_receipt.executed_quantity} '
                    f'but the volume-weighted execution price was missing (None).'
                )

            order = self._orders[order_receipt.client_order_id]
            self._ledger.update_exposure(
                side=order.side,
                quantity=order_receipt.executed_quantity,
                price=order_receipt.average_execution_price,
            )

        if (
            order_receipt.client_order_id == self._exit_order_id
            and order_receipt.state in (OrderState.CANCELED, OrderState.REJECTED)
        ):
            self._is_corrupted = True

# -----------------------------------------------------------------------------

    def notify_trade_change(self, trade_receipt: TradeReceipt) -> None:
        """Ingests an isolated clearing settlement receipt to update the contingent group state.

        Args:
            trade_receipt: The incoming broker transaction clearing receipt payload.

        Raises:
            CorruptedOrderGroupError: when the order group state is corrupted.
        """
        logger.debug(
            'Received trade receipt "%s" (group_id: %s)',
            'TRADE_OPEN' if trade_receipt.is_open else 'TRADE_CLOSE',
            trade_receipt.group_id,
        )

        self.emit(trade_receipt)

        if self._is_corrupted:
            raise CorruptedOrderGroupError(
                f'Action denied: order group "{self._parent_id}" is corrupted.'
            )

        if trade_receipt.is_open:
            self._clearing_closed = False
        else:
            self._clearing_closed = True

            any_child_filled = any(
                order_state == OrderState.FILLED
                for order_id, order_state in self._order_states.items()
                if order_id not in (self._parent_id, self._exit_order_id)
            )

            # Exclude authorized exit liquidations from clandestine closure guards
            if (
                not any_child_filled
                and self._exit_order_id is None
                and self.state == OrderGroupState.ACTIVE
            ):
                self._is_corrupted = True

        if self._is_corrupted:
            raise CorruptedOrderGroupError(
                f'Group "{self._parent_id}" entered corrupted state '
                f'during trade clearing evaluation.'
            )

# -----------------------------------------------------------------------------

    @property
    def state(self) -> OrderGroupState:
        """The computed transaction lifecycle state of the execution group."""
        if self._is_corrupted:
            return OrderGroupState.CORRUPTED

        is_flat = self._ledger.position_size == Decimal('0.0')
        parent_state = self._order_states.get(self._parent_id)

        bracket_orders_terminal = all(
            state.is_terminal
            for order_id, state in self._order_states.items()
            if order_id != self._exit_order_id
        )

        exit_order_terminal = (
            self._exit_order_id is None
            or self._order_states[self._exit_order_id].is_terminal
        )

        exit_triggered = (
            self._exit_order_id is not None
            and self._order_states[self._exit_order_id] == OrderState.FILLED
        )

        children_triggered = any(
            state == OrderState.FILLED
            for client_order_id, state in self._order_states.items()
            if client_order_id not in (self._parent_id, self._exit_order_id)
        )

        if is_flat:
            if parent_state == OrderState.REJECTED:
                return OrderGroupState.REJECTED

            if parent_state == OrderState.CANCELED:
                return OrderGroupState.CANCELED

            if parent_state == OrderState.FILLED:
                if (
                    bracket_orders_terminal
                    and exit_order_terminal
                    and self._clearing_closed
                ):
                    return OrderGroupState.COMPLETED
                return OrderGroupState.CLOSING

            return OrderGroupState.PENDING

        else:
            if exit_triggered or children_triggered:
                return OrderGroupState.CLOSING

            return OrderGroupState.ACTIVE

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
