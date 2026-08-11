import backtrader as bt

class FutureFixedMarginScheme(bt.CommissionInfo):
    """Explicit Future scheme: fixed margin lot requirement with daily mark-to-market."""
    params = (
        ('commission', 0.0),              # No transaction fees for isolation
        ('mult', 1.0),                    # Point multiplier anchored to 1.0
        ('margin', 50.0),                 # Flat 50.0 currency units blocked per lot
        ('commtype', bt.CommInfoBase.COMM_FIXED),
        ('stocklike', False),             # CRITICAL: Active daily cash adjustments
        ('leverage', 1.0),
        ('automargin', False),
        ('interest', 0.0),
        ('interest_long', False),
    )

class SpotStockCashScheme(bt.CommissionInfo):
    """Explicit Spot Cash asset scheme requiring full payment upfront (No Margin)."""
    params = (
        ('commission', 0.0),              # No transaction fees
        ('mult', 1.0),                    # Multiplier strictly 1.0
        ('margin', 0.0),                  # Stocks require 0.0 margin collateral
        ('commtype', bt.CommInfoBase.COMM_PERC),
        ('stocklike', True),              # CRITICAL: PnL remains floating and virtual
        ('leverage', 1.0),                # 1:1 spot leverage profile
        ('automargin', False),
        ('interest', 0.0),
        ('interest_long', False),
    )

class ForexFixedMarginScheme(bt.CommissionInfo):
    """Explicit Forex margin scheme with static lot requirements and virtual floating PnL."""
    params = (
        ('commission', 0.0),
        ('mult', 1.0),
        ('margin', 50.0),                 # Static collateral of 50.0 units per lot
        ('commtype', bt.CommInfoBase.COMM_FIXED),
        ('stocklike', True),              # CRITICAL: Disables daily cash adjustments
        ('leverage', 1.0),
        ('automargin', False),
        ('interest', 0.0),
        ('interest_long', False),
    )

class ForexDynamicLeverageScheme(bt.CommissionInfo):
    """Explicit Forex margin scheme with percentage based leverage (Automargin)."""
    params = (
        ('commission', 0.0),
        ('mult', 1.0),
        ('margin', 0.0),                  # Fixed margin is 0.0, overridden by automargin
        ('commtype', bt.CommInfoBase.COMM_FIXED),
        ('stocklike', True),              # CRITICAL: Disables daily cash adjustments
        ('leverage', 50.0),               # 1:50 leverage profile (2% requirement)
        ('automargin', 0.02),             # CRITICAL: Margin required = current price * 2%
        ('interest', 0.0),
        ('interest_long', False),
    )
