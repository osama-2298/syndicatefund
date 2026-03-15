"""Cycle orchestrator — runs the analysis pipeline with dynamic team/agent discovery."""

from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal

import structlog

from hivemind.config import settings

logger = structlog.get_logger()


def run_single_agent_dynamic(agent_def, registry, symbol, data):
    """Run a single agent (founding or dynamic). Thread-safe."""
    agent = registry.instantiate_agent(agent_def, symbol)
    t0 = time.monotonic()
    signal = agent.analyze(data)
    elapsed = time.monotonic() - t0
    return signal, agent_def.role, elapsed


def run_team_dynamic(
    team_name: str,
    team_agents,  # list[AgentDefinition]
    team_manager_prompt: str | None,
    data: dict,
    symbol: str,
    registry,
    executor: ThreadPoolExecutor,
):
    """Run all agents in a team in parallel, then synthesize through the manager."""
    # Launch all sub-agents in parallel
    futures: list[Future] = []
    for agent_def in team_agents:
        fut = executor.submit(
            run_single_agent_dynamic, agent_def, registry, symbol, data
        )
        futures.append(fut)

    # Collect results
    agent_signals = []
    for fut in futures:
        try:
            signal, role, elapsed = fut.result()
            agent_signals.append(signal)
            logger.debug("agent_completed", role=role, elapsed=f"{elapsed:.1f}s")
        except Exception as e:
            logger.error("agent_failed", error=str(e))

    if not agent_signals:
        return None

    # Manager synthesizes
    manager = registry.get_manager_for_team(team_name, team_manager_prompt)
    t0 = time.monotonic()
    team_signal = manager.synthesize(agent_signals, symbol)
    mgr_elapsed = time.monotonic() - t0

    final_signal = team_signal.to_signal()
    logger.debug("team_completed", team=team_name, elapsed=f"{mgr_elapsed:.1f}s")
    return final_signal


async def record_cycle_to_db(
    db_session,
    started_at: datetime,
    completed_at: datetime,
    duration_secs: float,
    regime: str,
    coins_analyzed: int,
    signals_produced: int,
    orders_executed: int,
    portfolio_value: float,
    error: str | None = None,
) -> int:
    """Record a completed cycle to the database. Returns cycle ID."""
    from hivemind.db.models import CycleRow

    cycle = CycleRow(
        started_at=started_at,
        completed_at=completed_at,
        duration_secs=duration_secs,
        regime=regime,
        coins_analyzed=coins_analyzed,
        signals_produced=signals_produced,
        orders_executed=orders_executed,
        portfolio_value=Decimal(str(round(portfolio_value, 4))),
        error=error,
    )
    db_session.add(cycle)
    await db_session.flush()
    return cycle.id
