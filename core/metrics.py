"""Aegis Framework - Quantitative Performance Metrics Assessor.

Computes mathematical evaluation vectors for backtest portfolio performance,
integrating Sharpe, Sortino, SQN, Profit Factor, and Ulcer volatility profiles.
"""
import math
from typing import Any

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class PerformanceAssessor:
    """Calculates vector performance statistics on discrete backtest arrays."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        equity_curve: list[float],
        trade_history: list[dict[str, Any]],
        initial_capital: float = 10000.0
    ):
        """Initializes the multi-metric quantitative evaluator workspace.

        Args:
            equity_curve (list[float]): Sequential snapshots of floating equity.
            trade_history (list[dict[str, Any]]): Ledger containing closed trade logs.
            initial_capital (float): Starting balance allocated to the window node.
        """
        self.equity_curve = equity_curve or [initial_capital]
        self.trade_history = trade_history
        self.initial_capital = initial_capital

# -----------------------------------------------------------------------------

    def compute_performance_matrix(self) -> dict[str, float]:
        """Processes historical arrays into 11 quantitative metric anchors.

        Returns:
            dict[str, float]: Compiled dictionary mapping evaluated records.
        """
        if not self.trade_history or len(self.equity_curve) < 2:
            return {
                'return_pct': 0.0,
                'win_rate': 0.0,
                'expected_value_pct': 0.0,
                'profit_factor': 0.0,
                'avg_payoff_ratio': 0.0,
                'max_drawdown': 0.0,
                'ulcer_index': 0.0,
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'recovery_ratio': 0.0,
                'system_quality_number': 0.0
            }

        # 1. Basic descriptive metrics calculations
        final_equity = self.equity_curve[-1]
        return_pct = (
            ((final_equity - self.initial_capital) / self.initial_capital) * 100.0
        )

        pnls = [float(trade['pnl']) for trade in self.trade_history]
        total_trades = len(pnls)

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        win_rate = len(wins) / total_trades
        mean_pnl = sum(pnls) / total_trades
        expected_value_pct = (mean_pnl / self.initial_capital) * 100.0

        # 2. Profit Factor and Payoff ratio protections
        gross_profits = sum(wins)
        gross_losses = abs(sum(losses))
        profit_factor = gross_profits / gross_losses if gross_losses > 0 else 99.0

        avg_win = gross_profits / len(wins) if wins else 0.0
        avg_loss = gross_losses / len(losses) if losses else 0.0
        avg_payoff_ratio = avg_win / avg_loss if avg_loss > 0 else 99.0

        # 3. Dynamic Drawdown and Ulcer Index vector evaluations
        max_drawdown = 0.0
        peak = self.equity_curve[0]
        drawdown_squares_sum = 0.0

        for eq in self.equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0.0
            if dd > max_drawdown:
                max_drawdown = dd
            drawdown_squares_sum += dd * dd

        ulcer_index = math.sqrt(drawdown_squares_sum / len(self.equity_curve))

        # 4. Chronological relative return extraction for Sharpe and Sortino
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev = self.equity_curve[i - 1]
            if prev > 0:
                returns.append((self.equity_curve[i] - prev) / prev)
            else:
                returns.append(0.0)

        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)

        downside_returns = [r for r in returns if r < 0]
        downside_var = sum(r ** 2 for r in downside_returns) / len(returns)
        downside_std = math.sqrt(downside_var)

        # Apply daily-scale annualization multiplier anchoring (\sqrt{252})
        sharpe_ratio = (mean_ret / std_dev) * math.sqrt(252) if std_dev > 0 else 0.0
        sortino_ratio = (
            (mean_ret / downside_std) * math.sqrt(252) if downside_std > 0 else 0.0
        )
        recovery_ratio = return_pct / (max_drawdown * 100.0) if max_drawdown > 0 else 0.0

        # 5. System Quality Number (SQN) formulation matrix
        trade_pnl_variance = sum((p - mean_pnl) ** 2 for p in pnls) / total_trades
        trade_pnl_std = math.sqrt(trade_pnl_variance)

        if trade_pnl_std > 0:
            system_quality_number = (mean_pnl / trade_pnl_std) * math.sqrt(total_trades)
        else:
            system_quality_number = 0.0

        return {
            'return_pct': return_pct,
            'win_rate': win_rate,
            'expected_value_pct': expected_value_pct,
            'profit_factor': profit_factor,
            'avg_payoff_ratio': avg_payoff_ratio,
            'max_drawdown': max_drawdown,
            'ulcer_index': ulcer_index,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'recovery_ratio': recovery_ratio,
            'system_quality_number': system_quality_number
        }

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
