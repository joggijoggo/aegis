"""Aegis Framework - Historical Buffer Unit Tests.

Validates sliding window accumulation, memory limits, and type conversion.
"""

import pytest

from aegis.core.caching import HistoricalBuffer

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_historical_buffer_accumulates_values() -> None:
    """Ensures input items append properly into the sequential store."""
    buffer = HistoricalBuffer(max_size=5)

    buffer.append(value=10.5)
    buffer.append(value=11.2)
    result = buffer.to_list()

    assert result == [10.5, 11.2]

# -----------------------------------------------------------------------------

def test_historical_buffer_enforces_maximum_capacity() -> None:
    """Ensures excess elements evict the oldest entry to maintain fixed size."""
    buffer = HistoricalBuffer(max_size=3)

    buffer.append(value=1.0)
    buffer.append(value=2.0)
    buffer.append(value=3.0)
    buffer.append(value=4.0)
    result = buffer.to_list()

    assert result == [2.0, 3.0, 4.0]

# -----------------------------------------------------------------------------

def test_historical_buffer_returns_pure_float_list() -> None:
    """Ensures the export mechanism yields a standard primitive float list."""
    buffer = HistoricalBuffer(max_size=2)

    buffer.append(value=1.0)
    result = buffer.to_list()

    assert isinstance(result, list)
    assert all(isinstance(item, float) for item in result)

# -----------------------------------------------------------------------------

def test_historical_buffer_validation_on_initialization() -> None:
    """Ensures negative size bounds trigger an immediate ValueError."""
    with pytest.raises(ValueError, match="Buffer maximum size must be greater than or equal to zero"):
        HistoricalBuffer(max_size=-1)

    # Verify that zero capacity is now successfully allowed
    buffer = HistoricalBuffer(max_size=0)
    assert buffer.to_list() == []

# -----------------------------------------------------------------------------

def test_historical_buffer_length_tracking() -> None:
    """Verifies that len() returns the exact count of active entries and
    correctly caps at the maximum allocated capacity bounds.
    """
    # Initialize a buffer with a restricted sliding capacity
    buffer = HistoricalBuffer(max_size=3)
    assert len(buffer) == 0

    # Append elements sequentially and verify the incremental sizing
    buffer.append(10.5)
    assert len(buffer) == 1

    buffer.append(11.2)
    assert len(buffer) == 2

    buffer.append(11.8)
    assert len(buffer) == 3

    # Append an extra element to trigger the internal rolling eviction
    # The size must remain locked to the maximum capacity ceiling parameter
    buffer.append(12.1)
    assert len(buffer) == 3

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
