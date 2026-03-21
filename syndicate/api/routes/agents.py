"""Agent listing and assignment endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from syndicate.api.dependencies import require_admin
from syndicate.db.models import AgentRow, AgentStatusDB, TeamRow
from syndicate.db.session import get_db

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentSummary(BaseModel):
    id: str
    contributor_id: str | None
    team_id: str | None
    team_name: str | None
    role: str
    agent_class: str | None
    model: str
    provider: str
    status: str
    total_signals: int
    correct_signals: int
    accuracy: float
    total_cost_usd: float
    quarantine_signals_remaining: int
    created_at: str


@router.get("", response_model=list[AgentSummary])
async def list_agents(
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
    team_id: str | None = None,
    include_fired: bool = False,
):
    """List all agents (full transparency)."""
    query = select(AgentRow).options(joinedload(AgentRow.team))

    if status:
        try:
            query = query.where(AgentRow.status == AgentStatusDB(status))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{status}'. Valid: {[s.value for s in AgentStatusDB]}",
            )
    elif not include_fired:
        query = query.where(AgentRow.status != AgentStatusDB.FIRED)
    if team_id:
        try:
            query = query.where(AgentRow.team_id == UUID(team_id))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid team_id UUID: '{team_id}'")

    result = await db.execute(query)
    agents = result.unique().scalars().all()

    # If DB has no signal data, enrich from snapshot files
    all_zero = all(a.total_signals == 0 for a in agents)
    team_stats: dict[str, dict] = {}
    if all_zero:
        team_stats = _load_team_stats_from_snapshots()

    summaries = []
    for a in agents:
        total = a.total_signals
        correct = a.correct_signals

        # Merge from snapshot team stats if DB is empty
        if total == 0 and a.team and a.team.name in team_stats:
            ts = team_stats[a.team.name]
            # Attribute team-level stats to each agent in the team
            total = ts.get("total", 0)
            correct = ts.get("correct", 0)

        accuracy = correct / total if total > 0 else 0.0
        summaries.append(AgentSummary(
            id=str(a.id),
            contributor_id=str(a.contributor_id) if a.contributor_id else None,
            team_id=str(a.team_id) if a.team_id else None,
            team_name=a.team.name if a.team else None,
            role=a.role,
            agent_class=a.agent_class,
            model=a.model,
            provider=a.provider.value,
            status=a.status.value,
            total_signals=total,
            correct_signals=correct,
            accuracy=round(accuracy, 4),
            total_cost_usd=float(a.total_cost_usd),
            quarantine_signals_remaining=a.quarantine_signals_remaining,
            created_at=a.created_at.isoformat(),
        ))
    return summaries


def _load_team_stats_from_snapshots() -> dict[str, dict]:
    """Load team signal stats from the latest cycle snapshot."""
    snapshots_dir = Path("data/cycles")
    if not snapshots_dir.exists():
        return {}
    files = sorted(snapshots_dir.glob("cycle_*.json"), reverse=True)
    if not files:
        return {}
    try:
        data = json.loads(files[0].read_text())
        return data.get("team_stats", {})
    except Exception:
        return {}


class AgentDetail(AgentSummary):
    metadata: dict


@router.get("/{agent_id}", response_model=AgentDetail)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed info for a single agent."""
    try:
        uid = UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent_id UUID: '{agent_id}'")

    result = await db.execute(
        select(AgentRow)
        .options(joinedload(AgentRow.team))
        .where(AgentRow.id == uid)
    )
    agent = result.unique().scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    return AgentDetail(
        id=str(agent.id),
        contributor_id=str(agent.contributor_id) if agent.contributor_id else None,
        team_id=str(agent.team_id) if agent.team_id else None,
        team_name=agent.team.name if agent.team else None,
        role=agent.role,
        agent_class=agent.agent_class,
        model=agent.model,
        provider=agent.provider.value,
        status=agent.status.value,
        total_signals=agent.total_signals,
        correct_signals=agent.correct_signals,
        accuracy=agent.correct_signals / agent.total_signals if agent.total_signals > 0 else 0.0,
        total_cost_usd=float(agent.total_cost_usd),
        quarantine_signals_remaining=agent.quarantine_signals_remaining,
        created_at=agent.created_at.isoformat(),
        metadata=agent.metadata_ or {},
    )


@router.get("/{agent_id}/prompt")
async def get_agent_prompt(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: bool = Depends(require_admin),
):
    """Admin: get an agent's system prompt."""
    try:
        uid = UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent_id UUID: '{agent_id}'")
    result = await db.execute(select(AgentRow).where(AgentRow.id == uid))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"system_prompt": agent.system_prompt}


class AssignRequest(BaseModel):
    team_id: str


@router.post("/{agent_id}/assign", response_model=AgentSummary)
async def assign_agent(
    agent_id: str,
    req: AssignRequest,
    db: AsyncSession = Depends(get_db),
    _admin: bool = Depends(require_admin),
):
    """Admin: assign an agent to a team (Phase 1 = manual assignment)."""
    try:
        agent_uid = UUID(agent_id)
        team_uid = UUID(req.team_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {e}")

    result = await db.execute(
        select(AgentRow).where(AgentRow.id == agent_uid)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.status == AgentStatusDB.FOUNDING:
        raise HTTPException(status_code=400, detail="Cannot reassign founding agents")

    # Verify team exists
    team_result = await db.execute(
        select(TeamRow).where(TeamRow.id == team_uid)
    )
    team = team_result.scalar_one_or_none()
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    agent.team_id = team.id
    agent.status = AgentStatusDB.ASSIGNED

    return AgentSummary(
        id=str(agent.id),
        contributor_id=str(agent.contributor_id) if agent.contributor_id else None,
        team_id=str(agent.team_id),
        team_name=team.name,
        role=agent.role,
        agent_class=agent.agent_class,
        model=agent.model,
        provider=agent.provider.value,
        status=agent.status.value,
        total_signals=agent.total_signals,
        correct_signals=agent.correct_signals,
        accuracy=agent.correct_signals / agent.total_signals if agent.total_signals > 0 else 0.0,
        total_cost_usd=float(agent.total_cost_usd),
        quarantine_signals_remaining=agent.quarantine_signals_remaining,
        created_at=agent.created_at.isoformat(),
    )
