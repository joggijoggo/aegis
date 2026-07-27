"""Aegis Framework - Isolated Asset Accounts Ledger.

Tracks cash balances, floating equity metrics, and maintains historic closed
transaction records for a single currency pair node.
"""

from typing import Any
from zoneinfo import ZoneInfo

from core.models import MarketPricePoint

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class IsolatedAssetAccount:
    """Isolated financial ledger node tracking a single asset pair workspace."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        asset_pair: str,
        initial_capital: float
    ):
        """Initializes the isolated ledger cache tracking bounds.

        Args:
            asset_pair (str): Target currency pair symbol identifier.
            initial_capital (float): Starting cash allocation size.
        """
        self.asset_pair = asset_pair
        self.balance = initial_capital
        self.equity = initial_capital
        self.closed_trades_history: list[dict[str, Any]] = []
        self.london_tz = ZoneInfo('Europe/London')
        self.mock_positions: list[dict[str, Any]] = []

# -----------------------------------------------------------------------------

    def open_mock_position(
        self,
        side: str,
        size_lots: float,
        entry_price: float
    ) -> None:
        """Injects a simplified position shell to validate financing mechanics.

        Args:
            side (str): Transaction direction ('LONG' or 'SHORT').
            size_lots (float): Core lot size volume.
            entry_price (float): Terminal entry price execution level.
        """
        self.mock_positions.append({
            'side': side,
            'size_lots': size_lots,
            'entry_price': entry_price
        })

# -----------------------------------------------------------------------------

    def process_market_bar(
        self,
        high_price: float,
        low_price: float,
        price_snapshot: MarketPricePoint
    ) -> None:
        """Evaluates active portfolio nodes and applies Tom-Next interest swaps.

        Args:
            high_price (float): Maximum price recorded in the current bar.
            low_price (float): Minimum price recorded in the current bar.
            price_snapshot (MarketPricePoint): Current dynamic price parameters.
        """
        london_time = price_snapshot.timestamp.astimezone(self.london_tz)

        # Intercept the official 22:00 London interbank cutoff milestone
        if london_time.hour == 22 and london_time.minute == 0:
            # Enforce 3x weight multiplier covering weekend clearing on Wednesdays
            days_weight = 3 if london_time.weekday() == 2 else 1

            for pos in self.mock_positions:
                # Standard FX Lot size definition maps to 100,000 units
                notional_exposure = (
                    pos['size_lots'] * 100000 * price_snapshot.mid_price
                )

                # Apply hardcoded proxy interest differential markup matching IG rules
                annual_swap_rate = -0.055 if pos['side'] == 'LONG' else 0.045

                # Dynamic interest formula mapped to money market conventions
                funding_fee = (
                    notional_exposure * (annual_swap_rate / 360) * days_weight
                )
                self.balance += funding_fee

        self.equity = self.balance

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
