"""Contributor registration and profile endpoints."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from syndicate.api.dependencies import generate_api_token, get_current_contributor
from syndicate.core.cost_estimator import estimate_monthly_cost
from syndicate.core.encryption import encrypt_api_key
from syndicate.db.models import AgentRow, AgentStatusDB, ContributorRow, ProviderType
from syndicate.db.session import get_db

router = APIRouter(prefix="/contributors", tags=["contributors"])


async def _validate_api_key(
    provider: ProviderType,
    api_key_anthropic: str | None = None,
    api_key_openai: str | None = None,
    api_key_google: str | None = None,
) -> str | None:
    """Validate an API key by making a minimal real call. Returns error message or None if valid."""
    import httpx

    async with httpx.AsyncClient(timeout=15.0) as http:
        try:
            if provider == ProviderType.ANTHROPIC and api_key_anthropic:
                resp = await http.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key_anthropic,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-haiku-4-5-20251001",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )
                if resp.status_code == 401:
                    return "Invalid Anthropic API key. Please check and try again."
                if resp.status_code == 403:
                    return "Anthropic API key is disabled or lacks permissions."
                if resp.status_code not in (200, 429):
                    return f"Anthropic API error: {resp.status_code}"

            elif provider == ProviderType.OPENAI and api_key_openai:
                resp = await http.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key_openai}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )
                if resp.status_code == 401:
                    return "Invalid OpenAI API key. Please check and try again."
                if resp.status_code == 403:
                    return "OpenAI API key is disabled or lacks permissions."
                if resp.status_code not in (200, 429):
                    return f"OpenAI API error: {resp.status_code}"

            elif provider == ProviderType.GOOGLE and api_key_google:
                resp = await http.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key_google}",
                    headers={"Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": "hi"}]}]},
                )
                if resp.status_code == 400 and "API_KEY_INVALID" in resp.text:
                    return "Invalid Google API key. Please check and try again."
                if resp.status_code == 403:
                    return "Google API key lacks permissions for Gemini."
                if resp.status_code not in (200, 429):
                    return f"Google API error: {resp.status_code}"

        except httpx.TimeoutException:
            return None  # Timeout is not a key validity issue, let it through
        except Exception as e:
            return f"Key validation failed: {str(e)[:100]}"

    return None  # Valid


class RegisterRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)
    email: str | None = None
    api_key_anthropic: str | None = None
    api_key_openai: str | None = None
    api_key_google: str | None = None
    max_agents: int = Field(default=2, ge=1, le=20)
    preferred_model: str = "claude-sonnet-4-6"
    cost_limit_usd: float | None = None


class RegisterResponse(BaseModel):
    contributor_id: str
    bearer_token: str
    agents_created: int
    estimated_monthly_cost_usd: float
    message: str


@router.post("/register", response_model=RegisterResponse)
async def register(
    req: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new contributor with API key(s) and desired agent count."""
    # Validate at least one API key
    if not any([req.api_key_anthropic, req.api_key_openai, req.api_key_google]):
        raise HTTPException(status_code=400, detail="At least one API key is required")

    # Determine provider from the key provided
    if req.api_key_anthropic:
        provider = ProviderType.ANTHROPIC
    elif req.api_key_openai:
        provider = ProviderType.OPENAI
    else:
        provider = ProviderType.GOOGLE

    # Validate the API key by making a real call
    validation_error = await _validate_api_key(
        provider=provider,
        api_key_anthropic=req.api_key_anthropic,
        api_key_openai=req.api_key_openai,
        api_key_google=req.api_key_google,
    )
    if validation_error:
        raise HTTPException(status_code=400, detail=validation_error)

    # Generate bearer token
    token, token_hash = generate_api_token()

    # Create contributor
    contributor = ContributorRow(
        display_name=req.display_name,
        email=req.email,
        api_key_anthropic_enc=encrypt_api_key(req.api_key_anthropic) if req.api_key_anthropic else None,
        api_key_openai_enc=encrypt_api_key(req.api_key_openai) if req.api_key_openai else None,
        api_key_google_enc=encrypt_api_key(req.api_key_google) if req.api_key_google else None,
        max_agents=req.max_agents,
        cost_limit_usd=Decimal(str(req.cost_limit_usd)) if req.cost_limit_usd else None,
        api_token_hash=token_hash,
    )
    db.add(contributor)
    await db.flush()  # Get the ID

    # Create registered (unassigned) agents
    agents_created = 0
    for i in range(req.max_agents):
        agent = AgentRow(
            contributor_id=contributor.id,
            role=f"analyst_{i + 1}",
            model=req.preferred_model,
            provider=provider,
            status=AgentStatusDB.REGISTERED,
            quarantine_signals_remaining=10,
        )
        db.add(agent)
        agents_created += 1

    # Cost estimate
    monthly_cost = estimate_monthly_cost(req.preferred_model, req.max_agents)

    # Trigger Board of Directors to assign the new agents (background)
    import asyncio
    from syndicate.board.session import BoardSession
    from syndicate.db.session import async_session_factory

    async def _convene_board():
        try:
            async with async_session_factory() as board_db:
                board = BoardSession(board_db)
                await board.convene(trigger="new_contributor")
                await board_db.commit()
        except Exception as e:
            import structlog
            structlog.get_logger().error("board_convene_failed", error=str(e))

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_convene_board())
    except RuntimeError:
        pass  # No event loop — skip board (e.g., testing)

    return RegisterResponse(
        contributor_id=str(contributor.id),
        bearer_token=token,
        agents_created=agents_created,
        estimated_monthly_cost_usd=float(monthly_cost),
        message=f"Welcome to Syndicate! {agents_created} agents created. Board will assign them shortly.",
    )


class ContributorProfile(BaseModel):
    id: str
    display_name: str
    email: str | None
    max_agents: int
    cost_limit_usd: float | None
    total_cost_usd: float
    status: str
    created_at: str
    agent_count: int


@router.get("/me", response_model=ContributorProfile)
async def get_me(
    contributor: ContributorRow = Depends(get_current_contributor),
    db: AsyncSession = Depends(get_db),
):
    """Get current contributor profile and usage."""
    # Count agents
    result = await db.execute(
        select(AgentRow).where(AgentRow.contributor_id == contributor.id)
    )
    agents = result.scalars().all()

    return ContributorProfile(
        id=str(contributor.id),
        display_name=contributor.display_name,
        email=contributor.email,
        max_agents=contributor.max_agents,
        cost_limit_usd=float(contributor.cost_limit_usd) if contributor.cost_limit_usd else None,
        total_cost_usd=float(contributor.total_cost_usd),
        status=contributor.status.value,
        created_at=contributor.created_at.isoformat(),
        agent_count=len(agents),
    )
