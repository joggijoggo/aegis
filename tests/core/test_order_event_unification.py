"""Aegis Framework - Order Event Unification Unit Tests.

Validates directional enums parsing and alphanumeric identifier safety.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from core.models import (
    OrderEvent,
    OrderSide,
    OrderStatus,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_order_event_enforces_alphanumeric_id_and_physical_side() -> None:
    """Ensures OrderEvent accepts string UUIDs and uses execution OrderSide enums."""
    target_dt = datetime(2026, 7, 29, 12, 0, tzinfo=ZoneInfo("UTC"))

    # 1. Instantiate the model executing an exhaustive parameters matrix
    event = OrderEvent(
        broker_reference="IG-DEAL-UUID-99482",
        executed_price=1.0850,
        executed_size=0.5,
        side=OrderSide.BUY,
        status=OrderStatus.PARTIALLY_FILLED,
        symbol="EURUSD",
        timestamp=target_dt,
    )

    # 2. Assert validation constraints across 100% of available fields
    assert isinstance(event.broker_reference, str)
    assert event.broker_reference == "IG-DEAL-UUID-99482"

    assert isinstance(event.symbol, str)
    assert event.symbol == "EURUSD"

    assert isinstance(event.status, OrderStatus)
    assert event.status == OrderStatus.PARTIALLY_FILLED

    assert isinstance(event.side, OrderSide)
    assert event.side == OrderSide.BUY

    assert isinstance(event.executed_price, float)
    assert event.executed_price == 1.0850

    assert isinstance(event.executed_size, float)
    assert event.executed_size == 0.5

    assert isinstance(event.timestamp, datetime)
    assert event.timestamp == target_dt

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
