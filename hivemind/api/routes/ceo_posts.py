"""CEO blog posts, memos, and briefings endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from hivemind.db.models import CeoPostRow
from hivemind.db.session import get_db

router = APIRouter(prefix="/ceo", tags=["ceo"])


class CeoPost(BaseModel):
    id: str
    post_type: str
    title: str
    content: str
    summary: str | None
    market_context: dict | None
    created_at: str


@router.get("/posts", response_model=list[CeoPost])
async def list_posts(
    db: AsyncSession = Depends(get_db),
    post_type: str | None = None,
    limit: int = 20,
):
    """List CEO posts (blogs, memos, briefings)."""
    query = select(CeoPostRow).order_by(desc(CeoPostRow.created_at)).limit(limit)
    if post_type:
        query = query.where(CeoPostRow.post_type == post_type)
    result = await db.execute(query)
    posts = result.scalars().all()
    return [
        CeoPost(
            id=str(p.id),
            post_type=p.post_type,
            title=p.title,
            content=p.content,
            summary=p.summary,
            market_context=p.market_context,
            created_at=p.created_at.isoformat(),
        )
        for p in posts
    ]


@router.get("/posts/latest")
async def latest_post(
    db: AsyncSession = Depends(get_db),
    post_type: str = "blog",
):
    """Get the most recent CEO post of a given type."""
    result = await db.execute(
        select(CeoPostRow)
        .where(CeoPostRow.post_type == post_type)
        .order_by(desc(CeoPostRow.created_at))
        .limit(1)
    )
    post = result.scalar_one_or_none()
    if post is None:
        return {"message": "No posts yet"}
    return CeoPost(
        id=str(post.id),
        post_type=post.post_type,
        title=post.title,
        content=post.content,
        summary=post.summary,
        market_context=post.market_context,
        created_at=post.created_at.isoformat(),
    )
