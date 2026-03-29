"""Cycle orchestrator — runs the analysis pipeline with dynamic team/agent discovery."""

from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog

from hivemind.config import settings, LLMProvider

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


# ─────────────────────────────────────────────
#  PRE-CYCLE BRIEFING
# ─────────────────────────────────────────────


def build_pre_cycle_briefing(
    directive,
    intel: dict[str, Any],
    portfolio_summary: dict[str, Any],
) -> str:
    """Build a concise market context briefing shared with all agents before analysis.

    Returns a 3-5 line string summarizing: regime, key BTC level, recent events, F&G.
    This provides consistent context so every agent starts from the same baseline.
    """
    lines = []

    # Regime
    regime = directive.regime.value.upper() if hasattr(directive.regime, "value") else str(directive.regime).upper()
    risk_mult = getattr(directive, "risk_multiplier", 1.0)
    lines.append(f"Regime: {regime} (risk multiplier {risk_mult:.1f})")

    # BTC key level
    btc_price = portfolio_summary.get("btc_price", 0)
    if btc_price:
        lines.append(f"BTC: ${btc_price:,.0f}")
    else:
        # Try from intel
        fg = intel.get("fear_greed", {})
        if fg:
            lines.append(f"BTC: price unavailable")

    # Fear & Greed
    fg = intel.get("fear_greed", {})
    if fg:
        fg_val = fg.get("current_value", "?")
        fg_label = fg.get("current_label", "?")
        fg_trend = fg.get("trend", "?")
        lines.append(f"Fear & Greed: {fg_val}/100 ({fg_label}, trend: {fg_trend})")

    # Recent notable events from intelligence
    events = []
    reddit = intel.get("reddit_sentiment", {})
    if reddit and reddit.get("engagement_level") in ("high", "extreme"):
        ratio = round(reddit.get("sentiment_ratio", 0.5) * 100)
        events.append(f"Reddit {reddit['engagement_level']} engagement ({ratio}% bullish)")

    global_mkt = intel.get("global_market", {})
    if global_mkt:
        btc_dom = global_mkt.get("btc_dominance", 0)
        mkt_change = global_mkt.get("market_cap_change_24h_pct", 0)
        if abs(mkt_change) > 3:
            events.append(f"Market cap {mkt_change:+.1f}% 24h")
        if btc_dom:
            events.append(f"BTC dom {btc_dom:.1f}%")

    pred = intel.get("prediction_markets", {})
    if pred:
        highlights = pred.get("highlights", [])
        if highlights:
            top = highlights[0]
            q = top.get("question", "")[:40]
            events.append(f"Polymarket top: {q}")

    if events:
        lines.append(f"Events: {'; '.join(events)}")

    # Portfolio state
    portfolio_val = portfolio_summary.get("total_value", 0)
    return_pct = portfolio_summary.get("return_pct", 0)
    n_positions = portfolio_summary.get("n_positions", 0)
    lines.append(f"Portfolio: ${portfolio_val:,.0f} ({return_pct:+.1f}%) with {n_positions} open positions")

    return "\n".join(lines)


# ─────────────────────────────────────────────
#  DISSENT RESOLUTION
# ─────────────────────────────────────────────

_DISSENT_TOOL = {
    "name": "resolve_dissent",
    "description": "Resolve disagreement between polarized team signals and produce a confidence adjustment.",
    "input_schema": {
        "type": "object",
        "properties": {
            "confidence_multiplier": {
                "type": "number",
                "description": (
                    "Multiplier for the aggregated confidence (0.7 to 1.3). "
                    "< 1.0 = reduce confidence (dissent is well-founded), "
                    "> 1.0 = increase confidence (one side clearly stronger)."
                ),
            },
            "reasoning": {
                "type": "string",
                "description": "2-3 sentences explaining why this adjustment is warranted.",
            },
            "lean_toward": {
                "type": "string",
                "enum": ["BULL", "BEAR", "NEUTRAL"],
                "description": "Which side has the stronger argument after review.",
            },
        },
        "required": ["confidence_multiplier", "reasoning", "lean_toward"],
    },
}


def resolve_dissent(
    aggregated_signal,
    contributing_signals: list,
    api_key: str,
    provider: LLMProvider,
    model: str,
) -> float | None:
    """If polarization > 0.6, collect the two most opposing team signals,
    format their reasoning, and have an LLM produce a revised confidence adjustment.

    Returns an optional confidence multiplier (0.7 to 1.3), or None if dissent
    resolution is not needed (polarization <= 0.6).
    """
    from hivemind.data.models import SignalAction

    polarization = aggregated_signal.weighted_scores.get("_polarization", 0.0)
    if polarization <= 0.6:
        return None

    # Separate signals into bullish and bearish camps
    BULLISH_ACTIONS = {SignalAction.BUY, SignalAction.COVER}
    BEARISH_ACTIONS = {SignalAction.SELL, SignalAction.SHORT}

    bulls = []
    bears = []
    for sig in contributing_signals:
        conv = sig.metadata.get("conviction", int(sig.confidence * 10))
        reasoning = sig.metadata.get("reasoning", "No reasoning provided.")
        team = sig.team.value if hasattr(sig.team, "value") else str(sig.team)
        entry = {"team": team, "conviction": conv, "reasoning": reasoning}
        if sig.action in BULLISH_ACTIONS:
            bulls.append(entry)
        elif sig.action in BEARISH_ACTIONS:
            bears.append(entry)

    if not bulls or not bears:
        return None

    # Pick the strongest signal from each side
    strongest_bull = max(bulls, key=lambda x: x["conviction"])
    strongest_bear = max(bears, key=lambda x: x["conviction"])

    # Build prompt
    symbol = aggregated_signal.symbol
    agg_action = aggregated_signal.recommended_action.value
    agg_conf = aggregated_signal.aggregated_confidence

    system_prompt = (
        "You are a senior risk analyst resolving a polarized signal disagreement. "
        "Two teams have opposing views. Evaluate their reasoning and decide whether "
        "the aggregated confidence should be adjusted. Be concise."
    )

    user_prompt = (
        f"Symbol: {symbol}\n"
        f"Aggregated direction: {agg_action} (confidence: {agg_conf:.2f})\n"
        f"Polarization score: {polarization:.2f}\n\n"
        f"BULL CASE (Team: {strongest_bull['team']}, Conviction: {strongest_bull['conviction']}/10):\n"
        f"{strongest_bull['reasoning']}\n\n"
        f"BEAR CASE (Team: {strongest_bear['team']}, Conviction: {strongest_bear['conviction']}/10):\n"
        f"{strongest_bear['reasoning']}\n\n"
        f"Based on the quality of arguments, should we adjust confidence? "
        f"Return a multiplier between 0.7 (reduce) and 1.3 (increase)."
    )

    try:
        from hivemind.agents.base import BaseLLMCaller
        caller = BaseLLMCaller(api_key=api_key, provider=provider, model=model)
        result = caller._call_llm_with_tool(system_prompt, user_prompt, _DISSENT_TOOL, max_tokens=512)

        multiplier = float(result.get("confidence_multiplier", 1.0))
        # Clamp to safe range
        multiplier = max(0.7, min(1.3, multiplier))

        lean = result.get("lean_toward", "NEUTRAL")
        reasoning = result.get("reasoning", "")

        logger.info(
            "dissent_resolved",
            symbol=symbol,
            polarization=round(polarization, 2),
            multiplier=round(multiplier, 2),
            lean_toward=lean,
            reasoning=reasoning[:100],
        )

        return multiplier

    except Exception as e:
        logger.warning("dissent_resolution_failed", symbol=symbol, error=str(e))
        return None
