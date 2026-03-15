"""Backtest results API endpoint."""

from __future__ import annotations
import json
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.get("/latest")
async def get_latest_backtest():
    """Return the most recent backtest results."""
    results_path = Path("data/backtest_results.json")
    if not results_path.exists():
        return {"status": "no_backtest_run", "results": None}

    try:
        data = json.loads(results_path.read_text())
        return {"status": "ok", "results": data}
    except Exception:
        return {"status": "error", "results": None}
