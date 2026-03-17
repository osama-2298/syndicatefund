"""Agent comms endpoints — powers the Transparency Feed."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from syndicate.db.models import AgentCommRow
from syndicate.db.session import get_db

router = APIRouter(prefix="/comms", tags=["comms"])


class CommResponse(BaseModel):
    id: str
    cycle_id: int | None
    comm_type: str
    agent_class: str | None
    agent_name: str
    team: str | None
    symbol: str | None
    direction: str | None
    conviction: int | None
    content: str
    metadata: dict | None
    created_at: str


def _row_to_response(row: AgentCommRow) -> CommResponse:
    return CommResponse(
        id=str(row.id),
        cycle_id=row.cycle_id,
        comm_type=row.comm_type,
        agent_class=row.agent_class,
        agent_name=row.agent_name,
        team=row.team,
        symbol=row.symbol,
        direction=row.direction,
        conviction=row.conviction,
        content=row.content,
        metadata=row.metadata_,
        created_at=row.created_at.isoformat(),
    )


@router.get("", response_model=list[CommResponse])
async def list_comms(
    db: AsyncSession = Depends(get_db),
    agent_class: str | None = Query(None),
    team: str | None = Query(None),
    symbol: str | None = Query(None),
    comm_type: str | None = Query(None),
    cycle_id: int | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    """List agent comms with optional filters. Falls back to JSON file."""
    query = select(AgentCommRow)

    if cycle_id is not None:
        query = query.where(AgentCommRow.cycle_id == cycle_id)
    if agent_class is not None:
        query = query.where(AgentCommRow.agent_class == agent_class)
    if team is not None:
        query = query.where(AgentCommRow.team == team)
    if symbol is not None:
        query = query.where(AgentCommRow.symbol == symbol)
    if comm_type is not None:
        query = query.where(AgentCommRow.comm_type == comm_type)

    query = query.order_by(desc(AgentCommRow.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.scalars().all()
    if rows:
        return [_row_to_response(r) for r in rows]

    # Fallback to JSON file
    return _comms_from_json(
        agent_class=agent_class, team=team, symbol=symbol,
        comm_type=comm_type, limit=limit,
    )


@router.get("/latest", response_model=list[CommResponse])
async def latest_comms(db: AsyncSession = Depends(get_db)):
    """Return comms from the most recent cycle only."""
    # Find latest cycle_id
    latest_query = (
        select(AgentCommRow.cycle_id)
        .where(AgentCommRow.cycle_id.isnot(None))
        .order_by(desc(AgentCommRow.created_at))
        .limit(1)
    )
    result = await db.execute(latest_query)
    latest_cycle_id = result.scalar_one_or_none()

    if latest_cycle_id is not None:
        query = (
            select(AgentCommRow)
            .where(AgentCommRow.cycle_id == latest_cycle_id)
            .order_by(AgentCommRow.created_at)
        )
        result = await db.execute(query)
        rows = result.scalars().all()
        if rows:
            return [_row_to_response(r) for r in rows]

    # Fallback to JSON
    return _comms_from_json(limit=500)


def _comms_from_json(
    agent_class: str | None = None,
    team: str | None = None,
    symbol: str | None = None,
    comm_type: str | None = None,
    limit: int = 100,
) -> list[CommResponse]:
    """Read comms from the JSON fallback file."""
    json_path = Path("data/latest_comms.json")
    if not json_path.exists():
        return []

    try:
        data = json.loads(json_path.read_text())
        if not isinstance(data, list):
            return []

        comms = []
        for i, c in enumerate(data):
            if agent_class and c.get("agent_class") != agent_class:
                continue
            if team and c.get("team") != team:
                continue
            if symbol and c.get("symbol") != symbol:
                continue
            if comm_type and c.get("comm_type") != comm_type:
                continue

            comms.append(CommResponse(
                id=f"json-comm-{i}",
                cycle_id=None,
                comm_type=c.get("comm_type", ""),
                agent_class=c.get("agent_class"),
                agent_name=c.get("agent_name", ""),
                team=c.get("team"),
                symbol=c.get("symbol"),
                direction=c.get("direction"),
                conviction=c.get("conviction"),
                content=c.get("content", ""),
                metadata=c.get("metadata"),
                created_at=c.get("created_at", ""),
            ))

            if len(comms) >= limit:
                break

        return comms
    except Exception:
        return []
