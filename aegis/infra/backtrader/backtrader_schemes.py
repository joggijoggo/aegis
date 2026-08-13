"""Aegis Framework - Backtrader Custom Commission Schemes.

Provides explicit leverage, margin, and contract multiplier configurations
matching specific brokerage account rule sets.
"""

import backtrader as bt

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class FutureFixedMarginScheme(bt.CommissionInfo):
    """Explicit Future scheme: fixed margin lot requirement with daily
    mark-to-market.
    """

    params = (
        ('commission', 0.0),
        ('mult', 1.0),
        ('margin', 50.0),
        ('commtype', bt.CommInfoBase.COMM_FIXED),
        ('stocklike', False),
        ('leverage', 1.0),
        ('automargin', False),
        ('interest', 0.0),
        ('interest_long', False),
    )

    def __init__(self, margin: float = 50.0, mult: float = 1.0) -> None:
        """Initializes the fixed margin scheme from contract parameters."""
        super().__init__()
        # pylint: disable=no-member
        self.p.margin = margin
        self.p.mult = mult

# -----------------------------------------------------------------------------

class SpotStockCashScheme(bt.CommissionInfo):
    """Explicit Spot Cash asset scheme requiring full payment upfront
    (No Margin).
    """

    params = (
        ('commission', 0.0),
        ('mult', 1.0),
        ('margin', 0.0),
        ('commtype', bt.CommInfoBase.COMM_PERC),
        ('stocklike', True),
        ('leverage', 1.0),
        ('automargin', False),
        ('interest', 0.0),
        ('interest_long', False),
    )

    def __init__(self, mult: float = 1.0) -> None:
        """Initializes the spot cash scheme from contract parameters."""
        super().__init__()
        # pylint: disable=no-member
        self.p.mult = mult

# -----------------------------------------------------------------------------

class ForexFixedMarginScheme(bt.CommissionInfo):
    """Explicit Forex margin scheme with static lot requirements and virtual
    floating PnL.
    """

    params = (
        ('commission', 0.0),
        ('mult', 1.0),
        ('margin', 50.0),
        ('commtype', bt.CommInfoBase.COMM_FIXED),
        ('stocklike', True),
        ('leverage', 1.0),
        ('automargin', False),
        ('interest', 0.0),
        ('interest_long', False),
    )

    def __init__(self, margin: float = 50.0, mult: float = 1.0) -> None:
        """Initializes the forex fixed margin scheme from contract parameters."""
        super().__init__()
        # pylint: disable=no-member
        self.p.margin = margin
        self.p.mult = mult

# -----------------------------------------------------------------------------

class ForexDynamicLeverageScheme(bt.CommissionInfo):
    """Explicit Forex margin scheme with percentage based leverage
    (Automargin).
    """

    params = (
        ('commission', 0.0),
        ('mult', 1.0),
        ('margin', 0.0),
        ('commtype', bt.CommInfoBase.COMM_FIXED),
        ('stocklike', True),
        ('leverage', 50.0),
        ('automargin', 0.02),
        ('interest', 0.0),
        ('interest_long', False),
    )

    def __init__(self, margin_requirement: float = 0.02, mult: float = 1.0) -> None:
        """Initializes the dynamic leverage scheme from margin requirements.

        The leverage profile property gets calculated internally via the
        mathematical inverse formula of the structural margin requirement.
        """
        super().__init__()
        # pylint: disable=no-member
        self.p.automargin = margin_requirement
        self.p.leverage = 1.0 / margin_requirement
        self.p.mult = mult

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
