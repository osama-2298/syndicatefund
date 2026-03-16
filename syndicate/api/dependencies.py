"""FastAPI dependencies — authentication, database sessions."""

from __future__ import annotations

import hashlib
import secrets
from uuid import UUID

from fastapi import Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from syndicate.db.models import ContributorRow, ContributorStatus
from syndicate.db.session import get_db


def hash_token(token: str) -> str:
    """Hash a bearer token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_api_token() -> tuple[str, str]:
    """Generate a bearer token and its hash. Returns (token, hash)."""
    token = f"hvm_{secrets.token_urlsafe(32)}"
    return token, hash_token(token)


async def get_current_contributor(
    authorization: str = Header(..., description="Bearer token"),
    db: AsyncSession = Depends(get_db),
) -> ContributorRow:
    """Validate bearer token and return the contributor."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    token_hash = hash_token(token)

    result = await db.execute(
        select(ContributorRow).where(
            ContributorRow.api_token_hash == token_hash,
            ContributorRow.status == ContributorStatus.ACTIVE,
        )
    )
    contributor = result.scalar_one_or_none()

    if contributor is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return contributor


# Admin auth — simple shared secret for now (Phase 1)
ADMIN_TOKEN = "syndicate-admin"  # TODO: move to env var


async def require_admin(
    authorization: str = Header(...),
) -> bool:
    """Validate admin token."""
    token = authorization.removeprefix("Bearer ").strip()
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return True
