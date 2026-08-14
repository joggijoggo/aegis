"""Aegis Framework - Telemetry Session History Isolation Tests.

Verifies types retrieval integrity, passive memory collection boundaries,
and type-based filtration accuracy for multi-asset chronological tracking.
"""

from dataclasses import dataclass

from aegis.core.telemetry import SessionHistory

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

@dataclass(frozen=True)
class MockModelA:
    """Mock domain class tracking specific type sample entries."""
    value: str

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class MockModelB:
    """Mock domain class tracking alternate type sample entries."""
    value: int

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_history_stores_records_and_filters_by_class() -> None:
    """Verifies that history extracts only records matching the exact class."""
    history = SessionHistory()
    record_a = MockModelA(value='SAMPLE_A')
    record_b = MockModelB(value=42)

    history.receive(record_a)
    history.receive(record_b)

    results_a = history.get_records(MockModelA)
    results_b = history.get_records(MockModelB)

    assert len(results_a) == 1
    assert results_a[0].value == 'SAMPLE_A'
    assert len(results_b) == 1
    assert results_b[0].value == 42

# -----------------------------------------------------------------------------

def test_history_returns_empty_list_when_no_match() -> None:
    """Verifies that filtering an empty or unmatched repository returns empty."""
    history = SessionHistory()
    record_a = MockModelA(value='SAMPLE_A')

    history.receive(record_a)
    results = history.get_records(MockModelB)

    assert len(results) == 0
    assert results == []

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
