"""Pipeline event system — captures every major decision for the frontend."""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class PipelineEvent:
    """In-memory event before DB persistence."""

    event_type: str
    stage: str
    actor: str
    title: str
    detail: dict[str, Any] | None = None
    elapsed_ms: int | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        d = asdict(self)
        # Cap text fields in detail to 200 chars
        if d.get("detail"):
            d["detail"] = _cap_detail(d["detail"])
        return d


def _cap_detail(detail: dict, max_len: int = 200) -> dict:
    """Cap string values in detail JSONB to max_len characters."""
    result = {}
    for k, v in detail.items():
        if isinstance(v, str) and len(v) > max_len:
            result[k] = v[:max_len] + "..."
        elif isinstance(v, dict):
            result[k] = _cap_detail(v, max_len)
        elif isinstance(v, list):
            result[k] = [
                _cap_detail(item, max_len) if isinstance(item, dict)
                else (item[:max_len] + "..." if isinstance(item, str) and len(item) > max_len else item)
                for item in v
            ]
        else:
            result[k] = v
    return result


class EventCollector:
    """Thread-safe collector that accumulates events during a cycle."""

    def __init__(self):
        self._events: list[PipelineEvent] = []
        self._lock = threading.Lock()
        self._start_time = time.monotonic()

    def emit(
        self,
        event_type: str,
        stage: str,
        actor: str,
        title: str,
        detail: dict[str, Any] | None = None,
        elapsed_ms: int | None = None,
    ) -> None:
        event = PipelineEvent(
            event_type=event_type,
            stage=stage,
            actor=actor,
            title=title,
            detail=detail,
            elapsed_ms=elapsed_ms,
        )
        with self._lock:
            self._events.append(event)

    @property
    def events(self) -> list[PipelineEvent]:
        with self._lock:
            return list(self._events)

    def __len__(self) -> int:
        with self._lock:
            return len(self._events)


# Module-level singleton
_current_collector: EventCollector | None = None
_collector_lock = threading.Lock()


def start_cycle_collector() -> EventCollector:
    """Create a new collector for this cycle."""
    global _current_collector
    with _collector_lock:
        _current_collector = EventCollector()
        return _current_collector


def get_collector() -> EventCollector | None:
    """Get the current cycle's collector."""
    return _current_collector


def emit_event(
    event_type: str,
    stage: str,
    actor: str,
    title: str,
    detail: dict[str, Any] | None = None,
    elapsed_ms: int | None = None,
) -> None:
    """Convenience function — appends to current collector (no-op if none active)."""
    collector = _current_collector
    if collector is not None:
        collector.emit(event_type, stage, actor, title, detail, elapsed_ms)


async def persist_events(cycle_id: int | None, collector: EventCollector) -> None:
    """Bulk-insert all events from the collector to the database."""
    from syndicate.db.models import PipelineEventRow
    from syndicate.db.session import async_session_factory

    events = collector.events
    if not events:
        return

    try:
        async with async_session_factory() as session:
            for ev in events:
                row = PipelineEventRow(
                    cycle_id=cycle_id,
                    event_type=ev.event_type,
                    timestamp=datetime.fromisoformat(ev.timestamp),
                    stage=ev.stage,
                    actor=ev.actor,
                    title=ev.title,
                    detail=ev.detail if ev.detail else None,
                    elapsed_ms=ev.elapsed_ms,
                )
                session.add(row)
            await session.commit()
        logger.info("events_persisted", count=len(events), cycle_id=cycle_id)
    except Exception as e:
        logger.warning("events_persist_failed", error=str(e))


def save_events_json(collector: EventCollector) -> None:
    """Persist events to data/latest_events.json as a fallback."""
    events = collector.events
    if not events:
        return
    try:
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(events),
            "events": [ev.to_dict() for ev in events],
        }
        path = Path("data/latest_events.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, default=str))
    except Exception:
        pass
