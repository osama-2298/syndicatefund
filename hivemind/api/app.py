"""Hivemind FastAPI application."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import FastAPI

from hivemind.api.routes import agents, contributors, cycles, portfolio, teams
from hivemind.config import settings

logger = structlog.get_logger()

CYCLE_INTERVAL_HOURS = 4


async def _load_registry():
    """Load the agent registry from the database."""
    from hivemind.core.agent_registry import AgentRegistry
    from hivemind.db.session import async_session_factory

    async with async_session_factory() as session:
        registry = AgentRegistry(session)
        await registry.load_all()
        return registry


async def _background_cycle_loop(shutdown_event: asyncio.Event):
    """Background task that runs the analysis pipeline every 4 hours."""
    import sys
    print("[CYCLE] Background cycle loop starting...", flush=True)

    try:
        from hivemind.data.binance_client import BinanceClient
        binance = BinanceClient()
        print(f"[CYCLE] BinanceClient created with {binance._base_url}", flush=True)
    except Exception as e:
        print(f"[CYCLE] FATAL: Failed to create BinanceClient: {e}", flush=True)
        return

    try:
        while not shutdown_event.is_set():
            # Load fresh registry each cycle (picks up new agents/teams)
            try:
                registry = await _load_registry()
            except Exception as e:
                logger.error("registry_load_failed", error=str(e))
                registry = None  # Fall back to hardcoded agents

            # Run pipeline in a thread (it's synchronous)
            try:
                print(f"[CYCLE] Starting pipeline run (registry={'loaded' if registry else 'none'})...", flush=True)
                from hivemind.main import run_pipeline
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, lambda: run_pipeline(binance=binance, registry=registry)
                )
                print("[CYCLE] Pipeline completed successfully", flush=True)
            except Exception as e:
                import traceback
                logger.error("cycle_failed", error=str(e), traceback=traceback.format_exc())

            # Sleep until next 4H boundary
            now = datetime.now(timezone.utc)
            current_slot = (now.hour // CYCLE_INTERVAL_HOURS) * CYCLE_INTERVAL_HOURS
            next_slot = current_slot + CYCLE_INTERVAL_HOURS
            boundary = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=next_slot)
            wait_secs = max(30, (boundary - datetime.now(timezone.utc)).total_seconds())

            logger.info("cycle_sleeping", next_run=boundary.isoformat(), wait_secs=round(wait_secs))

            # Sleep in chunks so we can respond to shutdown
            sleep_end = time.monotonic() + wait_secs
            while time.monotonic() < sleep_end and not shutdown_event.is_set():
                remaining = sleep_end - time.monotonic()
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=min(remaining, 30))
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    pass  # Continue sleeping
    finally:
        binance.close()
        logger.info("cycle_loop_stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    shutdown_event = asyncio.Event()

    # Start background cycle loop
    cycle_task = asyncio.create_task(_background_cycle_loop(shutdown_event))

    yield

    # Shutdown
    shutdown_event.set()
    cycle_task.cancel()
    try:
        await cycle_task
    except asyncio.CancelledError:
        pass

    from hivemind.db.session import engine
    await engine.dispose()


app = FastAPI(
    title="Hivemind",
    description="Scalable Multi-Agent Crypto Analysis Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend to call the API
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://hivemindfund.com",
        "https://www.hivemindfund.com",
        "http://localhost:3000",  # Local dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount route modules
app.include_router(contributors.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(teams.router, prefix="/api/v1")
app.include_router(cycles.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "hivemind"}
