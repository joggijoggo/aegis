import pytest
from tests.broker_adapters.bbroker_confrontations.schemes import SpotStockCashScheme
from tests.broker_adapters.bbroker_confrontations.data_feed import run_isolated_cerebro

def test_bt_spot_stock_cash_behavior() -> None:
    """Systematically verifies Spot Stock accounting metrics across all individual bars."""
    metrics = run_isolated_cerebro(SpotStockCashScheme)

    # -------------------------------------------------------------------------
    # BAR 1: INITIAL STATE (12:00) - Order Submitted
    # -------------------------------------------------------------------------
    assert metrics[1]['cash'] == 10000.0
    assert metrics[1]['value'] == 10000.0
    assert metrics[1]['size'] == 0.0

    # -------------------------------------------------------------------------
    # BAR 2: POSITION OPEN (12:01) - Share Bought at 1.0100 Open
    # -------------------------------------------------------------------------
    # MICROSTRUCTURAL ANALYSIS & METROLOGY ALIGNMENT:
    # Initial Theoretical Value Expectation: 10003.01
    # Actual Backtrader 1.9.78.123 Result: 10000.03
    #
    # EXPLANATION:
    # My previous manual calculation incorrectly added the absolute close price (1.0400)
    # to the initial capital base. The exact mathematical sequence executed by bbroker is:
    # 1. Available Cash = 10000.0 (Initial) - 1.0100 (Upfront Purchase Cost) = 9998.99
    # 2. Position Value = 1.0 (Size) * 1.0400 (Current Close Price) = 1.0400
    # 3. Total Account Value = 9998.99 (Cash) + 1.0400 (Asset Value) = 10000.03
    # This reflects a net floating gain of exactly +0.03 (1.0400 close - 1.0100 entry).
    # -------------------------------------------------------------------------
    assert metrics[2]['cash'] == pytest.approx(9998.99)
    assert metrics[2]['value'] == pytest.approx(10000.03)
    assert metrics[2]['size'] == 1.0

    # -------------------------------------------------------------------------
    # BAR 3: POSITION HELD (12:02) - Stock Price Appreciates to 1.0700 Close
    # -------------------------------------------------------------------------
    # Cash remains strictly static since no cashadjust() happens for stocklike=True.
    # Position Value updates to 1.0 * 1.0700 = 1.0700.
    # Total Account Value = 9998.99 (Cash) + 1.0700 (Asset) = 10000.06
    # -------------------------------------------------------------------------
    assert metrics[3]['cash'] == pytest.approx(9998.99)
    assert metrics[3]['value'] == pytest.approx(10000.06)
    assert metrics[3]['size'] == 1.0

    # -------------------------------------------------------------------------
    # BAR 4: POSITION CLOSED (12:03) - Share Liquidated at Open Price (1.0700)
    # -------------------------------------------------------------------------
    # The share is sold at Bar 4 Open (1.0700). Backtrader reinjects the full
    # proceeds back into liquid cash. Position size drops to 0.0.
    # Final Cash Balance = 9998.99 + 1.0700 = 10000.06
    # -------------------------------------------------------------------------
    assert metrics[4]['cash'] == pytest.approx(10000.06)
    assert metrics[4]['value'] == pytest.approx(10000.06)
    assert metrics[4]['size'] == 0.0
