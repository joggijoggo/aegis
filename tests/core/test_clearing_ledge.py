"""Aegis Framework - Clearing Ledger Unit Tests.

Validates volume accounting, weighted average pricing, realized profit and loss,
and over-hedge inversion sequences under symmetric market conditions.
"""

from decimal import Decimal

import pytest

from core.clearing_ledger import ClearingLedger
from core.models import OrderSide

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_clearing_ledger_initial_state() -> None:
    """Verify that a newly instantiated ledger starts perfectly flat."""
    ledger = ClearingLedger()
    assert ledger.position_size == Decimal('0.0')
    assert ledger.average_price == Decimal('0.0')
    assert ledger.realized_pnl == Decimal('0.0')

# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    'side,quantity,price,expected_size',
    [
        (OrderSide.BUY, Decimal('10.0'), Decimal('100.0'), Decimal('10.0')),
        (OrderSide.SELL, Decimal('10.0'), Decimal('100.0'), Decimal('-10.0')),
    ],
)
def test_clearing_ledger_exposure_opening(
    side: OrderSide,
    quantity: Decimal,
    price: Decimal,
    expected_size: Decimal,
) -> None:
    """Verify clean state initialization upon first execution ticket."""
    ledger = ClearingLedger()

    ledger.update_exposure(side, quantity, price)

    assert ledger.position_size == expected_size
    assert ledger.average_price == price
    assert ledger.realized_pnl == Decimal('0.0')

# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    'initial_side,accumulate_side,expected_size,expected_price',
    [
        (OrderSide.BUY, OrderSide.BUY, Decimal('15.0'), Decimal('105.0')),
        (OrderSide.SELL, OrderSide.SELL, Decimal('-15.0'), Decimal('105.0')),
    ],
)
def test_clearing_ledger_accumulation(
    initial_side: OrderSide,
    accumulate_side: OrderSide,
    expected_size: Decimal,
    expected_price: Decimal,
) -> None:
    """Verify weighted average price calculation during position accumulation."""
    ledger = ClearingLedger()
    ledger.update_exposure(initial_side, Decimal('10.0'), Decimal('100.0'))

    ledger.update_exposure(accumulate_side, Decimal('5.0'), Decimal('115.0'))

    assert ledger.position_size == expected_size
    assert ledger.average_price == expected_price
    assert ledger.realized_pnl == Decimal('0.0')

# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    'initial_side,reduce_side,expected_size,expected_pnl',
    [
        (OrderSide.BUY, OrderSide.SELL, Decimal('6.0'), Decimal('40.0')),
        (OrderSide.SELL, OrderSide.BUY, Decimal('-6.0'), Decimal('-40.0')),
    ],
)
def test_clearing_ledger_partial_reduction(
    initial_side: OrderSide,
    reduce_side: OrderSide,
    expected_size: Decimal,
    expected_pnl: Decimal,
) -> None:
    """Verify partial reduction maintains history and materializes PnL."""
    ledger = ClearingLedger()
    ledger.update_exposure(initial_side, Decimal('10.0'), Decimal('100.0'))

    ledger.update_exposure(reduce_side, Decimal('4.0'), Decimal('110.0'))

    assert ledger.position_size == expected_size
    assert ledger.average_price == Decimal('100.0')
    assert ledger.realized_pnl == expected_pnl

# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    'initial_side,close_side,price,expected_pnl',
    [
        (OrderSide.BUY, OrderSide.SELL, Decimal('90.0'), Decimal('-100.0')),
        (OrderSide.SELL, OrderSide.BUY, Decimal('90.0'), Decimal('100.0')),
    ],
)
def test_clearing_ledger_full_closure(
    initial_side: OrderSide,
    close_side: OrderSide,
    price: Decimal,
    expected_pnl: Decimal,
) -> None:
    """Verify atomical reset of cost history upon reaching flat exposure."""
    ledger = ClearingLedger()
    ledger.update_exposure(initial_side, Decimal('10.0'), Decimal('100.0'))

    ledger.update_exposure(close_side, Decimal('10.0'), price)

    assert ledger.position_size == Decimal('0.0')
    assert ledger.average_price == Decimal('0.0')
    assert ledger.realized_pnl == expected_pnl

# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    'initial_side,invert_side,expected_size,expected_pnl',
    [
        (OrderSide.BUY, OrderSide.SELL, Decimal('-5.0'), Decimal('-100.0')),
        (OrderSide.SELL, OrderSide.BUY, Decimal('5.0'), Decimal('100.0')),
    ],
)
def test_clearing_ledger_full_inversion_over_hedge(
    initial_side: OrderSide,
    invert_side: OrderSide,
    expected_size: Decimal,
    expected_pnl: Decimal,
) -> None:
    """Verify that out-sizing opposing flow resets history to market cost."""
    ledger = ClearingLedger()
    ledger.update_exposure(initial_side, Decimal('10.0'), Decimal('100.0'))

    ledger.update_exposure(invert_side, Decimal('15.0'), Decimal('90.0'))

    assert ledger.realized_pnl == expected_pnl
    assert ledger.position_size == expected_size
    assert ledger.average_price == Decimal('90.0')

# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    'invalid_quantity,invalid_price',
    [
        (Decimal('0.0'), Decimal('100.0')),
        (Decimal('10.0'), Decimal('-5.0')),
    ],
)
def test_clearing_ledger_invalid_metrics_raises(
    invalid_quantity: Decimal,
    invalid_price: Decimal,
) -> None:
    """Verify defensive rejection of corrupted execution parameters."""
    ledger = ClearingLedger()
    expected_msg = 'Metrics update failed: quantity'

    with pytest.raises(ValueError, match=expected_msg):
        ledger.update_exposure(
            OrderSide.BUY,
            invalid_quantity,
            invalid_price
        )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
