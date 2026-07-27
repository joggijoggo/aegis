"""Aegis Framework - Quantitative Performance Metrics Unit Tests.

Validates math operations for portfolio metrics including Sharpe, Sortino,
System Quality Number (SQN), Profit Factor, and Ulcer index vectors.
"""
from core.metrics import PerformanceAssessor

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_performance_assessor_calculation_matrix():
    """Validates vector calculations for the 11 institutional metrics."""
    # Starting at 10000.0, peaking at 10500.0, dropping to 9500.0, ending at 10200.0
    equity_curve = [10000.0, 10200.0, 10500.0, 9500.0, 10200.0]

    # Transaction tracking logs: 3 winning trades, 1 losing trade
    trade_history = [
        {'pnl': 200.0},
        {'pnl': 300.0},
        {'pnl': -1000.0},
        {'pnl': 700.0}
    ]

    assessor = PerformanceAssessor(
        equity_curve=equity_curve,
        trade_history=trade_history,
        initial_capital=10000.0
    )

    metrics = assessor.compute_performance_matrix()

    # 1. Return absolute performance percentage: (10200 - 10000) / 10000 = 2%
    assert round(metrics['return_pct'], 2) == 2.00

    # 2. Win Rate: 3 wins out of 4 trades = 75%
    assert round(metrics['win_rate'], 2) == 0.75

    # 3. Expected Value in percent of initial capital: Mean PnL (+50) / 10000 = 0.50%
    assert round(metrics['expected_value_pct'], 2) == 0.50

    # 4. Profit Factor: Gross Profits (1200) / Gross Loss (1000) = 1.20
    assert round(metrics['profit_factor'], 2) == 1.20

    # 5. Average Payoff Ratio: Avg Win (400) / Avg Loss (1000) = 0.40
    assert round(metrics['avg_payoff_ratio'], 2) == 0.40

    # 6. Maximum Drawdown: Peak 10500 to Trough 9500 -> 1000 / 10500 = 9.52%
    assert round(metrics['max_drawdown'], 4) == 0.0952

    # 7. Verification of types for advanced statistical metrics
    assert isinstance(metrics['ulcer_index'], float)
    assert isinstance(metrics['sharpe_ratio'], float)
    assert isinstance(metrics['sortino_ratio'], float)
    assert isinstance(metrics['recovery_ratio'], float)
    assert isinstance(metrics['system_quality_number'], float)

# -----------------------------------------------------------------------------

def test_performance_assessor_perfect_strategy_sentinel_coverage():
    """Validates maximal sentinel fallback triggers when zero losses exist."""
    equity_curve = [10000.0, 10500.0, 11000.0]
    trade_history = [{'pnl': 500.0}, {'pnl': 500.0}]

    assessor = PerformanceAssessor(
        equity_curve=equity_curve,
        trade_history=trade_history,
        initial_capital=10000.0
    )

    metrics = assessor.compute_performance_matrix()

    # Triggers gross_losses == 0 condition and trade_pnl_std == 0 condition
    assert metrics['profit_factor'] == 99.0
    assert metrics['avg_payoff_ratio'] == 99.0
    assert metrics['system_quality_number'] == 0.0

# -----------------------------------------------------------------------------

def test_performance_assessor_negative_equity_fallback():
    """Validates return tracking when historical equity drops to zero boundaries."""
    equity_curve = [10000.0, 0.0, 5000.0]
    trade_history = [{'pnl': -10000.0}, {'pnl': 5000.0}]

    assessor = PerformanceAssessor(
        equity_curve=equity_curve,
        trade_history=trade_history,
        initial_capital=10000.0
    )

    metrics = assessor.compute_performance_matrix()
    assert isinstance(metrics['sharpe_ratio'], float)

# -----------------------------------------------------------------------------

def test_performance_assessor_empty_and_zero_edge_cases():
    """Validates fallback protection constraints when data sets remain static."""
    assessor = PerformanceAssessor(
        equity_curve=[10000.0, 10000.0],
        trade_history=[],
        initial_capital=10000.0
    )

    metrics = assessor.compute_performance_matrix()

    assert metrics['return_pct'] == 0.0
    assert metrics['win_rate'] == 0.0
    assert metrics['expected_value_pct'] == 0.0
    assert metrics['profit_factor'] == 0.0
    assert metrics['avg_payoff_ratio'] == 0.0
    assert metrics['max_drawdown'] == 0.0
    assert metrics['ulcer_index'] == 0.0
    assert metrics['sharpe_ratio'] == 0.0
    assert metrics['sortino_ratio'] == 0.0
    assert metrics['recovery_ratio'] == 0.0
    assert metrics['system_quality_number'] == 0.0

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
