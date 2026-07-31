"""Aegis Framework - Global Test Configuration and Shared Fixtures."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

pytest_plugins = ['tests.testutils.fixtures']

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

@pytest.fixture
def base_utc_timeline() -> pd.DatetimeIndex:
    """Generates a clean 24-hour monotonic timeline grid for tick alignment."""
    return pd.date_range(
        start='2026-03-25 00:00:00',
        end='2026-03-26 00:00:00',
        freq='15min',
        tz='UTC'
    )

# -----------------------------------------------------------------------------

@pytest.fixture
def mock_asymmetric_data() -> dict[str, pd.DataFrame]:
    """Creates an intentionally flawed multi-asset historical matrix."""
    timestamps = [
        datetime(2026, 3, 25, 14, 0, tzinfo=ZoneInfo('UTC')),
        datetime(2026, 3, 25, 14, 15, tzinfo=ZoneInfo('UTC')),
        datetime(2026, 3, 25, 14, 30, tzinfo=ZoneInfo('UTC'))
    ]

    eurusd_data = pd.DataFrame({
        'open': [1.0800, 1.0810, 1.0820],
        'high': [1.0830, 1.0840, 1.0850],
        'low': [1.0790, 1.0800, 1.0810],
        'close': [1.0810, 1.0820, 1.0830],
        'volume': [1000.0, 1200.0, 1100.0],
        'atr': [0.0010, 0.0011, 0.0010]
    }, index=timestamps)

    gbpusd_timestamps = [timestamps[0], timestamps[2]]
    gbpusd_data = pd.DataFrame({
        'open': [1.2500, 1.2520],
        'high': [1.2530, 1.2550],
        'low': [1.2480, 1.2500],
        'close': [1.2510, 1.2530],
        'volume': [800.0, 900.0],
        'atr': [0.0015, 0.0016]
    }, index=gbpusd_timestamps)

    return {'EURUSD': eurusd_data, 'GBPUSD': gbpusd_data}

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
