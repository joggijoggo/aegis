"""Aegis Framework - Broker Port Interface Unit Tests.

Validates compile-time type safety and enforcement of contract compliance.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from brokers.base_broker import AbstractBrokerBridge
from core.models import (
    InstrumentSpecification,
    OrderReceipt,
    OrderSide,
    OrderType,
    PortfolioSnapshot,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class DummyBrokerAdapter(AbstractBrokerBridge):
    """Concrete mock adapter to validate abstract port contract enforcement."""

# -----------------------------------------------------------------------------

    def get_instrument_specification(self, symbol: str) -> InstrumentSpecification:
        """Fetch mock instrument contract specs mimicking the contract."""
        return InstrumentSpecification(
            base_spread_ticks=1.0,
            lot_size=100000,
            lot_step=0.1,
            margin_requirement=0.05,
            min_lot=0.1,
            tick_size=0.0001,
            volatility_factor=2.0,
        )

# -----------------------------------------------------------------------------

    def get_portfolio_snapshot(self) -> PortfolioSnapshot:
        """Fetch mock account parameters mimicking the contract."""
        return PortfolioSnapshot(
            account_id="IG-ACCOUNT-001",
            raw_balance=100000.0,
            raw_margin_allocated=5000.0,
            raw_unrealized_pnl=2500.0,
            timestamp=datetime(2026, 7, 29, 12, 0, tzinfo=ZoneInfo("UTC")),
        )

# -----------------------------------------------------------------------------

    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        volume_lots: float,
        stop_loss_price: float,
        take_profit_price: float,
    ) -> OrderReceipt:
        """Route mock execution payloads mimicking the contract."""
        return OrderReceipt(
            broker_reference="deal_ref_ig_99482",
            client_order_id="AEGIS-ORD-001",
            timestamp=datetime(2026, 7, 29, 12, 0, tzinfo=ZoneInfo("UTC")),
        )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_abstract_broker_bridge_cannot_be_instantiated_directly() -> None:
    """Ensures AbstractBrokerBridge throws standard TypeError if instantiated directly."""
    with pytest.raises(TypeError):
        AbstractBrokerBridge()  # type: ignore

# -----------------------------------------------------------------------------

def test_abstract_broker_bridge_contract_enforcement() -> None:
    """Ensures the concrete adapter complies perfectly with typed interface signatures."""
    adapter = DummyBrokerAdapter()

    # 1. Validate portfolio snapshot interface compliance and DTO field values
    snapshot = adapter.get_portfolio_snapshot()
    assert isinstance(snapshot, PortfolioSnapshot)
    assert snapshot.account_id == "IG-ACCOUNT-001"
    assert snapshot.raw_balance == 100000.0
    assert snapshot.raw_margin_allocated == 5000.0
    assert snapshot.raw_unrealized_pnl == 2500.0

    # 2. Validate order placement routing signatures and asynchronous identifiers
    receipt = adapter.place_order(
        symbol="EURUSD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        volume_lots=1.5,
        stop_loss_price=1.0800,
        take_profit_price=1.0950,
    )
    assert isinstance(receipt, OrderReceipt)
    assert receipt.broker_reference == "deal_ref_ig_99482"
    assert receipt.client_order_id == "AEGIS-ORD-001"

    # 3. Validate static contract configuration lookups
    spec = adapter.get_instrument_specification("EURUSD")
    assert isinstance(spec, InstrumentSpecification)
    assert spec.tick_size == 0.0001

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
