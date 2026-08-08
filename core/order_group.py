"""Aegis Framework - Order Group Invariant Authority.

Maintains structural integrity and execution alignment for contingent trading lifecycles.
"""

from core.exceptions import (
    CorruptedOrderGroupError,
    UntrackedOrderException,
)
from core.models import (
    Order,
    OrderGroupState,
    OrderState,
    OrderReceipt,
    TradeReceipt,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class OrderGroup:
    """Operational entity enforcing structural alignment over contingent orders."""

    # Defines the absolute Child Transition Matrix:
    #
    #   CurrentOrderGroupState x IncomingOrderState -> TargetOrderGroupState
    #
    _CHILD_MATRIX = {
        OrderGroupState.PENDING: {
            # Nominal state where protection orders sit waiting in the book
            OrderState.PENDING: OrderGroupState.PENDING,
            # Rupture: protection fills before parent entry executed; upside down
            OrderState.FILLED: OrderGroupState.CORRUPTED,
            # Severe rupture: protection cancelled before parent entry is executed
            OrderState.CANCELED: OrderGroupState.CORRUPTED,
            # Severe rupture: protection rejected before parent entry is executed
            OrderState.REJECTED: OrderGroupState.CORRUPTED,
        },
        OrderGroupState.ACTIVE: {
            # Nominal invariant where active protections monitor exposure
            OrderState.PENDING: OrderGroupState.ACTIVE,
            # Nominal protection hit; position unwinding initiated under closing
            OrderState.FILLED: OrderGroupState.CLOSING,
            # Severe rupture: live protection cancelled; exposure left naked
            OrderState.CANCELED: OrderGroupState.CORRUPTED,
            # Severe rupture: live protection rejected by broker; exposure naked
            OrderState.REJECTED: OrderGroupState.CORRUPTED,
        },
        OrderGroupState.CLOSING: {
            # Severe rupture: brother protection remains pending during closing
            OrderState.PENDING: OrderGroupState.CORRUPTED,
            # Severe rupture: brother protection fills during closing; double execution
            OrderState.FILLED: OrderGroupState.CORRUPTED,
            # Nominal sequence: brother protection cancelled successfully post unwind
            OrderState.CANCELED: OrderGroupState.CLOSING,
            # Severe rupture: broker rejects the protection cancellation during closing
            OrderState.REJECTED: OrderGroupState.CORRUPTED,
        },
        OrderGroupState.REJECTING: {
            # Severe rupture: child signals a pending state after parent failure
            OrderState.PENDING: OrderGroupState.CORRUPTED,
            # Severe rupture: child protection fills while parent entry failed
            OrderState.FILLED: OrderGroupState.CORRUPTED,
            # Nominal sequence: child cancelled following the parent failure
            OrderState.CANCELED: OrderGroupState.REJECTING,
            # The broker might already have canceled the child order.
            OrderState.REJECTED: OrderGroupState.REJECTING,
        },
        OrderGroupState.CANCELED: {
            # Deadlock state: cancelled groups reject late infrastructure packets
            OrderState.PENDING: OrderGroupState.CORRUPTED,
            OrderState.FILLED: OrderGroupState.CORRUPTED,
            OrderState.CANCELED: OrderGroupState.CORRUPTED,
            OrderState.REJECTED: OrderGroupState.CORRUPTED,
        },
        OrderGroupState.COMPLETED: {
            # Deadlock state: completed groups reject late infrastructure packets
            OrderState.PENDING: OrderGroupState.CORRUPTED,
            OrderState.FILLED: OrderGroupState.CORRUPTED,
            OrderState.CANCELED: OrderGroupState.CORRUPTED,
            OrderState.REJECTED: OrderGroupState.CORRUPTED,
        },
        OrderGroupState.REJECTED: {
            # Deadlock state: rejected groups reject late infrastructure packets
            OrderState.PENDING: OrderGroupState.CORRUPTED,
            OrderState.FILLED: OrderGroupState.CORRUPTED,
            OrderState.CANCELED: OrderGroupState.CORRUPTED,
            OrderState.REJECTED: OrderGroupState.CORRUPTED,
        },
        OrderGroupState.CORRUPTED: {
            # Deadlock state: once corrupted, the group blocks all modifications
            OrderState.PENDING: OrderGroupState.CORRUPTED,
            OrderState.FILLED: OrderGroupState.CORRUPTED,
            OrderState.CANCELED: OrderGroupState.CORRUPTED,
            OrderState.REJECTED: OrderGroupState.CORRUPTED,
        },
    }

    # Defines the absolute Parent Transition Matrix:
    #
    #   CurrentOrderGroupState x IncomingOrderState -> TargetOrderGroupState
    #
    _PARENT_MATRIX = {
        OrderGroupState.PENDING: {
            # Nominal state where the parent entrance order sits in the venue book
            OrderState.PENDING: OrderGroupState.PENDING,
            # Nominal entrance execution opening the trade exposure
            OrderState.FILLED: OrderGroupState.ACTIVE,
            # Parent order cancelled before matching; aborting the cycle cleanly
            OrderState.CANCELED: OrderGroupState.REJECTING,
            # Parent order rejected due to margin or venue rules; aborting cycle
            OrderState.REJECTED: OrderGroupState.REJECTING,
        },
        OrderGroupState.ACTIVE: {
            # Severe rupture: parent order goes back to pending while group is active
            OrderState.PENDING: OrderGroupState.CORRUPTED,
            # Severe rupture: duplicate entry execution received for an active trade
            OrderState.FILLED: OrderGroupState.CORRUPTED,
            # Severe rupture: parent order cancelled post matching; data mismatch
            OrderState.CANCELED: OrderGroupState.CORRUPTED,
            # Severe rupture: parent order rejected post matching; data mismatch
            OrderState.REJECTED: OrderGroupState.CORRUPTED,
        },
        OrderGroupState.CLOSING: {
            # Severe rupture: parent order goes back to pending while trade is closing
            OrderState.PENDING: OrderGroupState.CORRUPTED,
            # Severe rupture: duplicate entry fill received during unwinding phase
            OrderState.FILLED: OrderGroupState.CORRUPTED,
            # Severe rupture: parent order cancelled during unwinding phase
            OrderState.CANCELED: OrderGroupState.CORRUPTED,
            # Severe rupture: parent order rejected during unwinding phase
            OrderState.REJECTED: OrderGroupState.CORRUPTED,
        },
        OrderGroupState.REJECTING: {
            # Severe rupture: failed parent signals an impossible pending state late
            OrderState.PENDING: OrderGroupState.CORRUPTED,
            # Severe rupture: parent fills late while children are being purged
            OrderState.FILLED: OrderGroupState.CORRUPTED,
            # Severe rupture: redundant cancel received for an already failing parent
            OrderState.CANCELED: OrderGroupState.CORRUPTED,
            # Severe rupture: redundant reject received for an already failing parent
            OrderState.REJECTED: OrderGroupState.CORRUPTED,
        },
        OrderGroupState.CANCELED: {
            # Deadlock state: cancelled groups reject late infrastructure packets
            OrderState.PENDING: OrderGroupState.CORRUPTED,
            OrderState.FILLED: OrderGroupState.CORRUPTED,
            OrderState.CANCELED: OrderGroupState.CORRUPTED,
            OrderState.REJECTED: OrderGroupState.CORRUPTED,
        },
        OrderGroupState.COMPLETED: {
            # Deadlock state: completed groups reject late infrastructure packets
            OrderState.PENDING: OrderGroupState.CORRUPTED,
            OrderState.FILLED: OrderGroupState.CORRUPTED,
            OrderState.CANCELED: OrderGroupState.CORRUPTED,
            OrderState.REJECTED: OrderGroupState.CORRUPTED,
        },
        OrderGroupState.REJECTED: {
            # Deadlock state: rejected groups reject late infrastructure packets
            OrderState.PENDING: OrderGroupState.CORRUPTED,
            OrderState.FILLED: OrderGroupState.CORRUPTED,
            OrderState.CANCELED: OrderGroupState.CORRUPTED,
            OrderState.REJECTED: OrderGroupState.CORRUPTED,
        },
        OrderGroupState.CORRUPTED: {
            # Deadlock state: once corrupted, the group blocks all modifications
            OrderState.PENDING: OrderGroupState.CORRUPTED,
            OrderState.FILLED: OrderGroupState.CORRUPTED,
            OrderState.CANCELED: OrderGroupState.CORRUPTED,
            OrderState.REJECTED: OrderGroupState.CORRUPTED,
        },
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
        self._parent_id: str = parent_id
        self._clearing_closed: bool | None = None

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

        self._state: OrderGroupState = OrderGroupState.PENDING

# -----------------------------------------------------------------------------

    def _evaluate_eviction_barrier(self) -> None:
        """Evaluates microstructural and accounting conditions to finalize the lifecycle."""
        # Handle automated triggers for complete opening failures
        if self._state == OrderGroupState.REJECTING:
            all_children_terminal = True

            for order_id, order_state in self._order_states.items():
                if order_id != self._parent_id and not order_state.is_terminal:
                    all_children_terminal = False
                    break

            if all_children_terminal:
                parent_state = self._order_states.get(self._parent_id)

                if parent_state == OrderState.CANCELED:
                    self._state = OrderGroupState.CANCELED
                elif parent_state == OrderState.REJECTED:
                    self._state = OrderGroupState.REJECTED

        # Handle automated triggers for nominal closing sequences
        if self._state == OrderGroupState.CLOSING and self._clearing_closed:
            all_orders_terminal = True

            for order_state in self._order_states.values():
                if not order_state.is_terminal:
                    all_orders_terminal = False
                    break

            if all_orders_terminal:
                self._state = OrderGroupState.COMPLETED

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
        return self._state == OrderGroupState.PENDING and self._clearing_closed is None

# -----------------------------------------------------------------------------

    def is_closable(self) -> bool:
        """Determines whether the established market exposure can be liquidated.

        Returns:
            True if the group is closable, False otherwise.
        """
        # Exclude states that are already closing, aborting, dead, or corrupted.
        if self._state not in (OrderGroupState.PENDING, OrderGroupState.ACTIVE):
            return False

        # Prevent double-liquidation if the clearing closed the position ahead of the book.
        if self._clearing_closed is True:
            return False

        # Nominal active path: book confirms matching and clearing has not signaled closure.
        if self._state == OrderGroupState.ACTIVE:
            return True

        # Race condition path: clearing opens exposure while parent book status is delayed.
        return self._clearing_closed is False

# -----------------------------------------------------------------------------

    def is_terminal(self) -> bool:
        """Determines if the group execution cycle is completely dead or closed."""
        return self._state.is_terminal

# -----------------------------------------------------------------------------

    def notify_order_change(self, order_receipt: OrderReceipt) -> None:
        """Ingests an infrastructure execution receipt to update the contingent group state.

        Args:
            order_receipt: The incoming broker order execution receipt payload.

        Raises:
            CorruptedOrderGroupError: when the order group state is corrupted.
            UntrackedOrderException: when the receipt order id does not belong to the group.
        """
        if self._state == OrderGroupState.CORRUPTED:
            raise CorruptedOrderGroupError(
                f'Action denied: order group "{self._parent_id}" is corrupted.'
            )

        if order_receipt.state in self._UNSUPPORTED_STATES:
            self._state = OrderGroupState.CORRUPTED
            raise NotImplementedError(
                f"Order state {order_receipt.state} is not supported in the current framework."
            )

        if order_receipt.client_order_id not in self._orders:
            raise UntrackedOrderException(
                f'Order "{order_receipt.client_order_id}" not found '
                f'in group "{self._parent_id}".'
            )

        self._order_states[order_receipt.client_order_id] = order_receipt.state

        is_parent = order_receipt.client_order_id == self._parent_id
        target_matrix = self._PARENT_MATRIX if is_parent else self._CHILD_MATRIX

        prev_state = self._state
        self._state = target_matrix[self._state][order_receipt.state]

        if self._state == OrderGroupState.CORRUPTED:
            raise CorruptedOrderGroupError(
                f'Group "{self._parent_id}" went from "{prev_state}" '
                f'to "{self._state}" on order {order_receipt.client_order_id} '
                f'entering state "{order_receipt.state}".'
            )

        self._evaluate_eviction_barrier()

# -----------------------------------------------------------------------------

    def notify_trade_change(self, trade_receipt: TradeReceipt) -> None:
        """Ingests an isolated clearing settlement receipt to update the contingent group state.

        Args:
            trade_receipt: The incoming broker transaction clearing receipt payload.

        Raises:
            CorruptedOrderGroupError: when the order group state is corrupted.
        """
        if self._state == OrderGroupState.CORRUPTED:
            raise CorruptedOrderGroupError(
                f'Action denied: order group "{self._parent_id}" is corrupted.'
            )

        prev_state = self._state

        if trade_receipt.is_open:
            self._clearing_closed = False
        else:
            self._clearing_closed = True

            # Verify if any contingent protection order has triggered the unwind
            any_child_filled = False
            for order_id, order_state in self._order_states.items():
                if order_id != self._parent_id and order_state == OrderState.FILLED:
                    any_child_filled = True
                    break

            # Handle clandestine external closure vs authorized nominal sequence
            if not any_child_filled and self._state == OrderGroupState.ACTIVE:
                self._state = OrderGroupState.CORRUPTED
            elif self._state == OrderGroupState.CLOSING or any_child_filled:
                self._evaluate_eviction_barrier()

        if self._state == OrderGroupState.CORRUPTED:
            raise CorruptedOrderGroupError(
                f'Group "{self._parent_id}" went from {prev_state} '
                f'to {self._state} during trade clearing evaluation. '
                f'Trade Open flag: {trade_receipt.is_open}.'
            )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
