"""Aegis Framework - Clearing Ledger.

Manages physical volume accounting, weighted average price calculations,
and cumulative realized profit and loss independently from venue states.
"""

from decimal import Decimal

from aegis.core.model import OrderSide

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class ClearingLedger:
    """Manages physical volume accounting and net market exposure metrics."""

# -----------------------------------------------------------------------------

    def __init__(self) -> None:
        """Initializes an empty clearing ledger context."""
        self._position_size = Decimal('0.0')
        self._average_price = Decimal('0.0')
        self._realized_pnl = Decimal('0.0')

# -----------------------------------------------------------------------------

    @property
    def position_size(self) -> Decimal:
        """Retrieves the net physical open volume exposure."""
        return self._position_size

# -----------------------------------------------------------------------------

    @property
    def average_price(self) -> Decimal:
        """Retrieves the volume-weighted entry acquisition price."""
        return self._average_price

# -----------------------------------------------------------------------------

    @property
    def realized_pnl(self) -> Decimal:
        """Retrieves the cumulative realized profit and loss."""
        return self._realized_pnl

# -----------------------------------------------------------------------------

    def update_exposure(
        self,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
    ) -> None:
        """Updates internal accounting metrics from an execution fill.

        Args:
            side: The transaction side of the execution fill.
            quantity: The absolute execution volume of the fill.
            price: The execution unit price of the fill.

        Raises:
            ValueError: When quantity or price are not strictly positive.
        """
        target_quantity = Decimal(str(quantity))
        target_price = Decimal(str(price))

        if target_quantity <= 0 or target_price <= 0:
            raise ValueError(
                f'Metrics update failed: quantity ({target_quantity}) and '
                f'price ({target_price}) must be strictly positive.'
            )

        # Scenario 1: Exposure Opening
        if self._position_size == 0:
            if side == OrderSide.BUY:
                self._position_size = target_quantity
            else:
                self._position_size = -target_quantity

            self._average_price = target_price
            return

        is_buy = side == OrderSide.BUY
        is_accumulating = (self._position_size > 0 and is_buy) or (
            self._position_size < 0 and not is_buy
        )

        # Scenario 2: Accumulation
        if is_accumulating:
            if is_buy:
                flow = target_quantity
            else:
                flow = -target_quantity

            new_size = self._position_size + flow
            prior_cost = abs(self._position_size) * self._average_price
            incoming_cost = target_quantity * target_price
            total_cost = prior_cost + incoming_cost

            self._average_price = total_cost / abs(new_size)
            self._position_size = new_size
            return

        # Scenarios 3 & 4: Reduction, Closure or Inversion (Opposing flow)
        prior_abs_size = abs(self._position_size)
        closing_quantity = min(prior_abs_size, target_quantity)

        if self._position_size > 0:
            self._realized_pnl += closing_quantity * (
                target_price - self._average_price
            )
        else:
            self._realized_pnl += closing_quantity * (
                self._average_price - target_price
            )

        if target_quantity <= prior_abs_size:
            # Scenario 3: Simple reduction or full closure
            if target_quantity == prior_abs_size:
                self._position_size = Decimal('0.0')
                self._average_price = Decimal('0.0')
            else:
                if self._position_size > 0:
                    flow = -target_quantity
                else:
                    flow = target_quantity

                self._position_size += flow
        else:
            # Scenario 4: Full Inversion (Over-Hedge)
            residual_quantity = target_quantity - prior_abs_size
            if is_buy:
                self._position_size = residual_quantity
            else:
                self._position_size = -residual_quantity

            self._average_price = target_price

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
