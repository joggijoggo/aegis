"""Aegis Framework - Portfolio Risk Manager Authority.

Implements secondary prudential filters enforcing drawdown fuses and margin checks.
"""

from core.models import OrderRequest
from core.models import RiskValidationResult
from core.registry import InstrumentRegistry

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class RiskManager:
    """Universal risk authority protecting portfolio equity against disasters."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        instrument_registry: InstrumentRegistry,
        max_drawdown_limit: float,
    ) -> None:
        """Initialize the risk controller with technical reference criteria.

        Args:
            instrument_registry: Central database containing contract constants.
            max_drawdown_limit: The maximum historical equity loss allowed in %.
        """
        self._instrument_registry = instrument_registry
        self._max_drawdown_limit = max_drawdown_limit

# -----------------------------------------------------------------------------

    def assess_order_risk(
        self,
        account_equity: float,
        volume_lots: float,
        current_price: float,
        available_liquidity: float,
        current_portfolio_drawdown: float,
        order_request: OrderRequest,
    ) -> RiskValidationResult:
        """Evaluate strategic portfolio safety metrics before execution routing.

        Args:
            account_equity: The current total net asset value of the portfolio.
            volume_lots: The final transaction size calculated by the sizer.
            current_price: The financial spot quote price of the asset.
            available_liquidity: The free margin capital left on the account.
            current_portfolio_drawdown: The current equity loss distance in %.
            order_request: The raw parameters of the trading request.

        Returns:
            The structured verdict containing the definitive risk clearance.
        """
        if current_portfolio_drawdown >= self._max_drawdown_limit:
            return RiskValidationResult(
                is_approved=False,
                calculated_volume_lots=0.0,
                rejection_reason="Maximum drawdown limit breached.",
            )

        spec = self._instrument_registry.get_specification(
            symbol=order_request.symbol,
        )

        nominal_exposure = volume_lots * spec.lot_size * current_price
        required_margin = nominal_exposure * spec.margin_requirement

        if required_margin > available_liquidity:
            return RiskValidationResult(
                is_approved=False,
                calculated_volume_lots=0.0,
                rejection_reason="Insufficient margin liquidity.",
            )

        return RiskValidationResult(
            is_approved=True,
            calculated_volume_lots=volume_lots,
            rejection_reason="",
        )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
