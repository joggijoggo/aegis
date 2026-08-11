"""Aegis Framework - Market Regime Classifier Layer.

Implements the quantitative analysis engine computing Hurst and Kaufman indices.
"""

import logging
import math

from aegis.core.model import RegimeConfidenceVector

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class MarketRegimeClassifier:
    """Handles statistical evaluation of time series arrays to isolate regimes."""

# -----------------------------------------------------------------------------

    def classify_series(self, close_prices: list[float]) -> RegimeConfidenceVector:
        """Processes historical arrays into normalized probability metrics.

        Args:
            close_prices (list[float]): Sequential chronological baseline prices.

        Returns:
            RegimeConfidenceVector: Immutably stored classification scores.
        """
        if len(close_prices) < 10:
            return RegimeConfidenceVector(mean_reversion=0.33, trending=0.33, noise=0.34)

        # 1. Calculate Kaufman Efficiency Ratio (ER)
        direction = abs(close_prices[-1] - close_prices[0])
        volatility = sum(
            abs(close_prices[i] - close_prices[i - 1])
            for i in range(1, len(close_prices))
        )
        kaufman_er = direction / volatility if volatility > 0 else 0.0

        # 2. Calculate simplified Rescaled Range Proxy for Hurst Exponent
        returns = [
            close_prices[i] - close_prices[i - 1] for i in range(1, len(close_prices))
        ]
        mean_return = sum(returns) / len(returns)

        cum_deviations = [0.0]
        for r in returns:
            cum_deviations.append(cum_deviations[-1] + (r - mean_return))

        r_range = max(cum_deviations) - min(cum_deviations)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance) if variance > 0 else 1.0

        rs_scaled = r_range / std_dev
        hurst_exponent = (
            math.log(rs_scaled) / math.log(len(close_prices))
            if rs_scaled > 1
            else 0.5
        )

        # 3. Enhanced financial weight mapping
        mr_weight = max(0.0, (0.5 - hurst_exponent) * 4.0) + (1.0 - kaufman_er) * 2.0
        trend_weight = max(0.0, (hurst_exponent - 0.5) * 4.0) + kaufman_er * 3.0

        # Noise dominates only when Hurst is exactly near 0.5 and ER is neutral
        noise_weight = (1.0 - kaufman_er) * max(
            0.0, 1.0 - abs(hurst_exponent - 0.5) * 2.0,
        )

        # Secure total weight sum normalization to clear mathematical boundaries
        total_weight = mr_weight + trend_weight + noise_weight
        eps_weight = total_weight if total_weight > 0 else 1.0

        return RegimeConfidenceVector(
            mean_reversion=mr_weight / eps_weight,
            trending=trend_weight / eps_weight,
            noise=noise_weight / eps_weight
        )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
