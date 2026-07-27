"""Aegis Framework - Simulated Broker Adapter Layer.

Implements the outbound simulation adapter routing orders to the isolated ledger.
"""

import uuid
from typing import Any

from brokers.base_broker import AbstractBrokerBridge
from core.accounts import IsolatedAssetAccount
from core.models import OrderType
from core.models import TransactionSide

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class SimulatedBrokerAdapter(AbstractBrokerBridge):
    """Outbound adapter routing execution contracts to historical ledger nodes."""

# -----------------------------------------------------------------------------

    def __init__(self, target_account: IsolatedAssetAccount):
        """Initializes the simulation adapter anchored to a specific ledger account.

        Args:
            target_account (IsolatedAssetAccount): Target ledger workspace instance.
        """
        self.account = target_account

# -----------------------------------------------------------------------------

    def place_order(
        self,
        symbol: str,
        side: TransactionSide,
        order_type: OrderType,
        volume_lots: float,
        stop_loss_pips: float | None = None,
        take_profit_pips: float | None = None
    ) -> dict[str, Any]:
        """Routes an execution contract request to the target matching engine.

        Args:
            symbol (str): Target currency pair tracking identifier.
            side (TransactionSide): Enforced transaction direction enum.
            order_type (OrderType): Enforced execution constraint type enum.
            volume_lots (float): Lot size exposure allocation.
            stop_loss_pips (float | None): Optional protective stop distance.
            take_profit_pips (float | None): Optional target limit distance.

        Returns:
            dict[str, Any]: Standardized execution receipt parameters.
        """
        # Mapping the side enum value to historical string expected by Jalon 1 account
        self.account.open_mock_position(
            side=side.value,
            size_lots=volume_lots,
            entry_price=0.0
        )

        return {
            "transaction_id": str(uuid.uuid4()),
            "status": "FILLED",
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "volume_lots": volume_lots
        }

# -----------------------------------------------------------------------------

    def get_portfolio_snapshot(self) -> dict[str, Any]:
        """Fetches dynamic localized financial balances and open position nodes.

        Returns:
            dict[str, Any]: Structure mapping cash, equity, and active trades.
        """
        return {
            "balance": self.account.balance,
            "equity": self.account.equity,
            "positions": self.account.mock_positions
        }

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
