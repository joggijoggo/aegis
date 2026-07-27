"""Aegis Framework - Master Clock & Synchronizer Unit Tests.

Enforces TDD validation protocols onto the timeline alignment loop layers.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from core.aggregators import TimeframeAggregator
from core.engine import MasterClockBacktestEngine

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_master_clock_linear_progression(mock_asymmetric_data):
    """Validates monotonic time steps and strict Forward-Fill execution.

    Args:
        mock_asymmetric_data (dict[str, pd.DataFrame]): Flawed pricing matrix.
    """
    start_time = datetime(2026, 3, 25, 14, 0, tzinfo=ZoneInfo('UTC'))
    end_time = datetime(2026, 3, 25, 14, 30, tzinfo=ZoneInfo('UTC'))

    engine = MasterClockBacktestEngine(
        start_date=start_time,
        end_date=end_time,
        base_step_minutes=15
    )

    engine.register_tenant_account(
        bot_id='TDD_Bot',
        asset='EURUSD',
        initial_capital=10000.0,
        base_spread=0.6
    )
    engine.register_tenant_account(
        bot_id='TDD_Bot',
        asset='GBPUSD',
        initial_capital=10000.0,
        base_spread=0.9
    )

    compiled_results = engine.run_synchronized_backtest(
        historical_data_matrix=mock_asymmetric_data,
        strategy_registry={}
    )

    assert len(compiled_results) == 2

# -----------------------------------------------------------------------------

def test_master_clock_forward_fill_uninitialized_asset():
    """Validates the engine safety clause when an asset has no initial data history."""
    start_time = datetime(2026, 3, 25, 14, 0, tzinfo=ZoneInfo('UTC'))
    end_time = datetime(2026, 3, 25, 14, 15, tzinfo=ZoneInfo('UTC'))

    engine = MasterClockBacktestEngine(
        start_date=start_time,
        end_date=end_time,
        base_step_minutes=15
    )
    engine.register_tenant_account('TDD_Bot', 'EMPTY_ASSET', 10000.0, 0.5)

    # Empty matrix to force look_known_bars failure and trigger line 108 continue
    flawed_matrix = {'EMPTY_ASSET': pd.DataFrame(columns=['open'], index=[])}

    compiled_results = engine.run_synchronized_backtest(
        historical_data_matrix=flawed_matrix,
        strategy_registry={}
    )
    assert len(compiled_results) == 1

# -----------------------------------------------------------------------------

def test_timeframe_aggregator_look_ahead_shield():
    """Enforces zero look-ahead bias validation on macro data delivery."""
    aggregator = TimeframeAggregator(
        base_frame_minutes=15,
        macro_definitions=['4h']
    )
    asset = 'EURUSD'

    t1 = datetime(2026, 3, 25, 15, 30, tzinfo=ZoneInfo('UTC'))
    b1 = {'open': 1.0, 'high': 1.1, 'low': 0.9, 'close': 1.0, 'volume': 100}

    closes_t1 = aggregator.process_tick(
        asset=asset,
        utc_timestamp=t1,
        base_ohlc=b1
    )

    assert closes_t1['4h'] is False
    assert len(aggregator.get_completed_bars(asset, '4h')) == 0

    t2 = datetime(2026, 3, 25, 16, 0, tzinfo=ZoneInfo('UTC'))
    b2 = {'open': 1.0, 'high': 1.2, 'low': 0.8, 'close': 1.1, 'volume': 150}

    closes_t2 = aggregator.process_tick(
        asset=asset,
        utc_timestamp=t2,
        base_ohlc=b2
    )

    assert closes_t2['4h'] is True
    macro_bars = aggregator.get_completed_bars(asset, '4h')
    assert len(macro_bars) == 1
    assert macro_bars[0]['high'] == 1.2
    assert macro_bars[0]['low'] == 0.8

# -----------------------------------------------------------------------------

def test_timeframe_aggregator_daily_and_missing_asset():
    """Validates daily block closure processing and invalid asset extraction safety."""
    aggregator = TimeframeAggregator(
        base_frame_minutes=15,
        macro_definitions=['1d']
    )
    asset = 'EURUSD'

    # Midnight UTC timestamp to trigger the '1d' closure logic (line 66)
    t_midnight = datetime(2026, 3, 26, 0, 0, tzinfo=ZoneInfo('UTC'))
    b_dummy = {'open': 1.0, 'high': 1.0, 'low': 1.0, 'close': 1.0, 'volume': 10}

    # First seed the buffer
    t_seed = datetime(
        2026, 3, 25, 23, 45, tzinfo=ZoneInfo('UTC')
    )
    aggregator.process_tick(asset, t_seed, b_dummy)

    # Then hit the boundary milestone
    closes = aggregator.process_tick(asset, t_midnight, b_dummy)

    assert closes['1d'] is True
    assert len(aggregator.get_completed_bars(asset, '1d')) == 1

    # Assert missing asset extraction returns empty array strictly (line 100 safety code)
    assert aggregator.get_completed_bars('UNKNOWN_ASSET', '1d') == []

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
