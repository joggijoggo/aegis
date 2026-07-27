"""Aegis Framework - Market Regime Classifier Unit Tests.

Verifies mathematical matrix processing for Hurst and Kaufman algorithms.
"""

import math


# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_market_regime_classifier_statistical_vectors():
    """Validates math isolation for mean-reverting and trending data arrays."""
    from strategies.regime_manager import MarketRegimeClassifier

    classifier = MarketRegimeClassifier()

    # 1. Synthesize a cyclical mean-reverting series (Sine Wave)
    sine_series = [1.0 + math.sin(i * 0.5) for i in range(100)]
    vector_mr = classifier.classify_series(sine_series)

    assert vector_mr.mean_reversion > 0.50
    assert vector_mr.trending < 0.50

    # 2. Synthesize a distinct linear trending series
    trending_series = [float(i * 1.5) for i in range(100)]
    vector_trend = classifier.classify_series(trending_series)

    assert vector_trend.trending > 0.50
    assert vector_trend.mean_reversion < 0.50

# -----------------------------------------------------------------------------

def test_market_regime_classifier_insufficient_data_fallback():
    """Validates uniform distribution fallback when data length is too short."""
    from strategies.regime_manager import MarketRegimeClassifier

    classifier = MarketRegimeClassifier()
    short_series = [1.0, 1.02, 1.01]

    vector = classifier.classify_series(short_series)
    assert vector.mean_reversion == 0.33
    assert vector.trending == 0.33

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
