"""Aegis Framework - Indicator Caching Unit Tests.

Enforces TDD validation protocols onto the SQLite decentralized caching layers
and SHA-256 parameter signature generation.
"""
from core.caching import IndicatorCacheEngine

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_sqlite_cache_write_and_read_lifecycle():
    """Validates signature uniqueness and strict JSON serialization retrieval."""
    # Use an in-memory SQLite database to isolate test I/O contexts cleanly
    cache = IndicatorCacheEngine(db_path=':memory:')

    asset = 'EURUSD'
    ind_name = 'ATR'
    params = {'period': 14, 'multiplier': 2.0}
    mock_data = [1.0800, 1.0810, 1.0820, 1.0815]

    # 1. Attempt retrieval on empty cache database
    cached_payload = cache.get_vectors(
        asset_pair=asset,
        indicator_name=ind_name,
        parameters=params
    )
    assert cached_payload is None

    # 2. Write calculated mock sequence into database cache ledger
    cache.save_vectors(
        asset_pair=asset,
        indicator_name=ind_name,
        parameters=params,
        payload_data=mock_data
    )

    # 3. Re-attempt retrieval to validate signature match hit
    successful_payload = cache.get_vectors(
        asset_pair=asset,
        indicator_name=ind_name,
        parameters=params
    )
    assert successful_payload == mock_data

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
