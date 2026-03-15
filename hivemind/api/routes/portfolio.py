"""Portfolio state endpoints."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from hivemind.config import settings

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("")
async def get_portfolio():
    """Get current portfolio state from JSON file (Phase 1 — migrates to DB in Phase 3)."""
    portfolio_path = Path(settings.portfolio_state_path)

    if not portfolio_path.exists():
        return {
            "cash": 100_000.0,
            "positions": [],
            "total_value": 100_000.0,
            "total_realized_pnl": 0.0,
            "total_unrealized_pnl": 0.0,
        }

    try:
        data = json.loads(portfolio_path.read_text())
        return data
    except Exception:
        return {"error": "Failed to read portfolio state"}
