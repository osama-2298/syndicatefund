"""Team listing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from syndicate.db.models import AgentRow, AgentStatusDB, TeamRow
from syndicate.db.session import get_db

router = APIRouter(prefix="/teams", tags=["teams"])


class TeamSummary(BaseModel):
    id: str
    name: str
    discipline: str
    status: str
    weight: float
    activation_mode: str
    min_agents: int
    is_system: bool
    created_by: str
    created_at: str
    agent_count: int
    active_agent_count: int
    data_keys: list[str]


@router.get("", response_model=list[TeamSummary])
async def list_teams(
    db: AsyncSession = Depends(get_db),
):
    """List all teams with agent counts and performance."""
    result = await db.execute(select(TeamRow))
    teams = result.scalars().all()

    summaries = []
    for team in teams:
        # Count agents
        total_q = await db.execute(
            select(func.count(AgentRow.id)).where(AgentRow.team_id == team.id)
        )
        total_agents = total_q.scalar() or 0

        active_q = await db.execute(
            select(func.count(AgentRow.id)).where(
                AgentRow.team_id == team.id,
                AgentRow.status.in_([AgentStatusDB.ACTIVE, AgentStatusDB.FOUNDING]),
            )
        )
        active_agents = active_q.scalar() or 0

        summaries.append(TeamSummary(
            id=str(team.id),
            name=team.name,
            discipline=team.discipline,
            status=team.status.value,
            weight=team.weight,
            activation_mode=team.activation_mode.value,
            min_agents=team.min_agents,
            is_system=team.is_system,
            created_by=team.created_by,
            created_at=team.created_at.isoformat(),
            agent_count=total_agents,
            active_agent_count=active_agents,
            data_keys=team.data_keys or [],
        ))

    return summaries
