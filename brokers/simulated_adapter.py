"""Aegis Framework - Simulated Broker Adapter Layer.

Implements the outbound port adapter mimicking ledger execution transactions.
"""

from typing import Any

from brokers.base_broker import AbstractBrokerBridge
from core.accounts import IsolatedAssetAccount
from core.models import InstrumentSpecification
from core.models import OrderType
from core.models import TransactionSide
from core.registry import InstrumentRegistry

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class SimulatedBrokerAdapter(AbstractBrokerBridge):
    """Outbound adapter connecting strategies requests to virtual asset accounts."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        target_account: IsolatedAssetAccount,
        instrument_registry: InstrumentRegistry,
    ):
        """Initializes the structural adapter anchoring the target ledger account.

        Args:
            target_account (IsolatedAssetAccount): Virtual asset account node.
            instrument_registry (InstrumentRegistry): Enforced domain registry.
        """
        self.account = target_account
        self._instrument_registry = instrument_registry

# -----------------------------------------------------------------------------

    def place_order(
        self,
        symbol: str,
        side: TransactionSide,
        order_type: OrderType,
        volume_lots: float,
        stop_loss_price: float,
        take_profit_price: float,
    ) -> dict[str, Any]:
        """Routes transaction parameters records to the virtual isolated ledger.

        Args:
            symbol (str): Target currency pair symbol identifier.
            side (TransactionSide): Enforced execution direction enum.
            order_type (OrderType): Enforced execution constraint type enum.
            volume_lots (float): Lot size exposure parameter.
            stop_loss_price (float): Enforced absolute protection target marker.
            take_profit_price (float): Enforced absolute protection profit marker.

        Returns:
            dict[str, Any]: Execution parameters tracking mapping record.
        """
        self.account.mock_positions = {
            "symbol": symbol,
            "side": side.value,
            "size_lots": volume_lots,
        }
        return {"status": "SUBMITTED", "symbol": symbol}

# -----------------------------------------------------------------------------

    def get_portfolio_snapshot(self) -> dict[str, Any]:
        """Extracts dynamic ledger metrics maps parameters from virtual accounts.

        Returns:
            dict[str, Any]: Structure mapping balance and positions metrics records.
        """
        return {
            "balance": self.account.balance,
            "equity": self.account.equity,
            "positions": [self.account.mock_positions] if self.account.mock_positions else [],
        }

# -----------------------------------------------------------------------------

    def get_instrument_specification(self, symbol: str) -> InstrumentSpecification:
        """Fetches contract specifications from the central domain registry.

        Args:
            symbol (str): Target financial asset symbol tracking identifier.

        Returns:
            InstrumentSpecification: Typed immutable contract specifications.
        """
        return self._instrument_registry.get_specification(symbol=symbol)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
