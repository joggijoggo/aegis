from decimal import Decimal
from core.models import OrderRequest
from core.models import RiskValidationResult
from core.registry import InstrumentRegistry

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class PositionSizer:
    """Universal sizing calculator bound by contract parameters and risk scores."""

# -----------------------------------------------------------------------------

    def __init__(self, instrument_registry: InstrumentRegistry) -> None:
        """Initialize the positioning engine with the global specifications mapping.

        Args:
            instrument_registry: Central database containing contract constants.
        """
        self._instrument_registry = instrument_registry

# -----------------------------------------------------------------------------

    def compute_volume(
        self,
        account_equity: float,
        order_request: OrderRequest,
    ) -> RiskValidationResult:
        """Calculate the optimized trading size using the calibrated risk equation.

        Formula:
            Lots = (Equity * Risk% * Confidence) / (StopLossTicks * TickLoss)

        Args:
            account_equity: The current total net asset value of the portfolio.
            order_request: The raw parameters of the trading request.

        Returns:
            The structured verdict containing the final calculated size.
        """
        if order_request.risk_percentage < 0.0 or order_request.confidence_factor < 0.0:
            return RiskValidationResult(False, 0.0, "Risk parameters cannot be negative.")

        if order_request.confidence_factor > 1.0:
            return RiskValidationResult(
                is_approved=False,
                calculated_volume_lots=0.0,
                rejection_reason=(
                    "Confidence factor cannot amplify "
                    "maximum risk parameters."
                ),
            )

        spec = self._instrument_registry.get_specification(symbol=order_request.symbol)

        # Cast raw floats to string-based exact decimal instances
        equity_dec = Decimal(str(account_equity))
        risk_pct_dec = Decimal(str(order_request.risk_percentage))
        confidence_dec = Decimal(str(order_request.confidence_factor))
        stop_ticks_dec = Decimal(str(order_request.stop_loss_ticks))

        tick_size_dec = Decimal(str(spec.tick_size))
        lot_size_dec = Decimal(str(spec.lot_size))
        lot_step_dec = Decimal(str(spec.lot_step))
        min_lot_dec = Decimal(str(spec.min_lot))

        # Compute monetary risk budget allowed via high-precision math
        risk_fraction = risk_pct_dec / Decimal("100.0")
        risk_budget = equity_dec * risk_fraction * confidence_dec

        # Compute accurate total loss per lot unit profile
        tick_loss_per_lot = tick_size_dec * lot_size_dec
        total_loss_per_lot = stop_ticks_dec * tick_loss_per_lot

        if total_loss_per_lot <= Decimal("0.0"):
            return RiskValidationResult(
                is_approved=False,
                calculated_volume_lots=0.0,
                rejection_reason="Invalid risk or stop loss distance specification.",
            )

        # Derive raw volume and apply strict base-10 floor truncation
        raw_volume = risk_budget / total_loss_per_lot
        truncated_volume = (raw_volume // lot_step_dec) * lot_step_dec

        # Cast back to standard float signature after exact calculations
        final_volume = float(truncated_volume)

        if final_volume < float(min_lot_dec):
            return RiskValidationResult(
                is_approved=False,
                calculated_volume_lots=0.0,
                rejection_reason="Calculated volume is below minimum contract size.",
            )

        return RiskValidationResult(True, final_volume, "")

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
