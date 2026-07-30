"""Aegis Framework - Position Sizer Unit Tests.

Verifies mathematical risk-based volume scaling, multi-currency conversion,
and contract volume underflow exception routing.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from core.currency_converter import CurrencyConverter
from core.exceptions import ContractVolumeUnderflowError
from core.models import (
    AccountSnapshot,
    ContractSpecification,
    ExposureIntent,
    MarketContext,
    MarketPricePoint,
    OrderSide,
    OrderType,
    TimeInForce,
)
from core.position_sizer import PositionSizer

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_sizer_calculates_exact_volume_for_short_execution() -> None:
    """Ensures contract volumes and prices map correctly for sell short trades."""
    converter = CurrencyConverter()
    sizer = PositionSizer(currency_converter=converter)

    spec = ContractSpecification(
        symbol='EURUSD',
        base_spread_ticks=Decimal('2.0'),
        contract_multiplier=Decimal('100000'),
        base_currency='EUR',
        quote_currency='USD',
        contract_step=Decimal('0.01'),
        margin_requirement=Decimal('0.0333'),
        min_contract_size=Decimal('0.1'),
        tick_size=Decimal('0.00001'),
    )

    intent = ExposureIntent(
        alpha_direction=Decimal('-1.0'),
        stop_loss_ticks=500,
        take_profit_ticks=1000,
    )

    snapshot = AccountSnapshot(
        balance=Decimal('10000.00'),
        equity=Decimal('10000.00'),
        available_margin=Decimal('10000.00'),
        currency='USD',
    )

    prices = MarketPricePoint(
        timestamp=datetime.now(timezone.utc),
        mid_price=1.08501,
        bid=1.08500,
        ask=1.08502,
        current_atr=0.0015,
    )

    context = MarketContext(prices=prices)

    order = sizer.create_order(
        exposure_intent=intent,
        risk_percent=Decimal('0.01'),
        contract_specification=spec,
        account_snapshot=snapshot,
        market_context=context,
    )

    assert order.symbol == 'EURUSD'
    assert order.quantity == Decimal('0.20')
    assert order.side == OrderSide.SELL
    assert order.stop_loss_price == Decimal('1.09000')
    assert order.take_profit_price == Decimal('1.07500')

# -----------------------------------------------------------------------------

def test_sizer_calculates_exact_volume_on_native_currency_match() -> None:
    """Ensures contract volumes map directly when no conversion is required."""
    converter = CurrencyConverter()
    sizer = PositionSizer(currency_converter=converter)

    spec = ContractSpecification(
        symbol='EURUSD',
        base_spread_ticks=Decimal('2.0'),
        contract_multiplier=Decimal('100000'),
        base_currency='EUR',
        quote_currency='USD',
        contract_step=Decimal('0.01'),
        margin_requirement=Decimal('0.0333'),
        min_contract_size=Decimal('0.1'),
        tick_size=Decimal('0.00001'),
    )

    intent = ExposureIntent(
        alpha_direction=Decimal('1.0'),
        stop_loss_ticks=500,
        take_profit_ticks=1000,
    )

    snapshot = AccountSnapshot(
        balance=Decimal('10000.00'),
        equity=Decimal('10000.00'),
        available_margin=Decimal('10000.00'),
        currency='USD',
    )

    prices = MarketPricePoint(
        timestamp=datetime.now(timezone.utc),
        mid_price=1.08501,
        bid=1.08500,
        ask=1.08502,
        current_atr=0.0015,
    )

    context = MarketContext(prices=prices)

    order = sizer.create_order(
        exposure_intent=intent,
        risk_percent=Decimal('0.01'),
        contract_specification=spec,
        account_snapshot=snapshot,
        market_context=context,
    )

    assert order.symbol == 'EURUSD'
    assert order.quantity == Decimal('0.20')
    assert order.side == OrderSide.BUY
    assert order.order_type == OrderType.MARKET
    assert order.time_in_force == TimeInForce.DAY
    assert order.stop_loss_price == Decimal('1.08002')
    assert order.take_profit_price == Decimal('1.09502')

# -----------------------------------------------------------------------------

def test_sizer_calculates_volume_with_cross_currency_translation() -> None:
    """Ensures cross currency conversions are integrated prior to sizing."""
    converter = CurrencyConverter()
    converter.update_rate(pair='EURUSD', rate=Decimal('1.0850'))
    sizer = PositionSizer(currency_converter=converter)

    spec = ContractSpecification(
        symbol='EURUSD',
        base_spread_ticks=Decimal('2.0'),
        contract_multiplier=Decimal('100000'),
        base_currency='EUR',
        quote_currency='USD',
        contract_step=Decimal('0.01'),
        margin_requirement=Decimal('0.0333'),
        min_contract_size=Decimal('0.1'),
        tick_size=Decimal('0.00001'),
    )

    intent = ExposureIntent(
        alpha_direction=Decimal('1.0'),
        stop_loss_ticks=500,
        take_profit_ticks=1000,
    )

    snapshot = AccountSnapshot(
        balance=Decimal('10000.00'),
        equity=Decimal('10000.00'),
        available_margin=Decimal('10000.00'),
        currency='EUR',
    )

    prices = MarketPricePoint(
        timestamp=datetime.now(timezone.utc),
        mid_price=1.08501,
        bid=1.08500,
        ask=1.08502,
        current_atr=0.0015,
    )

    context = MarketContext(prices=prices)

    order = sizer.create_order(
        exposure_intent=intent,
        risk_percent=Decimal('0.01'),
        contract_specification=spec,
        account_snapshot=snapshot,
        market_context=context,
    )

    assert order.symbol == 'EURUSD'
    assert order.quantity == Decimal('0.21')
    assert order.side == OrderSide.BUY
    assert order.order_type == OrderType.MARKET
    assert order.time_in_force == TimeInForce.DAY
    assert order.stop_loss_price == Decimal('1.08002')
    assert order.take_profit_price == Decimal('1.09502')

# -----------------------------------------------------------------------------

def test_sizer_calculates_volume_with_tri_currency_cross_rates() -> None:
    """Ensures raw asset pricing is translated to account currency layers."""
    converter = CurrencyConverter()
    converter.update_rate(pair='EURJPY', rate=Decimal('165.00'))
    sizer = PositionSizer(currency_converter=converter)

    spec = ContractSpecification(
        symbol='AUDJPY',
        base_spread_ticks=Decimal('1.5'),
        contract_multiplier=Decimal('10'),
        base_currency='AUD',
        quote_currency='JPY',
        contract_step=Decimal('1.0'),
        margin_requirement=Decimal('0.05'),
        min_contract_size=Decimal('1.0'),
        tick_size=Decimal('0.01'),
    )

    intent = ExposureIntent(
        alpha_direction=Decimal('1.0'),
        stop_loss_ticks=500,
        take_profit_ticks=1000,
    )

    snapshot = AccountSnapshot(
        balance=Decimal('10000.00'),
        equity=Decimal('10000.00'),
        available_margin=Decimal('10000.00'),
        currency='EUR',
    )

    prices = MarketPricePoint(
        timestamp=datetime.now(timezone.utc),
        mid_price=98.50,
        bid=98.49,
        ask=98.51,
        current_atr=0.45,
    )

    context = MarketContext(prices=prices)

    order = sizer.create_order(
        exposure_intent=intent,
        risk_percent=Decimal('0.01'),
        contract_specification=spec,
        account_snapshot=snapshot,
        market_context=context,
    )

    # Ask = 98.51
    # Stop = 98.51 - (500 * 0.01) = 93.51
    # Target = 98.51 + (1000 * 0.01) = 108.51
    assert order.symbol == 'AUDJPY'
    assert order.quantity == Decimal('330.0')
    assert order.side == OrderSide.BUY
    assert order.stop_loss_price == Decimal('93.51')
    assert order.take_profit_price == Decimal('108.51')

# -----------------------------------------------------------------------------

def test_sizer_raises_contract_volume_underflow_error() -> None:
    """Ensures sub-minimum fractional calculations trigger domain alerts."""
    converter = CurrencyConverter()
    sizer = PositionSizer(currency_converter=converter)

    spec = ContractSpecification(
        symbol='EURUSD',
        base_spread_ticks=Decimal('2.0'),
        contract_multiplier=Decimal('100000'),
        base_currency='EUR',
        quote_currency='USD',
        contract_step=Decimal('0.01'),
        margin_requirement=Decimal('0.0333'),
        min_contract_size=Decimal('0.1'),
        tick_size=Decimal('0.00001'),
    )

    intent = ExposureIntent(
        alpha_direction=Decimal('1.0'),
        stop_loss_ticks=500,
        take_profit_ticks=1000,
    )

    snapshot = AccountSnapshot(
        balance=Decimal('1000.00'),
        equity=Decimal('1000.00'),
        available_margin=Decimal('1000.00'),
        currency='USD',
    )

    prices = MarketPricePoint(
        timestamp=datetime.now(timezone.utc),
        mid_price=1.08501,
        bid=1.08500,
        ask=1.08502,
        current_atr=0.0015,
    )

    context = MarketContext(prices=prices)

    with pytest.raises(ContractVolumeUnderflowError):
        sizer.create_order(
            exposure_intent=intent,
            risk_percent=Decimal('0.01'),
            contract_specification=spec,
            account_snapshot=snapshot,
            market_context=context,
        )

# -----------------------------------------------------------------------------

def test_sizer_raises_not_implemented_error_for_neutral_alpha() -> None:
    """Ensures unhandled neutral or closure alpha signals throw exceptions."""
    converter = CurrencyConverter()
    sizer = PositionSizer(currency_converter=converter)

    spec = ContractSpecification(
        symbol='EURUSD',
        base_spread_ticks=Decimal('2.0'),
        contract_multiplier=Decimal('100000'),
        base_currency='EUR',
        quote_currency='USD',
        contract_step=Decimal('0.01'),
        margin_requirement=Decimal('0.0333'),
        min_contract_size=Decimal('0.1'),
        tick_size=Decimal('0.00001'),
    )

    intent = ExposureIntent(
        alpha_direction=Decimal('0.0'),
        stop_loss_ticks=500,
        take_profit_ticks=1000,
    )

    snapshot = AccountSnapshot(
        balance=Decimal('10000.00'),
        equity=Decimal('10000.00'),
        available_margin=Decimal('10000.00'),
        currency='USD',
    )

    prices = MarketPricePoint(
        timestamp=datetime.now(timezone.utc),
        mid_price=1.08501,
        bid=1.08500,
        ask=1.08502,
        current_atr=0.0015,
    )

    context = MarketContext(prices=prices)

    with pytest.raises(NotImplementedError):
        sizer.create_order(
            exposure_intent=intent,
            risk_percent=Decimal('0.01'),
            contract_specification=spec,
            account_snapshot=snapshot,
            market_context=context,
        )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
