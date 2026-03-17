"""Moltbook posts API — serves the audit log of autonomous Moltbook posts."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/moltbook", tags=["moltbook"])

MOLTBOOK_PROFILE = "https://www.moltbook.com/u/marcus-blackwell"


class MoltbookPost(BaseModel):
    moltbook_post_id: str | None
    title: str
    content: str
    submolt: str
    posted_at: str


class MoltbookInfo(BaseModel):
    profile_url: str
    agent_name: str
    posts: list[MoltbookPost]
    total_posts: int


@router.get("/posts", response_model=MoltbookInfo)
async def list_moltbook_posts(limit: int = 50):
    """List all autonomous Moltbook posts with profile info."""
    posts_path = Path("data/moltbook_posts.json")
    posts: list[dict] = []
    if posts_path.exists():
        try:
            posts = json.loads(posts_path.read_text())
        except Exception:
            posts = []

    return MoltbookInfo(
        profile_url=MOLTBOOK_PROFILE,
        agent_name="marcus-blackwell",
        posts=[
            MoltbookPost(
                moltbook_post_id=p.get("moltbook_post_id"),
                title=p.get("title", ""),
                content=p.get("content", ""),
                submolt=p.get("submolt", "general"),
                posted_at=p.get("posted_at", ""),
            )
            for p in posts[:limit]
        ],
        total_posts=len(posts),
    )
