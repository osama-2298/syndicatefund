"""Agent leaderboard endpoint — agents ranked by accuracy."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func, case, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from syndicate.db.models import AgentRow, AgentStatusDB, SignalRow, SignalOutcome
from syndicate.db.session import get_db

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


class LeaderboardEntry(BaseModel):
    agent_id: str
    role: str
    agent_class: str | None
    team_name: str | None
    model: str
    provider: str
    status: str
    total_signals: int
    correct_signals: int
    accuracy: float
    streak_count: int
    streak_type: str  # "win" or "loss" or "none"


@router.get("", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    db: AsyncSession = Depends(get_db),
):
    """Agents ranked by accuracy (min 5 signals)."""
    query = (
        select(AgentRow)
        .options(joinedload(AgentRow.team))
        .where(AgentRow.total_signals >= 5)
        .where(AgentRow.status != AgentStatusDB.FIRED)
        .order_by(desc(
            case(
                (AgentRow.total_signals > 0,
                 AgentRow.correct_signals * 1.0 / AgentRow.total_signals),
                else_=0.0,
            )
        ))
    )
    result = await db.execute(query)
    agents = result.unique().scalars().all()

    if not agents:
        return []

    # Batch-load recent signals for all agents in one query (fixes N+1)
    from sqlalchemy import and_
    agent_ids = [a.id for a in agents]
    # Use window function to get last 20 signals per agent
    row_num = func.row_number().over(
        partition_by=SignalRow.agent_id,
        order_by=desc(SignalRow.created_at),
    ).label("rn")
    sub = (
        select(SignalRow.agent_id, SignalRow.outcome, row_num)
        .where(
            and_(
                SignalRow.agent_id.in_(agent_ids),
                SignalRow.outcome != SignalOutcome.PENDING,
            )
        )
        .subquery()
    )
    streak_result = await db.execute(
        select(sub.c.agent_id, sub.c.outcome)
        .where(sub.c.rn <= 20)
        .order_by(sub.c.agent_id, sub.c.rn)
    )
    # Group by agent
    from collections import defaultdict
    signals_by_agent: dict[str, list] = defaultdict(list)
    for row in streak_result.all():
        signals_by_agent[row.agent_id].append(row.outcome)

    entries = []
    for agent in agents:
        recent_outcomes = signals_by_agent.get(agent.id, [])

        streak_count = 0
        streak_type = "none"
        if recent_outcomes:
            first = recent_outcomes[0]
            streak_type = "win" if first == SignalOutcome.CORRECT else "loss"
            for outcome in recent_outcomes:
                if outcome == first:
                    streak_count += 1
                else:
                    break

        accuracy = agent.correct_signals / agent.total_signals if agent.total_signals > 0 else 0.0

        entries.append(
            LeaderboardEntry(
                agent_id=str(agent.id),
                role=agent.role,
                agent_class=agent.agent_class,
                team_name=agent.team.name if agent.team else None,
                model=agent.model,
                provider=agent.provider.value,
                status=agent.status.value,
                total_signals=agent.total_signals,
                correct_signals=agent.correct_signals,
                accuracy=round(accuracy, 4),
                streak_count=streak_count,
                streak_type=streak_type,
            )
        )

    return entries
