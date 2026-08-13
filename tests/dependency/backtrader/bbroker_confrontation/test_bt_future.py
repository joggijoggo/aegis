import pytest

from aegis.infra.backtrader import FutureFixedMarginScheme
from tests.dependency.backtrader.bbroker_confrontation.data_feed import (
    run_isolated_cerebro,
)

def test_bt_future_fixed_margin_behavior() -> None:
    """Systematically verifies Future accounting metrics across all individual bars."""
    metrics = run_isolated_cerebro(FutureFixedMarginScheme)

    # -------------------------------------------------------------------------
    # BAR 1: INITIAL STATE (12:00) - Order Submitted
    # -------------------------------------------------------------------------
    assert metrics[1]['cash'] == 10000.0
    assert metrics[1]['value'] == 10000.0
    assert metrics[1]['size'] == 0.0

    # -------------------------------------------------------------------------
    # BAR 2: POSITION OPEN (12:01) - Order Executed at Open Price (1.0100)
    # -------------------------------------------------------------------------
    # MICROSTRUCTURAL ANALYSIS & METROLOGY ALIGNMENT:
    # Initial Theoretical Expectation: 9950.03
    # Actual Backtrader 1.9.78.123 Result: 9950.030000000001 (Float drift)
    #
    # EXPLANATION:
    # The native Backtrader BackBroker operates entirely on standard IEEE 754
    # floating-point numbers. Accumulating fractional values like 0.03 (the bar PnL
    # from 1.0100 open to 1.0400 close) creates an unrounded binary mantissa remainder.
    # We must enforce pytest.approx() to safely bridge this precision gap.
    # -------------------------------------------------------------------------
    assert metrics[2]['cash'] == pytest.approx(9950.03)
    assert metrics[2]['value'] == pytest.approx(10000.03)
    assert metrics[2]['size'] == 1.0

    # -------------------------------------------------------------------------
    # BAR 3: POSITION HELD (12:02) - Position Survives and Accumulates PnL
    # -------------------------------------------------------------------------
    # The bar closes at 1.0700. Additional profit = 1.0700 - 1.0400 = +0.03.
    # The daily cashadjust() engine triggers at the close of this bar interval,
    # forcing the previous bar's profit to crystallize into physical cash equity.
    # Accumulated Cash = 9950.03 + 0.03 = 9950.06
    # -------------------------------------------------------------------------
    assert metrics[3]['cash'] == pytest.approx(9950.06)
    assert metrics[3]['value'] == pytest.approx(10000.06)
    assert metrics[3]['size'] == 1.0

    # -------------------------------------------------------------------------
    # BAR 4: POSITION CLOSED (12:03) - Position Liquidated at Open Price (1.0700)
    # -------------------------------------------------------------------------
    # The market close signal executes at the open of Bar 4 (1.0700).
    # The position size drops back to 0.0. The 50.0 flat margin collateral held
    # under lock is fully un-sequestered and returned to the free cash register.
    # Final Cash Balance = 9950.06 + 50.0 = 10000.06
    # -------------------------------------------------------------------------
    assert metrics[4]['cash'] == pytest.approx(10000.06)
    assert metrics[4]['value'] == pytest.approx(10000.06)
    assert metrics[4]['size'] == 0.0
