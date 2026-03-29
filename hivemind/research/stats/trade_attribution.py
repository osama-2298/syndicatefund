"""
Trade attribution engine — analyzes WHY trades won or lost.

Pure computation — feeds the Strategy Researcher agent.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from hivemind.config import settings


def _load_trades() -> list[dict]:
    """Load trades from the trade ledger."""
    path = Path(settings.trade_ledger_path)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "entries" in data:
            return data["entries"]
        return []
    except Exception:
        return []


def _closed_trades() -> list[dict]:
    """Get only closed trades (have exit_price > 0 and exit_reason != OPEN)."""
    return [t for t in _load_trades() if t.get("exit_reason") and t["exit_reason"] != "OPEN" and t.get("exit_price", 0) > 0]


def attribution_by_regime() -> dict[str, dict]:
    """Win rate and P&L by market regime."""
    trades = _closed_trades()
    result = defaultdict(lambda: {"total": 0, "wins": 0, "losses": 0, "total_pnl": 0.0})

    for t in trades:
        regime = t.get("regime", "unknown")
        result[regime]["total"] += 1
        pnl = t.get("pnl_usd", 0)
        result[regime]["total_pnl"] += pnl
        if pnl > 0:
            result[regime]["wins"] += 1
        else:
            result[regime]["losses"] += 1

    for stats in result.values():
        stats["win_rate"] = stats["wins"] / stats["total"] if stats["total"] > 0 else 0
        stats["avg_pnl"] = stats["total_pnl"] / stats["total"] if stats["total"] > 0 else 0

    return dict(result)


def attribution_by_conviction() -> dict[int, dict]:
    """Win rate at each conviction level."""
    trades = _closed_trades()
    result = defaultdict(lambda: {"total": 0, "wins": 0, "losses": 0, "total_pnl": 0.0})

    for t in trades:
        conv = t.get("conviction", 5)
        result[conv]["total"] += 1
        pnl = t.get("pnl_usd", 0)
        result[conv]["total_pnl"] += pnl
        if pnl > 0:
            result[conv]["wins"] += 1
        else:
            result[conv]["losses"] += 1

    for stats in result.values():
        stats["win_rate"] = stats["wins"] / stats["total"] if stats["total"] > 0 else 0
        stats["avg_pnl"] = stats["total_pnl"] / stats["total"] if stats["total"] > 0 else 0

    return dict(sorted(result.items()))


def attribution_by_exit_reason() -> dict[str, dict]:
    """Breakdown by how trades were closed."""
    trades = _closed_trades()
    result = defaultdict(lambda: {"total": 0, "wins": 0, "avg_pnl": 0.0, "total_pnl": 0.0, "avg_holding_hours": 0.0, "holding_sum": 0.0})

    for t in trades:
        reason = t.get("exit_reason", "unknown")
        result[reason]["total"] += 1
        pnl = t.get("pnl_usd", 0)
        result[reason]["total_pnl"] += pnl
        result[reason]["holding_sum"] += t.get("holding_hours", 0)
        if pnl > 0:
            result[reason]["wins"] += 1

    for stats in result.values():
        stats["win_rate"] = stats["wins"] / stats["total"] if stats["total"] > 0 else 0
        stats["avg_pnl"] = stats["total_pnl"] / stats["total"] if stats["total"] > 0 else 0
        stats["avg_holding_hours"] = stats["holding_sum"] / stats["total"] if stats["total"] > 0 else 0
        del stats["holding_sum"]

    return dict(result)


def attribution_by_asset_tier() -> dict[str, dict]:
    """Win rate by asset tier (btc, top5, large_cap, mid_cap, meme)."""
    trades = _closed_trades()
    result = defaultdict(lambda: {"total": 0, "wins": 0, "total_pnl": 0.0})

    for t in trades:
        tier = t.get("asset_tier", "unknown")
        result[tier]["total"] += 1
        pnl = t.get("pnl_usd", 0)
        result[tier]["total_pnl"] += pnl
        if pnl > 0:
            result[tier]["wins"] += 1

    for stats in result.values():
        stats["win_rate"] = stats["wins"] / stats["total"] if stats["total"] > 0 else 0
        stats["avg_pnl"] = stats["total_pnl"] / stats["total"] if stats["total"] > 0 else 0

    return dict(result)


def attribution_by_side() -> dict[str, dict]:
    """Win rate for LONG vs SHORT trades."""
    trades = _closed_trades()
    result = defaultdict(lambda: {"total": 0, "wins": 0, "total_pnl": 0.0})

    for t in trades:
        side = t.get("side", t.get("direction", "unknown"))
        result[side]["total"] += 1
        pnl = t.get("pnl_usd", 0)
        result[side]["total_pnl"] += pnl
        if pnl > 0:
            result[side]["wins"] += 1

    for stats in result.values():
        stats["win_rate"] = stats["wins"] / stats["total"] if stats["total"] > 0 else 0
        stats["avg_pnl"] = stats["total_pnl"] / stats["total"] if stats["total"] > 0 else 0

    return dict(result)


def holding_period_analysis() -> dict:
    """Analyze relationship between holding period and outcomes."""
    trades = _closed_trades()
    if not trades:
        return {"buckets": {}, "optimal_holding_hours": None}

    # Bucket by holding period
    buckets = {"0-4h": [], "4-12h": [], "12-24h": [], "24-48h": [], "48h+": []}

    for t in trades:
        hours = t.get("holding_hours", 0)
        pnl = t.get("pnl_usd", 0)
        if hours <= 4: buckets["0-4h"].append(pnl)
        elif hours <= 12: buckets["4-12h"].append(pnl)
        elif hours <= 24: buckets["12-24h"].append(pnl)
        elif hours <= 48: buckets["24-48h"].append(pnl)
        else: buckets["48h+"].append(pnl)

    result = {}
    for bucket, pnls in buckets.items():
        if pnls:
            result[bucket] = {
                "count": len(pnls),
                "win_rate": sum(1 for p in pnls if p > 0) / len(pnls),
                "avg_pnl": sum(pnls) / len(pnls),
                "total_pnl": sum(pnls),
            }

    # Find optimal holding period
    best_bucket = max(result.items(), key=lambda x: x[1].get("avg_pnl", 0)) if result else None

    return {
        "buckets": result,
        "optimal_holding_period": best_bucket[0] if best_bucket else None,
    }


def optimal_parameters() -> dict:
    """Data-driven recommendations for optimal trading parameters."""
    trades = _closed_trades()
    if len(trades) < 10:
        return {"insufficient_data": True, "trade_count": len(trades)}

    by_conviction = attribution_by_conviction()
    by_regime = attribution_by_regime()
    holding = holding_period_analysis()

    # Find optimal conviction threshold
    best_conv = None
    best_conv_wr = 0
    for conv, stats in by_conviction.items():
        if stats["total"] >= 5 and stats["win_rate"] > best_conv_wr:
            best_conv_wr = stats["win_rate"]
            best_conv = conv

    # Find best regime
    best_regime = None
    best_regime_wr = 0
    for regime, stats in by_regime.items():
        if stats["total"] >= 3 and stats["win_rate"] > best_regime_wr:
            best_regime_wr = stats["win_rate"]
            best_regime = regime

    # Compute overall stats
    pnls = [t.get("pnl_usd", 0) for t in trades]
    wins = sum(1 for p in pnls if p > 0)

    return {
        "total_trades": len(trades),
        "overall_win_rate": wins / len(trades),
        "total_pnl": sum(pnls),
        "avg_pnl": sum(pnls) / len(trades),
        "best_conviction_level": best_conv,
        "best_conviction_win_rate": best_conv_wr,
        "current_conviction_threshold": 4,
        "recommended_conviction_threshold": best_conv if best_conv and best_conv > 4 else 4,
        "best_regime": best_regime,
        "best_regime_win_rate": best_regime_wr,
        "optimal_holding_period": holding.get("optimal_holding_period"),
        "profit_factor": sum(p for p in pnls if p > 0) / max(abs(sum(p for p in pnls if p < 0)), 0.01),
        "max_win": max(pnls) if pnls else 0,
        "max_loss": min(pnls) if pnls else 0,
        "sharpe_estimate": (np.mean(pnls) / np.std(pnls)) * np.sqrt(6 * 365) if np.std(pnls) > 0 else 0,  # Annualized, 6 cycles/day
    }


def full_report() -> dict[str, Any]:
    """Complete trade attribution report for the Strategy Researcher."""
    return {
        "by_regime": attribution_by_regime(),
        "by_conviction": attribution_by_conviction(),
        "by_exit_reason": attribution_by_exit_reason(),
        "by_asset_tier": attribution_by_asset_tier(),
        "by_side": attribution_by_side(),
        "holding_analysis": holding_period_analysis(),
        "optimal_parameters": optimal_parameters(),
    }
