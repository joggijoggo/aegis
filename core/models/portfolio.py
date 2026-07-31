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

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class ContractSpecification:
    """Microstructural parameter specification for trading contracts.

    Attributes:
        symbol: Unique financial instrument market identifier.
            Example: 'EURUSD' or 'IX.D.DOW.IFS.IP'.
        base_spread_ticks: Minimum structural transaction cost in ticks.
            Example: 2.0 for a two-tick spread.
        contract_multiplier: Leverage scaling factor linking price to nominal values.
            Example: 100000 for Forex, 1 for indices.
        base_currency: Native currency unit of the underlying contract.
            Example: "EUR" for EURUSD, "USD" for Wall Street index.
        quote_currency: Currency unit denominating the transaction price.
            Example: "USD" for EURUSD, "EUR" for France 40 index.
        contract_step: Minimum fractional volume increment permitted for orders.
            Example: 0.01 for Forex, 0.1 for indices.
        margin_requirement: Percentage of total exposure required as safety collateral.
            Example: 0.0333 for a thirty-to-one leverage ratio.
        min_contract_size: Absolute minimum volume threshold accepted for execution.
            Example: 0.1 for micro-contracts.
        tick_size: Minimum incremental fraction of price movement.
            Example: 0.00001 for EURUSD, 1.0 for Dow Jones.
    """
    symbol: str
    base_spread_ticks: Decimal
    contract_multiplier: Decimal
    base_currency: str
    quote_currency: str
    contract_step: Decimal
    margin_requirement: Decimal
    min_contract_size: Decimal
    tick_size: Decimal

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
