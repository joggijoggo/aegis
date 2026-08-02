"""Aegis Framework - Position Sizer.

Calculates standardized transaction contracts based on fixed account balance
risk parameters.
"""

import uuid
from decimal import Decimal, ROUND_DOWN

from core.currency_converter import CurrencyConverter
from core.exceptions import ContractVolumeUnderflowError
from core.models import (
    AccountSnapshot,
    ContractSpecification,
    ExposureIntent,
    MarketContext,
    Order,
    OrderSide,
    OrderType,
    TimeInForce,
)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class PositionSizer:
    """Generates executable transaction orders aligned with capital risk bounds."""

# -----------------------------------------------------------------------------

    def __init__(self, currency_converter: CurrencyConverter):
        """Initializes the position sizer.

        Args:
            currency_converter: Service executing currency exchange translations.
        """
        self._currency_converter = currency_converter

# -----------------------------------------------------------------------------

    def create_order(
        self,
        exposure_intent: ExposureIntent,
        risk_percent: Decimal,
        contract_specification: ContractSpecification,
        account_snapshot: AccountSnapshot,
        market_context: MarketContext,
    ) -> Order:
        """Creates an execution order sized to a specific balance risk percentage.

        Args:
            exposure_intent: Bot intent containing direction, take profit and
                stop loss ticks.
            risk_percent: Maximum fractional capital risk allowed per transaction.
            contract_specification: Microstructural parameters of the asset.
            account_snapshot: Current financial state providing account balance.
            market_context: Current market price information.
        """
        # 1. Determine execution side and entry price base with strict validation
        if exposure_intent.alpha_direction > Decimal('0'):
            side = OrderSide.BUY
            entry_price = Decimal(str(market_context.prices.ask))
            stop_modifier = Decimal('-1')
            profit_modifier = Decimal('1')
        elif exposure_intent.alpha_direction < Decimal('0'):
            side = OrderSide.SELL
            entry_price = Decimal(str(market_context.prices.bid))
            stop_modifier = Decimal('1')
            profit_modifier = Decimal('-1')
        else:
            raise NotImplementedError(
                'Position closure or neutral signals are not yet '
                f'implemented: {exposure_intent.alpha_direction}'
            )

        # 2. Derive monetary tick evaluation translated to account currency
        native_tick_value = (
            contract_specification.contract_multiplier
            * contract_specification.tick_size
        )
        account_tick_value = self._currency_converter.convert(
            amount=native_tick_value,
            from_currency=contract_specification.quote_currency,
            to_currency=account_snapshot.currency,
        )

        # 3. Apply sizing equations mapping cash risk limits to tick distances
        max_risk_amount = account_snapshot.balance * risk_percent
        risk_per_contract = (
            Decimal(str(exposure_intent.stop_loss_ticks))
            * account_tick_value
        )
        raw_quantity = max_risk_amount / risk_per_contract

        # 4. Enforce fractional discrete step routing boundaries
        step = contract_specification.contract_step
        quantized_quantity = (raw_quantity / step).quantize(
            Decimal('1'), rounding=ROUND_DOWN
        ) * step

        if quantized_quantity < contract_specification.min_contract_size:
            raise ContractVolumeUnderflowError(
                f'Calculated volume {quantized_quantity} violates broker '
                f'minimum threshold: {contract_specification.min_contract_size}'
            )

        # 5. Extract temporal tracking marker from snapshot coordinates
        execution_time = market_context.prices.timestamp

        # 6. Extrapolate target absolute protective boundaries from entry price
        tick_size = contract_specification.tick_size
        stop_loss_distance = (
            Decimal(str(exposure_intent.stop_loss_ticks)) * tick_size
        )
        take_profit_distance = (
            Decimal(str(exposure_intent.take_profit_ticks)) * tick_size
        )

        stop_loss_price = entry_price + (stop_modifier * stop_loss_distance)
        take_profit_price = (
            entry_price + (profit_modifier * take_profit_distance)
        )

        # 7. Generate a unique, deterministic internal tracking identifier
        epoch_timestamp = int(execution_time.timestamp())
        client_order_id = f'AEGIS-{epoch_timestamp}-{uuid.uuid4()}'

        return Order(
            client_order_id=client_order_id,
            timestamp=execution_time,
            symbol=contract_specification.symbol,
            side=side,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.GTC,
            quantity=quantized_quantity,
            price=None,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
        )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
