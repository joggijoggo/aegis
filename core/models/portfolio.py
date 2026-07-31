"""Aegis Framework - Account Balances and Ledger Assets.

Tracks financial capital risk snapshots, clearing fees, and margin validation metrics
requiring decimal accuracy.
"""

from dataclasses import dataclass
from decimal import Decimal

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

@dataclass(frozen=True)
class AccountSnapshot:
    """Financial metrics of the trading account.

    Attributes:
        currency: Base denomination currency unit of the trading
            account ledger (e.g., "EUR").
        balance: Account cash excluding open positions.
        equity: Account cash including unrealized profits and losses.
        available_margin: Account cash excluding locked position margin.
    """
    currency: str
    balance: Decimal
    equity: Decimal
    available_margin: Decimal

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
