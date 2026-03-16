"""Board session endpoints — powers the Board Room page."""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from syndicate.db.models import BoardDecisionRow
from syndicate.db.session import get_db

router = APIRouter(prefix="/board", tags=["board"])


class BoardDecision(BaseModel):
    id: str
    decision_type: str
    agent_id: str | None
    team_id: str | None
    reasoning: str | None
    decided_by: str
    created_at: str


class BoardSession(BaseModel):
    session_id: str
    decisions: list[BoardDecision]
    created_at: str


@router.get("/sessions", response_model=list[BoardSession])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, le=50),
):
    """List board sessions with their decisions, grouped by session_id."""
    query = (
        select(BoardDecisionRow)
        .order_by(desc(BoardDecisionRow.created_at))
        .limit(limit * 10)  # Fetch extra rows since we group by session
    )
    result = await db.execute(query)
    rows = result.scalars().all()

    # Group by session_id
    sessions: dict[str, list[BoardDecisionRow]] = defaultdict(list)
    for row in rows:
        sessions[str(row.session_id)].append(row)

    # Build response, limited to `limit` sessions
    response = []
    for session_id, decisions in list(sessions.items())[:limit]:
        response.append(
            BoardSession(
                session_id=session_id,
                created_at=decisions[0].created_at.isoformat(),
                decisions=[
                    BoardDecision(
                        id=str(d.id),
                        decision_type=d.decision_type,
                        agent_id=str(d.agent_id) if d.agent_id else None,
                        team_id=str(d.team_id) if d.team_id else None,
                        reasoning=d.reasoning,
                        decided_by=d.decided_by,
                        created_at=d.created_at.isoformat(),
                    )
                    for d in decisions
                ],
            )
        )

    return response
