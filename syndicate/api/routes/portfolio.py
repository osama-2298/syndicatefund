"""Portfolio state and trade history endpoints."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from syndicate.config import settings
from syndicate.db.session import get_db

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
async def get_trades(db: AsyncSession = Depends(get_db)):
    """Get trade ledger — all trades with P&L and computed stats.

    Data sources (in priority order):
    1. trade_ledger.json (primary — written by pipeline + price monitor)
    2. DB pipeline_events for trade_executed / trade_closed (fallback)
    """
    from syndicate.execution.trade_ledger import TradeLedger

    ledger = TradeLedger(storage_path=settings.trade_ledger_path)

    # If ledger has entries, use it (canonical source)
    if ledger.entries:
        trades = [e.to_dict() for e in ledger.entries]
        stats = ledger.get_stats()
        return {"trades": trades, "stats": stats}

    # Fallback: reconstruct from DB pipeline_events
    trades_from_db = await _trades_from_pipeline_events(db)
    if trades_from_db:
        return {"trades": trades_from_db, "stats": _compute_basic_stats(trades_from_db)}

    return {"trades": [], "stats": {}}


async def _trades_from_pipeline_events(db: AsyncSession) -> list[dict]:
    """Reconstruct trade history from pipeline_events table."""
    try:
        from syndicate.db.models import PipelineEventRow

        # Get all trade_executed and trade_closed events
        query = (
            select(PipelineEventRow)
            .where(PipelineEventRow.event_type.in_(["trade_executed", "trade_closed"]))
            .order_by(PipelineEventRow.timestamp)
        )
        result = await db.execute(query)
        rows = result.scalars().all()

        if not rows:
            return []

        # Build trade records from events
        # trade_executed events have entry info, trade_closed have exit info
        open_trades: dict[str, dict] = {}  # symbol -> trade entry data
        closed_trades: list[dict] = []

        for row in rows:
            detail = row.detail or {}
            ts = row.timestamp.isoformat() if row.timestamp else ""

            if row.event_type == "trade_executed":
                symbol = detail.get("symbol", "")
                open_trades[symbol] = {
                    "symbol": symbol,
                    "side": detail.get("side", ""),
                    "entry_price": detail.get("price", detail.get("entry_price", 0)),
                    "quantity": detail.get("quantity", 0),
                    "entry_time": ts,
                    "exit_price": 0,
                    "exit_time": "",
                    "exit_reason": "OPEN",
                    "pnl_pct": 0,
                    "pnl_usd": 0,
                    "holding_hours": 0,
                    "asset_tier": detail.get("asset_tier", ""),
                    "stop_loss": detail.get("stop_loss", 0),
                    "take_profit_1": detail.get("take_profit_1", 0),
                    "conviction": detail.get("conviction", 0),
                    "confidence": detail.get("confidence", 0),
                }

            elif row.event_type == "trade_closed":
                symbol = detail.get("symbol", "")
                entry = open_trades.pop(symbol, None)
                trade = {
                    "symbol": symbol,
                    "side": detail.get("side", entry.get("side", "") if entry else ""),
                    "entry_price": detail.get("entry_price", entry.get("entry_price", 0) if entry else 0),
                    "exit_price": detail.get("exit_price", detail.get("price", 0)),
                    "quantity": detail.get("quantity", 0),
                    "entry_time": entry.get("entry_time", "") if entry else "",
                    "exit_time": ts,
                    "exit_reason": detail.get("exit_reason", "CLOSED"),
                    "pnl_pct": detail.get("pnl_pct", 0),
                    "pnl_usd": detail.get("pnl_usd", 0),
                    "holding_hours": detail.get("holding_hours", 0),
                    "asset_tier": detail.get("asset_tier", entry.get("asset_tier", "") if entry else ""),
                    "stop_loss": entry.get("stop_loss", 0) if entry else 0,
                    "take_profit_1": entry.get("take_profit_1", 0) if entry else 0,
                    "conviction": entry.get("conviction", 0) if entry else 0,
                    "confidence": entry.get("confidence", 0) if entry else 0,
                }
                closed_trades.append(trade)

        # Include remaining open trades too
        all_trades = list(open_trades.values()) + closed_trades
        return all_trades

    except Exception:
        return []


def _compute_basic_stats(trades: list[dict]) -> dict:
    """Compute basic stats from a list of trade dicts."""
    closed = [t for t in trades if t.get("exit_reason", "OPEN") != "OPEN"]
    if not closed:
        return {"total_trades": len(trades), "closed_trades": 0, "open_trades": len(trades)}

    wins = [t for t in closed if t.get("pnl_pct", 0) > 0.001]
    losses = [t for t in closed if t.get("pnl_pct", 0) < -0.001]
    total_pnl = sum(t.get("pnl_usd", 0) for t in closed)

    return {
        "total_trades": len(trades),
        "open_trades": len(trades) - len(closed),
        "closed_trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0,
        "total_pnl_usd": round(total_pnl, 2),
        "avg_pnl_pct": round(sum(t.get("pnl_pct", 0) for t in closed) / len(closed) * 100, 2) if closed else 0,
    }


@router.get("/team-performance")
async def get_team_performance():
    """Per-team signal quality analytics."""
    from syndicate.evaluation.performance_tracker import PerformanceTracker
    from syndicate.executive.team_weights import TeamWeightManager

    tracker = PerformanceTracker(storage_path=settings.perf_history_path)
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
