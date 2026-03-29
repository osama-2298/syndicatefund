"""Portfolio state and trade history endpoints."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from hivemind.config import settings

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("")
async def get_portfolio():
    """Get current portfolio state from JSON file."""
    portfolio_path = Path(settings.portfolio_state_path)

    if not portfolio_path.exists():
        return {
            "cash": 100_000.0,
            "positions": [],
            "total_value": 100_000.0,
            "total_realized_pnl": 0.0,
            "total_unrealized_pnl": 0.0,
        }

    try:
        data = json.loads(portfolio_path.read_text())
        return data
    except Exception:
        return {"error": "Failed to read portfolio state"}


@router.get("/trades")
async def get_trades():
    """Get trade ledger — all closed trades with P&L."""
    ledger_path = Path(settings.trade_ledger_path)

    if not ledger_path.exists():
        return {"trades": [], "stats": {}}

    try:
        data = json.loads(ledger_path.read_text())
        return data
    except Exception:
        return {"trades": [], "stats": {}}


@router.get("/team-performance")
async def get_team_performance():
    """Per-team signal quality analytics."""
    from hivemind.evaluation.performance_tracker import PerformanceTracker
    from hivemind.execution.trade_ledger import TradeLedger
    from hivemind.executive.team_weights import TeamWeightManager

    tracker = PerformanceTracker(storage_path=settings.perf_history_path)
    ledger = TradeLedger(storage_path=settings.trade_ledger_path)
    weights = TeamWeightManager(storage_path=settings.team_weights_path)

    team_stats = tracker.get_team_stats()

    result = {}
    for team, stats in team_stats.items():
        result[team] = {
            "total_signals": stats["total"],
            "signal_accuracy": stats["accuracy"],
            "correct": stats["correct"],
            "incorrect": stats["incorrect"],
            "pending": stats["pending"],
            "current_weight": weights.get_weight(team),
        }

    return result
