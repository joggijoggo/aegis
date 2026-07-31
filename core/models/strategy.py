"""Aegis Framework - Strategy Decision Records.

Captures alpha trend convictions, statistical regime classifications, and operational
telemetry logging matrices.
"""

from dataclasses import dataclass

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

@dataclass(frozen=True)
class ExposureIntent:
    """Immutable data record capturing passive execution desires.

    Attributes:
        alpha_direction: The continuous trend conviction scalar bounded strictly
            between -1.0 and 1.0. A value of 0.0 explicitly enforces a flat position
            and triggers a portfolio liquidation. A value of None indicates no active
            opinion, instructing the engine to maintain ongoing exposures.
        stop_loss_ticks: The protective exit distance measured in ticks.
        take_profit_ticks: The target take-profit distance measured in ticks.
    """
    alpha_direction: float | None = None
    stop_loss_ticks: float = 0.0
    take_profit_ticks: float = 0.0

# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class RegimeConfidenceVector:
    """Stores statistical confidence metrics computed by math classifiers.

    Attributes:
        mean_reversion: Probability weight assigned to cyclic behaviors.
        trending: Probability weight assigned to directional patterns.
        noise: Probability weight assigned to non-exploitable random dynamics.
    """
    mean_reversion: float
    trending: float
    noise: float

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
