"""Aegis Framework - Order Group Invariant Authority.

Maintains structural integrity and execution alignment for contingent trading lifecycles.
"""

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
    """Operational entity enforcing structural alignment over contingent orders.

    Attributes:
        group_id: Unique internal tracking identifier identical to the parent order ID.
        clearing_closed: Boolean flag confirming asset ledger inventory is flat.
        order_states: Live lifecycle tracking state mapping for each registered order ID.
        orders: Technical specification index records for each registered order ID.
        state: Aggregated execution lifecycle state of the entire contingent group.
    """

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
            # Severe rupture: broker rejects the child cancellation post parent failure
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
        self.group_id: str = parent_id
        self.clearing_closed: bool = False

        # Build the technical specification index and initialize atomic states
        self.orders: dict[str, Order] = {}
        self.order_states: dict[str, OrderState] = {}

        for order in orders:
            self.orders[order.client_order_id] = order
            self.order_states[order.client_order_id] = OrderState.PENDING

        # Enforce strict birth invariant protection
        if self.group_id not in self.orders:
            raise ValueError(
                f"Initialization failed: parent order '{self.group_id}' "
                f"is missing from the provided orders collection."
            )

        self.state: OrderGroupState = OrderGroupState.PENDING

# -----------------------------------------------------------------------------

    def _evaluate_eviction_barrier(self) -> None:
        """Evaluates microstructural and accounting conditions to finalize the lifecycle."""
        # Handle automated triggers for complete opening failures
        if self.state == OrderGroupState.REJECTING:
            all_children_terminal = True

            for order_id, order_state in self.order_states.items():
                if order_id != self.group_id and not order_state.is_terminal:
                    all_children_terminal = False
                    break

            if all_children_terminal:
                parent_state = self.order_states.get(self.group_id)

                if parent_state == OrderState.CANCELED:
                    self.state = OrderGroupState.CANCELED
                elif parent_state == OrderState.REJECTED:
                    self.state = OrderGroupState.REJECTED

        # Handle automated triggers for nominal closing sequences
        if self.state == OrderGroupState.CLOSING and self.clearing_closed:
            all_orders_terminal = True

            for order_state in self.order_states.values():
                if not order_state.is_terminal:
                    all_orders_terminal = False
                    break

            if all_orders_terminal:
                self.state = OrderGroupState.COMPLETED

# -----------------------------------------------------------------------------

    @property
    def is_terminal(self) -> bool:
        """Determines if the group execution cycle is completely dead or closed."""
        return self.state.is_terminal

# -----------------------------------------------------------------------------

    # FIXME: Freeze execution mutations if the molecular state is already CORRUPTED
    def notify_order_change(self, order_receipt: OrderReceipt) -> None:
        """Ingests an infrastructure execution receipt to update the contingent group state.

        Args:
            order_receipt: The incoming broker order execution receipt payload.
        """
        if order_receipt.state in self._UNSUPPORTED_STATES:
            self.state = OrderGroupState.CORRUPTED
            raise NotImplementedError(
                f"Order state {order_receipt.state} is not supported in the current framework."
            )

        # FIXME: Replace this passive guard with an untracked order exception layout
        if order_receipt.client_order_id not in self.orders:
            return

        self.order_states[order_receipt.client_order_id] = order_receipt.state

        is_parent = order_receipt.client_order_id == self.group_id
        target_matrix = self._PARENT_MATRIX if is_parent else self._CHILD_MATRIX

        self.state = target_matrix[self.state][order_receipt.state]

        self._evaluate_eviction_barrier()

# -----------------------------------------------------------------------------

    def notify_trade_change(self, trade_receipt: TradeReceipt) -> None:
        """Ingests an isolated clearing settlement receipt to update the contingent group state.

        Args:
            trade_receipt: The incoming broker transaction clearing receipt payload.
        """
        if trade_receipt.is_open:
            self.clearing_closed = False
        else:
            self.clearing_closed = True

            # Verify if any contingent protection order has triggered the unwind
            any_child_filled = False
            for order_id, order_state in self.order_states.items():
                if order_id != self.group_id and order_state == OrderState.FILLED:
                    any_child_filled = True
                    break

            # Handle clandestine external closure vs authorized nominal sequence
            if not any_child_filled and self.state == OrderGroupState.ACTIVE:
                self.state = OrderGroupState.CORRUPTED
            elif self.state == OrderGroupState.CLOSING or any_child_filled:
                self._evaluate_eviction_barrier()

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
