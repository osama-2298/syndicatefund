"""API routes for the master DATA knowledge base."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["data"])

DATA_FILE = Path(__file__).resolve().parents[3] / "DATA.md"


class DataUpdateRequest(BaseModel):
    """Request body for updating the DATA knowledge base."""
    market_snapshot: dict[str, Any] | None = None
    macro_summary: str | None = None
    sector_alerts: list[dict[str, str]] | None = None
    crypto_signals: dict[str, Any] | None = None
    custom_notes: str | None = None


@router.get("/data/knowledge-base")
async def get_knowledge_base():
    """Return the current DATA.md content."""
    if not DATA_FILE.exists():
        raise HTTPException(status_code=404, detail="DATA.md not found")
    content = DATA_FILE.read_text(encoding="utf-8")
    return {"content": content, "lines": content.count("\n") + 1}


@router.get("/data/knowledge-base/summary")
async def get_knowledge_base_summary():
    """Return metadata about the knowledge base."""
    if not DATA_FILE.exists():
        raise HTTPException(status_code=404, detail="DATA.md not found")
    content = DATA_FILE.read_text(encoding="utf-8")
    lines = content.count("\n") + 1
    sections = [
        line.strip("# ").strip()
        for line in content.split("\n")
        if line.startswith("# PART")
    ]
    has_updates = "# LATEST UPDATES" in content
    return {
        "lines": lines,
        "chars": len(content),
        "sections": sections,
        "has_latest_updates": has_updates,
    }


@router.post("/data/knowledge-base/refresh")
async def refresh_knowledge_base(body: DataUpdateRequest):
    """Update the DATA knowledge base with new market intelligence."""
    from syndicate.research.data_updater import refresh_data_file

    success = refresh_data_file(
        market_snapshot=body.market_snapshot,
        macro_summary=body.macro_summary,
        sector_alerts=body.sector_alerts,
        crypto_signals=body.crypto_signals,
        custom_notes=body.custom_notes,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update DATA.md")

    return {"status": "updated", "message": "DATA.md refreshed and agents reloaded"}
