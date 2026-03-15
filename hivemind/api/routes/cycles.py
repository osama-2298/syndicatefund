"""Cycle history endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from hivemind.db.models import CycleRow
from hivemind.db.session import get_db

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


@router.get("", response_model=list[CycleSummary])
async def list_cycles(
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
):
    """List recent cycle history."""
    result = await db.execute(
        select(CycleRow).order_by(desc(CycleRow.id)).limit(limit)
    )
    cycles = result.scalars().all()

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
