"""Aegis Framework - Saxo Bank Microstructural Specifications.

Stores hard-coded parameter rule variations for symbols mapping to Saxo Bank
execution environments.

WARNING: Saxo Bank uses fixed commission until a certain volume which then
switch to percent commission.
"""

from decimal import Decimal

from aegis.core.model.market import ContractSpecification

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

SAXO_BANK_SPECIFICATIONS: dict[str, ContractSpecification] = {
    "AUDJPY": ContractSpecification(
        symbol="AUDJPY",
        base_spread_ticks=Decimal("1.5"),
        contract_multiplier=Decimal("100000"),
        base_currency="AUD",
        quote_currency="JPY",
        contract_step=Decimal("0.01"),
        margin_requirement=Decimal("0.0500"),
        min_contract_size=Decimal("0.01"),
        tick_size=Decimal("0.01"),
    ),
    "AUDUSD": ContractSpecification(
        symbol="AUDUSD",
        base_spread_ticks=Decimal("0.7"),
        contract_multiplier=Decimal("100000"),
        base_currency="AUD",
        quote_currency="USD",
        contract_step=Decimal("0.01"),
        margin_requirement=Decimal("0.0500"),
        min_contract_size=Decimal("0.01"),
        tick_size=Decimal("0.00001"),
    ),
    "EURCHF": ContractSpecification(
        symbol="EURCHF",
        base_spread_ticks=Decimal("2.2"),
        contract_multiplier=Decimal("100000"),
        base_currency="EUR",
        quote_currency="CHF",
        contract_step=Decimal("0.01"),
        margin_requirement=Decimal("0.0500"),
        min_contract_size=Decimal("0.01"),
        tick_size=Decimal("0.00001"),
    ),
    "EURGBP": ContractSpecification(
        symbol="EURGBP",
        base_spread_ticks=Decimal("1.0"),
        contract_multiplier=Decimal("100000"),
        base_currency="EUR",
        quote_currency="GBP",
        contract_step=Decimal("0.01"),
        margin_requirement=Decimal("0.0333"),
        min_contract_size=Decimal("0.01"),
        tick_size=Decimal("0.00001"),
    ),
    "EURJPY": ContractSpecification(
        symbol="EURJPY",
        base_spread_ticks=Decimal("1.3"),
        contract_multiplier=Decimal("100000"),
        base_currency="EUR",
        quote_currency="JPY",
        contract_step=Decimal("0.01"),
        margin_requirement=Decimal("0.0333"),
        min_contract_size=Decimal("0.01"),
        tick_size=Decimal("0.01"),
    ),
    "EURUSD": ContractSpecification(
        symbol="EURUSD",
        base_spread_ticks=Decimal("0.7"),
        contract_multiplier=Decimal("100000"),
        base_currency="EUR",
        quote_currency="USD",
        contract_step=Decimal("0.01"),
        margin_requirement=Decimal("0.0333"),
        min_contract_size=Decimal("0.01"),
        tick_size=Decimal("0.00001"),
    ),
    "GBPJPY": ContractSpecification(
        symbol="GBPJPY",
        base_spread_ticks=Decimal("1.8"),
        contract_multiplier=Decimal("100000"),
        base_currency="GBP",
        quote_currency="JPY",
        contract_step=Decimal("0.01"),
        margin_requirement=Decimal("0.0333"),
        min_contract_size=Decimal("0.01"),
        tick_size=Decimal("0.01"),
    ),
    "GBPUSD": ContractSpecification(
        symbol="GBPUSD",
        base_spread_ticks=Decimal("1.0"),
        contract_multiplier=Decimal("100000"),
        base_currency="GBP",
        quote_currency="USD",
        contract_step=Decimal("0.01"),
        margin_requirement=Decimal("0.0333"),
        min_contract_size=Decimal("0.01"),
        tick_size=Decimal("0.00001"),
    ),
    "USDCAD": ContractSpecification(
        symbol="USDCAD",
        base_spread_ticks=Decimal("1.5"),
        contract_multiplier=Decimal("100000"),
        base_currency="USD",
        quote_currency="CAD",
        contract_step=Decimal("0.01"),
        margin_requirement=Decimal("0.0333"),
        min_contract_size=Decimal("0.01"),
        tick_size=Decimal("0.00001"),
    ),
    "USDCHF": ContractSpecification(
        symbol="USDCHF",
        base_spread_ticks=Decimal("1.1"),
        contract_multiplier=Decimal("100000"),
        base_currency="USD",
        quote_currency="CHF",
        contract_step=Decimal("0.01"),
        margin_requirement=Decimal("0.0333"),
        min_contract_size=Decimal("0.01"),
        tick_size=Decimal("0.00001"),
    ),
    "USDJPY": ContractSpecification(
        symbol="USDJPY",
        base_spread_ticks=Decimal("0.8"),
        contract_multiplier=Decimal("100000"),
        base_currency="USD",
        quote_currency="JPY",
        contract_step=Decimal("0.01"),
        margin_requirement=Decimal("0.0333"),
        min_contract_size=Decimal("0.01"),
        tick_size=Decimal("0.01"),
    ),
    "XAUUSD": ContractSpecification(
        symbol="XAUUSD",
        base_spread_ticks=Decimal("3.5"),
        contract_multiplier=Decimal("100"),
        base_currency="XAU",
        quote_currency="USD",
        contract_step=Decimal("0.01"),
        margin_requirement=Decimal("0.0500"),
        min_contract_size=Decimal("0.01"),
        tick_size=Decimal("0.01"),
    ),
}

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
