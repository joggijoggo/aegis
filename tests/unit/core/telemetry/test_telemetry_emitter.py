"""Aegis Framework - Telemetry Emitter Decoupling Tests.

Verifies standalone broadcasting integrity, multi-cast functional routing,
and instance isolation boundaries for core domain metrics distribution.
"""

from typing import Any

from aegis.core.telemetry import TelemetryEmitter

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_emitter_broadcasts_to_single_listener() -> None:
    """Verifies that a single attached listener receives the exact emitted record."""
    emitter = TelemetryEmitter()
    received_records: list[Any] = []

    def sample_listener(record: Any) -> None:
        received_records.append(record)

    emitter.register_listener(sample_listener)
    emitter.emit('MOCK_RECORD_A')

    assert len(received_records) == 1
    assert received_records[0] == 'MOCK_RECORD_A'

# -----------------------------------------------------------------------------

def test_emitter_broadcasts_to_multiple_listeners() -> None:
    """Verifies that multiple attached listeners receive the same emitted record."""
    emitter = TelemetryEmitter()
    first_received: list[Any] = []
    second_received: list[Any] = []

    emitter.register_listener(lambda r: first_received.append(r))
    emitter.register_listener(lambda r: second_received.append(r))
    emitter.emit('MOCK_RECORD_B')

    assert len(first_received) == 1
    assert first_received[0] == 'MOCK_RECORD_B'
    assert len(second_received) == 1
    assert second_received[0] == 'MOCK_RECORD_B'

# -----------------------------------------------------------------------------

def test_emitter_handles_emission_without_listeners() -> None:
    """Verifies that calling emit when no listeners are registered does not fail."""
    emitter = TelemetryEmitter()

    # Execution should pass seamlessly without raising exceptions or state errors
    emitter.emit('MOCK_RECORD_C')

# -----------------------------------------------------------------------------

def test_emitter_instances_are_isolated() -> None:
    """Verifies that broadcasting on one emitter does not cross into another."""
    emitter_one = TelemetryEmitter()
    emitter_two = TelemetryEmitter()
    received_records: list[Any] = []

    emitter_one.register_listener(lambda r: received_records.append(r))
    emitter_two.emit('MOCK_RECORD_D')

    assert len(received_records) == 0

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
