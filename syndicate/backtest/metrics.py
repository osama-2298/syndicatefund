"""Backtest metrics -- Sharpe, drawdown, benchmark comparison."""

from __future__ import annotations

import math
from typing import Any


def compute_backtest_metrics(
    equity_curve: list[dict],
    daily_returns: list[float],
    benchmark_prices: dict[str, list[float]] | None = None,
) -> dict[str, Any]:
    """Compute comprehensive backtest metrics.

    Args:
        equity_curve: List of dicts with at least ``{"date": ..., "value": ...}``.
        daily_returns: List of fractional daily returns (e.g. 0.01 = 1%).
        benchmark_prices: Optional ``{"BTC": [p0, p1, ...], "ETH": [p0, p1, ...]}``.

    Returns:
        Dict with all computed metrics.
    """

    # -- Basic returns ---------------------------------------------------
    if not equity_curve or len(equity_curve) < 2:
        return _empty_metrics()

    start_value = equity_curve[0]["value"]
    end_value = equity_curve[-1]["value"]
    total_return_pct = ((end_value / start_value) - 1) * 100 if start_value > 0 else 0.0

    n_days = len(daily_returns) if daily_returns else 1
    ann_factor = 365  # crypto trades 365 days/year

    # Annualised return (compound)
    if start_value > 0 and n_days > 0:
        annualized_return_pct = ((end_value / start_value) ** (ann_factor / n_days) - 1) * 100
    else:
        annualized_return_pct = 0.0

    # -- Sharpe ratio ----------------------------------------------------
    sharpe_ratio = _sharpe(daily_returns, ann_factor)

    # -- Sortino ratio ---------------------------------------------------
    sortino_ratio = _sortino(daily_returns, ann_factor)

    # -- Max drawdown ----------------------------------------------------
    max_drawdown = _max_drawdown(equity_curve)

    # -- Calmar ratio ----------------------------------------------------
    calmar_ratio = (annualized_return_pct / 100) / max_drawdown if max_drawdown > 0 else 0.0

    # -- Trade-level metrics (extracted from equity curve trades) ---------
    trades = [e for e in equity_curve if e.get("trade_pnl_pct") is not None]
    wins = [t for t in trades if t["trade_pnl_pct"] > 0]
    losses = [t for t in trades if t["trade_pnl_pct"] <= 0]

    total_trades = len(trades)
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0.0

    gross_profit = sum(t["trade_pnl_pct"] for t in wins) if wins else 0.0
    gross_loss = abs(sum(t["trade_pnl_pct"] for t in losses)) if losses else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)

    avg_trade_pnl_pct = (sum(t["trade_pnl_pct"] for t in trades) / total_trades) if total_trades > 0 else 0.0

    # -- Benchmark comparison --------------------------------------------
    vs_btc_hold = 0.0
    vs_eth_hold = 0.0
    information_ratio = 0.0

    if benchmark_prices:
        vs_btc_hold = _vs_benchmark(total_return_pct, benchmark_prices.get("BTC"))
        vs_eth_hold = _vs_benchmark(total_return_pct, benchmark_prices.get("ETH"))
        # Information ratio: excess return / tracking error
        if "BTC" in benchmark_prices:
            information_ratio = _information_ratio(
                daily_returns, benchmark_prices["BTC"], ann_factor
            )

    return {
        "sharpe_ratio": round(sharpe_ratio, 4),
        "sortino_ratio": round(sortino_ratio, 4),
        "max_drawdown": round(max_drawdown, 4),
        "calmar_ratio": round(calmar_ratio, 4),
        "win_rate": round(win_rate, 2),
        "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else 999.0,
        "total_return_pct": round(total_return_pct, 4),
        "annualized_return_pct": round(annualized_return_pct, 4),
        "vs_btc_hold": round(vs_btc_hold, 4),
        "vs_eth_hold": round(vs_eth_hold, 4),
        "information_ratio": round(information_ratio, 4),
        "total_trades": total_trades,
        "avg_trade_pnl_pct": round(avg_trade_pnl_pct, 4),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _empty_metrics() -> dict[str, Any]:
    return {
        "sharpe_ratio": 0.0,
        "sortino_ratio": 0.0,
        "max_drawdown": 0.0,
        "calmar_ratio": 0.0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "total_return_pct": 0.0,
        "annualized_return_pct": 0.0,
        "vs_btc_hold": 0.0,
        "vs_eth_hold": 0.0,
        "information_ratio": 0.0,
        "total_trades": 0,
        "avg_trade_pnl_pct": 0.0,
    }


def _sharpe(daily_returns: list[float], ann_factor: int) -> float:
    """Annualised Sharpe ratio (risk-free rate assumed 0)."""
    if len(daily_returns) < 2:
        return 0.0
    mean_r = sum(daily_returns) / len(daily_returns)
    var = sum((r - mean_r) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
    std = math.sqrt(var) if var > 0 else 0.0
    if std == 0:
        return 0.0
    return (mean_r / std) * math.sqrt(ann_factor)


def _sortino(daily_returns: list[float], ann_factor: int) -> float:
    """Annualised Sortino ratio (downside deviation only)."""
    if len(daily_returns) < 2:
        return 0.0
    mean_r = sum(daily_returns) / len(daily_returns)
    downside = [r for r in daily_returns if r < 0]
    if not downside:
        return 0.0 if mean_r <= 0 else 999.0
    downside_var = sum(r ** 2 for r in downside) / len(downside)
    downside_std = math.sqrt(downside_var)
    if downside_std == 0:
        return 0.0
    return (mean_r / downside_std) * math.sqrt(ann_factor)


def _max_drawdown(equity_curve: list[dict]) -> float:
    """Peak-to-trough percentage drawdown."""
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]["value"]
    max_dd = 0.0
    for entry in equity_curve:
        val = entry["value"]
        if val > peak:
            peak = val
        if peak > 0:
            dd = (peak - val) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd


def _vs_benchmark(
    strategy_return_pct: float,
    benchmark_prices: list[float] | None,
) -> float:
    """Alpha vs buy-and-hold of a benchmark asset."""
    if not benchmark_prices or len(benchmark_prices) < 2:
        return 0.0
    bm_return_pct = ((benchmark_prices[-1] / benchmark_prices[0]) - 1) * 100
    return strategy_return_pct - bm_return_pct


def _information_ratio(
    strategy_returns: list[float],
    benchmark_prices: list[float],
    ann_factor: int,
) -> float:
    """Information ratio: annualised excess return / tracking error."""
    if len(benchmark_prices) < 2 or len(strategy_returns) < 2:
        return 0.0

    # Compute benchmark daily returns
    bm_returns: list[float] = []
    for i in range(1, len(benchmark_prices)):
        if benchmark_prices[i - 1] > 0:
            bm_returns.append((benchmark_prices[i] / benchmark_prices[i - 1]) - 1)
        else:
            bm_returns.append(0.0)

    # Align lengths (take minimum)
    n = min(len(strategy_returns), len(bm_returns))
    excess = [strategy_returns[i] - bm_returns[i] for i in range(n)]

    if n < 2:
        return 0.0

    mean_excess = sum(excess) / n
    var_excess = sum((e - mean_excess) ** 2 for e in excess) / (n - 1)
    tracking_error = math.sqrt(var_excess) if var_excess > 0 else 0.0

    if tracking_error == 0:
        return 0.0

    return (mean_excess / tracking_error) * math.sqrt(ann_factor)
