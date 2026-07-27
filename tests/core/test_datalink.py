"""Aegis Framework - Local CSV DataLink Unit Tests.

Enforces TDD validation protocols onto historical file system ingestion layers
and timezone-aware pandas parsing.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from core.datalink import LocalCsvDataLink

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_csv_datalink_load_success(tmp_path):
    """Validates successful ingestion, parsing, and strict UTC index mapping."""
    # 1. Create a structured dummy CSV file within a sandboxed temporary directory
    csv_dir = tmp_path / 'data'
    csv_dir.mkdir()
    file_path = csv_dir / 'EURUSD.csv'

    # Write explicit mock data structure matching Aegis requirements
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('timestamp,open,high,low,close,volume,atr\n')
        f.write('2026-03-25 14:00:00,1.0800,1.0830,1.0790,1.0810,1000.0,0.0010\n')
        f.write('2026-03-25 14:15:00,1.0810,1.0840,1.0800,1.0820,1200.0,0.0011\n')

    # 2. Initialize the link pointing to the temporary sandbox folder
    datalink = LocalCsvDataLink(root_directory=str(csv_dir))
    df = datalink.load_asset_history(asset_pair='EURUSD')

    # 3. Structural assertions
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert float(df.iloc[0]['open']) == 1.0800

    # Validate that the index is strictly timezone-aware and anchored in UTC
    assert str(df.index.tz) == 'UTC'

    expected_dt = datetime(2026, 3, 25, 14, 0, tzinfo=ZoneInfo('UTC'))
    assert df.index[0] == expected_dt

# -----------------------------------------------------------------------------

def test_csv_datalink_with_pre_existing_timezone(tmp_path):
    """Validates conversion logic when historical data contains native timezones."""
    csv_dir = tmp_path / 'data_tz'
    csv_dir.mkdir()
    file_path = csv_dir / 'GBPUSD.csv'

    # Write mock data containing an explicit +02:00 timezone offset string
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('timestamp,open,high,low,close,volume,atr\n')
        f.write('2026-03-25 16:00:00+02:00,1.2500,1.2530,1.2480,1.2510,800.0,0.0015\n')

    datalink = LocalCsvDataLink(root_directory=str(csv_dir))
    df = datalink.load_asset_history(asset_pair='GBPUSD')

    assert str(df.index.tz) == 'UTC'
    # 16:00+02:00 must convert strictly to 14:00 UTC
    expected_dt = datetime(2026, 3, 25, 14, 0, tzinfo=ZoneInfo('UTC'))
    assert df.index[0] == expected_dt

# -----------------------------------------------------------------------------

def test_csv_datalink_missing_file_raises_exception():
    """Validates that explicit FileNotFoundError is raised for missing records."""
    datalink = LocalCsvDataLink(root_directory='/non_existent_folder_aegis_xyz')

    with pytest.raises(FileNotFoundError):
        datalink.load_asset_history(asset_pair='GBPUSD')

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
