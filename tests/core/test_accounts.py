"""Aegis Framework - Isolated Ledger Account Unit Tests.

Enforces TDD validation protocols onto the Tom-Next overnight financing layers
and triple Wednesday multiplier mechanics.
"""

from datetime import datetime

from zoneinfo import ZoneInfo

from core.accounts import IsolatedAssetAccount
from core.models import MarketPricePoint

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_overnight_financing_standard_day():
    """Validates single-day Tom-Next debit application on standard nights."""
    account = IsolatedAssetAccount(
        asset_pair='EURUSD',
        initial_capital=10000.0
    )

    # 1. Open a virtual long position of 1.0 standard lot at 22:00 London
    t_tuesday = datetime(2026, 3, 24, 22, 0, tzinfo=ZoneInfo('Europe/London'))
    price_snapshot = MarketPricePoint(
        timestamp=t_tuesday,
        mid_price=1.0800,
        bid=1.0797,
        ask=1.0803,
        current_atr=0.0010
    )

    account.open_mock_position(
        side='LONG',
        size_lots=1.0,
        entry_price=1.0803
    )

    # 2. Execute ledger bar routing to trigger potential financing settlements
    account.process_market_bar(
        high_price=1.0810,
        low_price=1.0790,
        price_snapshot=price_snapshot
    )

    assert account.balance < 10000.0

# -----------------------------------------------------------------------------

def test_overnight_financing_triple_wednesday():
    """Validates the institutional 3x multiplier markup on Wednesday nights."""
    account_standard = IsolatedAssetAccount(
        asset_pair='EURUSD',
        initial_capital=10000.0
    )
    account_wednesday = IsolatedAssetAccount(
        asset_pair='EURUSD',
        initial_capital=10000.0
    )

    account_standard.open_mock_position(
        side='LONG',
        size_lots=1.0,
        entry_price=1.0800
    )
    account_wednesday.open_mock_position(
        side='LONG',
        size_lots=1.0,
        entry_price=1.0800
    )

    # Run Standard Night (Tuesday to Wednesday)
    t_tuesday = datetime(2026, 3, 24, 22, 0, tzinfo=ZoneInfo('Europe/London'))
    p_tuesday = MarketPricePoint(
        timestamp=t_tuesday,
        mid_price=1.0800,
        bid=1.0797,
        ask=1.0803,
        current_atr=0.0
    )
    account_standard.process_market_bar(1.0810, 1.0790, p_tuesday)

    # Run Triple Night (Wednesday to Thursday)
    t_wednesday = datetime(2026, 3, 25, 22, 0, tzinfo=ZoneInfo('Europe/London'))
    p_wednesday = MarketPricePoint(
        timestamp=t_wednesday,
        mid_price=1.0800,
        bid=1.0797,
        ask=1.0803,
        current_atr=0.0
    )
    account_wednesday.process_market_bar(1.0810, 1.0790, p_wednesday)

    fee_standard = 10000.0 - account_standard.balance
    fee_wednesday = 10000.0 - account_wednesday.balance

    assert round(fee_wednesday, 4) == round(fee_standard * 3.0, 4)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
