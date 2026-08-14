"""Aegis Framework - Position Sizer Unit Tests.

Verifies mathematical risk-based volume scaling, multi-currency conversion,
and contract volume underflow exception routing.
"""

from decimal import Decimal

import pytest

from aegis.core.currency_converter import CurrencyConverter
from aegis.core.exception import ContractVolumeUnderflowError
from aegis.core.model import (
    ExposureIntent,
    OrderSide,
    OrderType,
    TimeInForce,
)
from aegis.core.position_sizer import PositionSizer
from tests.testutil import (
    create_account_snapshot_factory,
    create_contract_specification_factory,
    create_market_context_factory,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_sizer_calculates_exact_volume_for_short_execution(currency_converter) -> None:
    """Ensures contract volumes and prices map correctly for sell short trades."""
    sizer = PositionSizer(currency_converter=currency_converter)
    spec = create_contract_specification_factory()
    intent = ExposureIntent(
        alpha_direction=Decimal('-1.0'),
        stop_loss_ticks=500,
        take_profit_ticks=1000,
    )
    snapshot = create_account_snapshot_factory(currency='USD')
    context = create_market_context_factory()

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
    assert order.stop_loss_price == Decimal('1.08990')
    assert order.take_profit_price == Decimal('1.07490')

# -----------------------------------------------------------------------------

def test_sizer_ignore_take_profit_when_none(currency_converter) -> None:
    """Verifies that take_profit_price is None when exposure has no TP."""
    sizer = PositionSizer(currency_converter=currency_converter)
    spec = create_contract_specification_factory()
    intent = ExposureIntent(
        alpha_direction=Decimal('-1.0'),
        stop_loss_ticks=500,
        take_profit_ticks=None,
    )
    snapshot = create_account_snapshot_factory(currency='USD')
    context = create_market_context_factory()

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
    assert order.stop_loss_price == Decimal('1.08990')
    assert order.take_profit_price is None

# -----------------------------------------------------------------------------

def test_sizer_calculates_exact_volume_on_native_currency_match(
    currency_converter,
) -> None:
    """Ensures contract volumes map directly when no conversion is required."""
    sizer = PositionSizer(currency_converter=currency_converter)
    spec = create_contract_specification_factory()
    intent = ExposureIntent(
        alpha_direction=Decimal('1.0'),
        stop_loss_ticks=500,
        take_profit_ticks=1000,
    )
    snapshot = create_account_snapshot_factory(currency='USD')
    context = create_market_context_factory()

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
    assert order.time_in_force == TimeInForce.GTC
    assert order.stop_loss_price == Decimal('1.08010')
    assert order.take_profit_price == Decimal('1.09510')

# -----------------------------------------------------------------------------

def test_sizer_calculates_volume_with_cross_currency_translation() -> None:
    """Ensures cross currency conversions are integrated prior to sizing."""
    converter = CurrencyConverter()
    converter.update_rate(pair='EURUSD', rate=Decimal('1.0850'))
    sizer = PositionSizer(currency_converter=converter)

    spec = create_contract_specification_factory()
    intent = ExposureIntent(
        alpha_direction=Decimal('1.0'),
        stop_loss_ticks=500,
        take_profit_ticks=1000,
    )
    snapshot = create_account_snapshot_factory(currency='EUR')
    context = create_market_context_factory()

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
    assert order.time_in_force == TimeInForce.GTC
    assert order.stop_loss_price == Decimal('1.08010')
    assert order.take_profit_price == Decimal('1.09510')

# -----------------------------------------------------------------------------

def test_sizer_calculates_volume_with_tri_currency_cross_rates() -> None:
    """Ensures raw asset pricing is translated to account currency layers."""
    converter = CurrencyConverter()
    converter.update_rate(pair='EURJPY', rate=Decimal('165.00'))
    sizer = PositionSizer(currency_converter=converter)

    spec = create_contract_specification_factory(
        symbol='AUDJPY',
        contract_multiplier=Decimal('10'),
        contract_step=Decimal('1.0'),
        min_contract_size=Decimal('1.0'),
        tick_size=Decimal('0.01'),
        quote_currency='JPY',
    )
    intent = ExposureIntent(
        alpha_direction=Decimal('1.0'),
        stop_loss_ticks=500,
        take_profit_ticks=1000,
    )
    snapshot = create_account_snapshot_factory(currency='EUR')
    context = create_market_context_factory(
        mid_price=98.50,
        bid=98.49,
        ask=98.51,
    )

    order = sizer.create_order(
        exposure_intent=intent,
        risk_percent=Decimal('0.01'),
        contract_specification=spec,
        account_snapshot=snapshot,
        market_context=context,
    )

    assert order.symbol == 'AUDJPY'
    assert order.quantity == Decimal('330.0')
    assert order.side == OrderSide.BUY
    assert order.stop_loss_price == Decimal('93.51')
    assert order.take_profit_price == Decimal('108.51')

# -----------------------------------------------------------------------------

def test_sizer_raises_contract_volume_underflow_error(currency_converter) -> None:
    """Ensures sub-minimum fractional calculations trigger domain alerts."""
    sizer = PositionSizer(currency_converter=currency_converter)
    spec = create_contract_specification_factory()
    intent = ExposureIntent(
        alpha_direction=Decimal('1.0'),
        stop_loss_ticks=500,
        take_profit_ticks=1000,
    )
    snapshot = create_account_snapshot_factory(
        balance=Decimal('1000.00'),
        currency='USD',
    )
    context = create_market_context_factory()

    with pytest.raises(ContractVolumeUnderflowError):
        sizer.create_order(
            exposure_intent=intent,
            risk_percent=Decimal('0.01'),
            contract_specification=spec,
            account_snapshot=snapshot,
            market_context=context,
        )

# -----------------------------------------------------------------------------

def test_sizer_raises_not_implemented_error_for_neutral_alpha(currency_converter) -> None:
    """Ensures unhandled neutral or closure alpha signals throw exceptions."""
    sizer = PositionSizer(currency_converter=currency_converter)
    spec = create_contract_specification_factory()
    intent = ExposureIntent(
        alpha_direction=Decimal('0.0'),
        stop_loss_ticks=None,
        take_profit_ticks=None,
    )
    snapshot = create_account_snapshot_factory(currency='USD')
    context = create_market_context_factory()

    with pytest.raises(NotImplementedError):
        sizer.create_order(
            exposure_intent=intent,
            risk_percent=Decimal('0.01'),
            contract_specification=spec,
            account_snapshot=snapshot,
            market_context=context,
        )

# -----------------------------------------------------------------------------

def test_sizer_raises_value_error_for_neutral_alpha(currency_converter) -> None:
    """Ensure neutral alpha direction throw exception."""
    sizer = PositionSizer(currency_converter=currency_converter)
    spec = create_contract_specification_factory()
    intent = ExposureIntent(alpha_direction=None,)
    snapshot = create_account_snapshot_factory(currency='USD')
    context = create_market_context_factory()

    with pytest.raises(ValueError):
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
