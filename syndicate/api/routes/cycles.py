"""Cycle history endpoints."""

from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from syndicate.db.models import CycleRow
from syndicate.db.session import get_db

_cycle_running = threading.Event()

router = APIRouter(prefix="/cycles", tags=["cycles"])


class CycleSummary(BaseModel):
    id: int
    started_at: str
    completed_at: str | None
    duration_secs: float | None
    regime: str | None
    coins_analyzed: int
    signals_produced: int
    orders_executed: int
    portfolio_value: float | None
    error: str | None


def _load_snapshot_cycles(limit: int = 20) -> list[CycleSummary]:
    """Load cycle summaries from snapshot JSON files as fallback."""
    snapshots_dir = Path("data/cycles")
    if not snapshots_dir.exists():
        return []
    files = sorted(snapshots_dir.glob("cycle_*.json"), reverse=True)[:limit]
    results = []
    for i, f in enumerate(files):
        try:
            data = json.loads(f.read_text())
            results.append(CycleSummary(
                id=1000 + i,  # Synthetic ID from file index
                started_at=data.get("timestamp", ""),
                completed_at=data.get("timestamp", ""),
                duration_secs=data.get("duration_secs"),
                regime=data.get("ceo_directive", {}).get("regime"),
                coins_analyzed=data.get("coins_analyzed", 0),
                signals_produced=data.get("signals_produced", 0),
                orders_executed=data.get("orders_executed", 0),
                portfolio_value=data.get("portfolio_summary", {}).get("total_value"),
                error=None,
            ))
        except Exception:
            continue
    return results


@router.get("", response_model=list[CycleSummary])
async def list_cycles(
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
):
    """List recent cycle history. Falls back to snapshot files if DB empty."""
    result = await db.execute(
        select(CycleRow).order_by(desc(CycleRow.id)).limit(limit)
    )
    cycles = result.scalars().all()

    if cycles:
        return [
            CycleSummary(
                id=c.id,
                started_at=c.started_at.isoformat(),
                completed_at=c.completed_at.isoformat() if c.completed_at else None,
                duration_secs=c.duration_secs,
                regime=c.regime,
                coins_analyzed=c.coins_analyzed,
                signals_produced=c.signals_produced,
                orders_executed=c.orders_executed,
                portfolio_value=float(c.portfolio_value) if c.portfolio_value else None,
                error=c.error,
            )
            for c in cycles
        ]

    # Fallback to snapshot files
    return _load_snapshot_cycles(limit)


@router.get("/current")
async def current_cycle(
    db: AsyncSession = Depends(get_db),
):
    """Get current/latest cycle status."""
    result = await db.execute(
        select(CycleRow).order_by(desc(CycleRow.id)).limit(1)
    )
    cycle = result.scalar_one_or_none()

    if cycle is None:
        return {"status": "no_cycles", "message": "No cycles have been run yet"}

    is_running = cycle.completed_at is None
    return {
        "status": "running" if is_running else "completed",
        "cycle_id": cycle.id,
        "started_at": cycle.started_at.isoformat(),
        "completed_at": cycle.completed_at.isoformat() if cycle.completed_at else None,
        "regime": cycle.regime,
    }


@router.get("/snapshots")
async def list_snapshots(limit: int = 10):
    """List available cycle snapshots from data/cycles/."""
    snapshots_dir = Path("data/cycles")
    if not snapshots_dir.exists():
        return []
    files = sorted(snapshots_dir.glob("cycle_*.json"), reverse=True)[:limit]
    results = []
    for f in files:
        try:
            data = json.loads(f.read_text())
            results.append({
                "filename": f.name,
                "timestamp": data.get("timestamp", ""),
                "regime": data.get("ceo_directive", {}).get("regime"),
                "coins_analyzed": data.get("coins_analyzed", 0),
                "signals_produced": data.get("signals_produced", 0),
                "orders_executed": data.get("orders_executed", 0),
                "duration_secs": data.get("duration_secs", 0),
                "agent_signals_count": len(data.get("agent_signals", [])),
                "disagreements_count": len(data.get("disagreements", [])),
                "trades_count": len(data.get("trades_executed", [])),
            })
        except Exception:
            continue
    return results


@router.get("/snapshots/{filename}")
async def get_snapshot(filename: str):
    """Get full cycle snapshot data by filename."""
    # Sanitize filename
    if not filename.startswith("cycle_") or not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Invalid snapshot filename")
    path = Path("data/cycles") / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Snapshot not found")
    try:
        return json.loads(path.read_text())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read snapshot: {e}")


@router.get("/latest-snapshot")
async def get_latest_snapshot():
    """Get the most recent cycle snapshot."""
    snapshots_dir = Path("data/cycles")
    if not snapshots_dir.exists():
        raise HTTPException(status_code=404, detail="No snapshots available")
    files = sorted(snapshots_dir.glob("cycle_*.json"), reverse=True)
    if not files:
        raise HTTPException(status_code=404, detail="No snapshots available")
    try:
        return json.loads(files[0].read_text())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read snapshot: {e}")


@router.post("/trigger")
async def trigger_cycle():
    """Manually trigger a full pipeline cycle (bypasses daily mode).

    Returns immediately; cycle runs in background.
    """
    if _cycle_running.is_set():
        return {"status": "already_running", "message": "A cycle is already in progress"}

    async def _run():
        _cycle_running.set()
        try:
            from syndicate.config import settings
            from syndicate.data.binance_client import BinanceClient
            from syndicate.main import run_pipeline

            # Force full decision cycle by temporarily overriding decision_mode
            original_mode = settings.decision_mode
            settings.decision_mode = "every_cycle"

            # Try to load registry from DB
            registry = None
            try:
                from syndicate.core.agent_registry import AgentRegistry
                from syndicate.db.session import async_session_factory
                async with async_session_factory() as session:
                    registry = AgentRegistry(session)
                    await registry.load_all()
            except Exception:
                pass

            try:
                binance = BinanceClient()
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, lambda: run_pipeline(binance=binance, registry=registry)
                )
                binance.close()
            finally:
                # Restore original decision mode
                settings.decision_mode = original_mode
        finally:
            _cycle_running.clear()

    asyncio.create_task(_run())
    return {"status": "triggered", "message": "Full pipeline cycle started in background (decision_mode override)"}
