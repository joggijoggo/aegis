"""Aegis Framework - Walk-Forward Optimization Unit Tests.

Enforces TDD validation protocols onto the rolling walk-forward slicing loops
and historical matrix parameters.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from core.optimization import WalkForwardOptimizer

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_wfo_window_slicing_integrity():
    """Validates boundary anchoring and zero data leakage between windows."""
    # Define a 3-month anchor space grid
    start_time = datetime(2026, 1, 1, 0, 0, tzinfo=ZoneInfo('UTC'))
    end_time = datetime(2026, 4, 1, 0, 0, tzinfo=ZoneInfo('UTC'))

    # Instantiate the optimization orchestrator
    # Train: 30 days, Test: 10 days rolling segment anchor windows
    optimizer = WalkForwardOptimizer(
        start_date=start_time,
        end_date=end_time,
        train_days=30,
        test_days=10
    )

    windows = optimizer.generate_sliding_windows()

    # Assertions checking that window blocks are extracted cleanly
    assert len(windows) > 0

    # Examine the first window payload block boundary structure
    first_w = windows[0]
    assert first_w['train_start'] == start_time
    assert first_w['train_end'] == first_w['test_start']
    assert first_w['test_end'] <= end_time

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
