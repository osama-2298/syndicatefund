"""Pipeline event endpoints — powers the Activity Feed and Cycle Replay."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from syndicate.db.models import PipelineEventRow, PipelineEventType
from syndicate.db.session import get_db

router = APIRouter(prefix="/events", tags=["events"])


class EventResponse(BaseModel):
    id: str
    cycle_id: int | None
    event_type: str
    timestamp: str
    stage: str
    actor: str
    title: str
    detail: dict | None
    elapsed_ms: int | None


def _row_to_response(row: PipelineEventRow) -> EventResponse:
    return EventResponse(
        id=str(row.id),
        cycle_id=row.cycle_id,
        event_type=row.event_type.value,
        timestamp=row.timestamp.isoformat(),
        stage=row.stage,
        actor=row.actor,
        title=row.title,
        detail=row.detail,
        elapsed_ms=row.elapsed_ms,
    )


@router.get("", response_model=list[EventResponse])
async def list_events(
    db: AsyncSession = Depends(get_db),
    cycle_id: int | None = Query(None),
    event_type: str | None = Query(None),
    limit: int = Query(50, le=200),
):
    """List pipeline events with optional filters. Falls back to snapshot files."""
    query = select(PipelineEventRow)

    if cycle_id is not None:
        query = query.where(PipelineEventRow.cycle_id == cycle_id)
    if event_type is not None:
        try:
            evt = PipelineEventType(event_type)
            query = query.where(PipelineEventRow.event_type == evt)
        except ValueError:
            pass

    query = query.order_by(desc(PipelineEventRow.timestamp)).limit(limit)
    result = await db.execute(query)
    rows = result.scalars().all()
    if rows:
        return [_row_to_response(r) for r in rows]

    # Fallback: reconstruct filtered events from snapshot files
    return _events_from_snapshots(event_type=event_type, limit=limit)


def _events_from_snapshots(event_type: str | None = None, limit: int = 50) -> list[EventResponse]:
    """Reconstruct events from cycle snapshot files when DB is empty."""
    snapshots_dir = Path("data/cycles")
    if not snapshots_dir.exists():
        return []
    files = sorted(snapshots_dir.glob("cycle_*.json"), reverse=True)[:10]
    all_events: list[EventResponse] = []

    for f in files:
        try:
            snap = json.loads(f.read_text())
            ts = snap.get("timestamp", "")

            events: list[tuple[str, str, str, str, dict | None, int | None]] = []
            # (event_type, stage, actor, title, detail, elapsed_ms)

            if snap.get("ceo_directive"):
                d = snap["ceo_directive"]
                events.append(("ceo_directive", "ceo", "CEO Marcus Blackwell",
                    f"Regime: {(d.get('regime', '?')).upper()} — Risk multiplier: {d.get('risk_multiplier', '?')}x",
                    d, snap.get("ceo_elapsed_ms")))

            if snap.get("coo_selection", {}).get("selected_coins"):
                coins = snap["coo_selection"]["selected_coins"]
                events.append(("coo_selection", "coin_selection", "COO Elena Vasquez",
                    f"Selected {len(coins)} coins: {', '.join(c.replace('USDT','') for c in coins)}",
                    snap["coo_selection"], snap.get("coo_elapsed_ms")))

            if snap.get("cro_rules"):
                events.append(("cro_rules", "risk_rules", "CRO Tobias Richter",
                    f"Risk limits set", snap["cro_rules"], snap.get("cro_elapsed_ms")))

            for sig in snap.get("team_signals", []):
                events.append(("team_signal", "agent_analysis", f"Team {sig.get('team', '?')}",
                    f"{sig.get('team','?')} → {sig.get('action','?')} {sig.get('symbol','').replace('USDT','')} ({round(sig.get('confidence',0)*100)}% conf)",
                    sig, sig.get("elapsed_ms")))

            for agg in snap.get("aggregated_signals", []):
                sym = agg.get("symbol", "").replace("USDT", "")
                events.append(("aggregation_result", "aggregation", "Aggregator",
                    f"{sym} → {agg.get('action','?')} ({round(agg.get('confidence',0)*100)}% conf)",
                    agg, None))

            for dis in snap.get("disagreements", []):
                sym = dis.get("symbol", "").replace("USDT", "")
                events.append(("disagreement", "aggregation", "Signal Aggregator",
                    f"POLARIZED: {sym} — {round(dis.get('polarization',0)*100)}% disagreement",
                    dis, None))

            for v in snap.get("verdicts", []):
                sym = v.get("symbol", "").replace("USDT", "")
                events.append(("verdict", "verdicts", "System",
                    f"{sym} → {'BLOCKED' if v.get('blocked') else v.get('action','?')}" + (f" ({v.get('reason','')})" if v.get('reason') else ""),
                    v, None))

            for t in snap.get("trades_executed", []):
                sym = t.get("symbol", "").replace("USDT", "")
                events.append(("trade_executed", "execution", "Execution Kai Nakamura",
                    f"{t.get('side','?')} {sym} @ ${t.get('price',0):,.2f}", t, None))

            for ex in snap.get("trade_exits", []):
                sym = ex.get("symbol", "").replace("USDT", "")
                events.append(("trade_closed", "trade_monitor", "Trade Monitor",
                    f"Closed {sym} — {ex.get('exit_reason','?')}", ex, None))

            if snap.get("ceo_review"):
                events.append(("ceo_review", "review", "CEO Marcus Blackwell",
                    "CEO reviewed cycle performance", snap["ceo_review"], snap.get("ceo_review_elapsed_ms")))

            # Filter by event_type if specified
            for i, (etype, stage, actor, title, detail, elapsed) in enumerate(events):
                if event_type and etype != event_type:
                    continue
                all_events.append(EventResponse(
                    id=f"snap-{f.stem}-{i}",
                    cycle_id=None,
                    event_type=etype,
                    timestamp=ts,
                    stage=stage,
                    actor=actor,
                    title=title,
                    detail=detail,
                    elapsed_ms=elapsed,
                ))
        except Exception:
            continue

    return all_events[:limit]


@router.get("/live", response_model=list[EventResponse])
async def live_events(
    db: AsyncSession = Depends(get_db),
):
    """Returns events from the latest cycle, ordered chronologically.

    Falls back to data/latest_events.json if DB is empty.
    """
    # Find the latest cycle_id that has events
    latest_query = (
        select(PipelineEventRow.cycle_id)
        .where(PipelineEventRow.cycle_id.isnot(None))
        .order_by(desc(PipelineEventRow.timestamp))
        .limit(1)
    )
    result = await db.execute(latest_query)
    latest_cycle_id = result.scalar_one_or_none()

    if latest_cycle_id is not None:
        query = (
            select(PipelineEventRow)
            .where(PipelineEventRow.cycle_id == latest_cycle_id)
            .order_by(PipelineEventRow.timestamp)
        )
        result = await db.execute(query)
        rows = result.scalars().all()
        if rows:
            return [_row_to_response(r) for r in rows]

    # Also try events with no cycle_id (latest batch)
    query = (
        select(PipelineEventRow)
        .order_by(desc(PipelineEventRow.timestamp))
        .limit(50)
    )
    result = await db.execute(query)
    rows = result.scalars().all()
    if rows:
        return [_row_to_response(r) for r in reversed(rows)]

    # Fallback to JSON file
    json_path = Path("data/latest_events.json")
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text())
            events = data.get("events", [])
            if events:
                return [
                    EventResponse(
                        id=ev.get("id", ""),
                        cycle_id=None,
                        event_type=ev.get("event_type", ""),
                        timestamp=ev.get("timestamp", ""),
                        stage=ev.get("stage", ""),
                        actor=ev.get("actor", ""),
                        title=ev.get("title", ""),
                        detail=ev.get("detail"),
                        elapsed_ms=ev.get("elapsed_ms"),
                    )
                    for ev in events
                ]
        except Exception:
            pass

    # Last resort: reconstruct events from latest cycle snapshot
    snapshots_dir = Path("data/cycles")
    if snapshots_dir.exists():
        files = sorted(snapshots_dir.glob("cycle_*.json"), reverse=True)
        if files:
            try:
                snap = json.loads(files[0].read_text())
                events = []
                ts = snap.get("timestamp", "")

                # Reconstruct key events from snapshot data
                if snap.get("ceo_directive"):
                    d = snap["ceo_directive"]
                    events.append(EventResponse(id="snap-ceo", cycle_id=None, event_type="ceo_directive", timestamp=ts,
                        stage="ceo", actor="CEO Marcus Blackwell",
                        title=f"Regime: {(d.get('regime', '?')).upper()} — Risk multiplier: {d.get('risk_multiplier', '?')}x",
                        detail=d, elapsed_ms=snap.get("ceo_elapsed_ms")))

                if snap.get("coo_selection", {}).get("selected_coins"):
                    coins = snap["coo_selection"]["selected_coins"]
                    events.append(EventResponse(id="snap-coo", cycle_id=None, event_type="coo_selection", timestamp=ts,
                        stage="coin_selection", actor="COO Elena Vasquez",
                        title=f"Selected {len(coins)} coins: {', '.join(c.replace('USDT','') for c in coins)}",
                        detail=snap["coo_selection"], elapsed_ms=snap.get("coo_elapsed_ms")))

                for sig in snap.get("aggregated_signals", []):
                    sym = sig.get("symbol", "").replace("USDT", "")
                    events.append(EventResponse(id=f"snap-agg-{sym}", cycle_id=None, event_type="aggregation_result", timestamp=ts,
                        stage="aggregation", actor="Aggregator",
                        title=f"{sym} → {sig.get('action', '?')} ({round(sig.get('confidence', 0) * 100)}% conf)",
                        detail=sig, elapsed_ms=None))

                for dis in snap.get("disagreements", []):
                    sym = dis.get("symbol", "").replace("USDT", "")
                    events.append(EventResponse(id=f"snap-dis-{sym}", cycle_id=None, event_type="disagreement", timestamp=ts,
                        stage="aggregation", actor="Signal Aggregator",
                        title=f"POLARIZED: {sym} — {round(dis.get('polarization', 0) * 100)}% disagreement",
                        detail=dis, elapsed_ms=None))

                for v in snap.get("verdicts", []):
                    sym = v.get("symbol", "").replace("USDT", "")
                    events.append(EventResponse(id=f"snap-v-{sym}", cycle_id=None, event_type="verdict", timestamp=ts,
                        stage="verdicts", actor="System",
                        title=f"{sym} → {'BLOCKED' if v.get('blocked') else v.get('action', '?')}" + (f" ({v.get('reason', '')})" if v.get('reason') else ""),
                        detail=v, elapsed_ms=None))

                for t in snap.get("trades_executed", []):
                    sym = t.get("symbol", "").replace("USDT", "")
                    events.append(EventResponse(id=f"snap-t-{sym}", cycle_id=None, event_type="trade_executed", timestamp=ts,
                        stage="execution", actor="Execution Kai Nakamura",
                        title=f"{t.get('side', '?')} {sym} @ ${t.get('price', 0):,.2f}",
                        detail=t, elapsed_ms=None))

                if events:
                    return events
            except Exception:
                pass

    return []
