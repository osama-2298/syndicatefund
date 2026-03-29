"""Signal subscription API — latest aggregated signals."""

from __future__ import annotations
import json
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/latest")
async def get_latest_signals():
    """Return the most recent cycle's aggregated signals.

    Signals are delayed by one cycle (4h) for non-subscribers.
    """
    signals_path = Path("data/latest_signals.json")
    if not signals_path.exists():
        return {"signals": [], "cycle_timestamp": None}

    try:
        data = json.loads(signals_path.read_text())
        return data
    except Exception:
        return {"signals": [], "cycle_timestamp": None}
