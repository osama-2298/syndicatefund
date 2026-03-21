"""Intelligence / Fast Loop API endpoints."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Query

from syndicate.config import settings

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.get("/events")
async def get_intelligence_events(
    limit: int = Query(default=50, le=200),
    severity: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
):
    """Get fast loop intelligence events (news, whale alerts, risk actions).

    Filterable by severity (critical/high/medium/low) and event_type.
    Returns most recent first.
    """
    events_path = Path(settings.data_dir) / "fast_loop_events.json"

    if not events_path.exists():
        return {"events": [], "total": 0}

    try:
        all_events = json.loads(events_path.read_text())
        if not isinstance(all_events, list):
            return {"events": [], "total": 0}

        # Apply filters
        filtered = all_events
        if severity:
            filtered = [e for e in filtered if e.get("severity") == severity]
        if event_type:
            filtered = [e for e in filtered if e.get("event_type") == event_type]

        # Return most recent first
        filtered = list(reversed(filtered))[:limit]

        return {"events": filtered, "total": len(all_events)}

    except Exception:
        return {"events": [], "total": 0}


@router.get("/status")
async def get_intelligence_status():
    """Get current fast loop status — last run time, monitored symbols, event counts."""
    events_path = Path(settings.data_dir) / "fast_loop_events.json"
    risk_path = Path(settings.data_dir) / "latest_risk_snapshot.json"

    # Count recent events
    total_events = 0
    recent_critical = 0
    if events_path.exists():
        try:
            events = json.loads(events_path.read_text())
            total_events = len(events)
            # Count critical in last 50
            for e in events[-50:]:
                if e.get("severity") == "critical":
                    recent_critical += 1
        except Exception:
            pass

    # Get latest risk snapshot
    risk_data = {}
    if risk_path.exists():
        try:
            risk_data = json.loads(risk_path.read_text())
        except Exception:
            pass

    return {
        "fast_loop_enabled": True,
        "interval_minutes": getattr(settings, "fast_loop_interval_minutes", 15),
        "total_events_logged": total_events,
        "recent_critical_events": recent_critical,
        "latest_risk": risk_data,
    }


@router.get("/scouts")
async def get_active_scouts():
    """Get active scout bots and their monitoring assignments.

    Returns list of agents with role_type='scout' and their fast_loop_source.
    Falls back to empty list if no scouts are assigned yet.
    """
    try:
        from sqlalchemy import select
        from syndicate.db.models import AgentRow
        from syndicate.db.session import async_session_factory

        async with async_session_factory() as session:
            query = select(AgentRow).where(AgentRow.role_type == "scout")
            result = await session.execute(query)
            scouts = result.scalars().all()

            return {
                "scouts": [
                    {
                        "id": str(s.id),
                        "role": s.role,
                        "agent_class": s.agent_class,
                        "model": s.model,
                        "provider": s.provider.value if s.provider else None,
                        "status": s.status.value if s.status else None,
                        "fast_loop_source": s.fast_loop_source,
                        "last_active_at": s.last_active_at.isoformat() if s.last_active_at else None,
                    }
                    for s in scouts
                ],
                "total": len(scouts),
            }

    except Exception:
        # DB not available — return empty
        return {"scouts": [], "total": 0}
