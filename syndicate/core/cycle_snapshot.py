"""Cycle snapshot — captures EVERY piece of data generated during a pipeline cycle.

Saves a complete JSON file per cycle at data/cycles/cycle_{timestamp}.json.
Nothing is lost. Every signal, every decision, every stat.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class CycleSnapshot:
    """Accumulates all data generated during a single pipeline cycle."""

    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # ── Intelligence ──
    intel: dict[str, Any] = field(default_factory=dict)
    btc_stats: dict[str, Any] = field(default_factory=dict)

    # ── CEO Directive ──
    ceo_directive: dict[str, Any] = field(default_factory=dict)
    ceo_elapsed_ms: int = 0

    # ── COO Selection ──
    coo_selection: dict[str, Any] = field(default_factory=dict)
    coo_elapsed_ms: int = 0
    hot_coins: list[dict] = field(default_factory=list)

    # ── CRO Risk Rules ──
    cro_rules: dict[str, Any] = field(default_factory=dict)
    cro_reasoning: str = ""
    cro_elapsed_ms: int = 0

    # ── Individual Agent Signals (the big one — every agent's raw output) ──
    agent_signals: list[dict[str, Any]] = field(default_factory=list)

    # ── Team Manager Signals ──
    team_signals: list[dict[str, Any]] = field(default_factory=list)

    # ── Aggregated Signals ──
    aggregated_signals: list[dict[str, Any]] = field(default_factory=list)

    # ── Disagreements ──
    disagreements: list[dict[str, Any]] = field(default_factory=list)

    # ── Signal Funnel ──
    signal_funnel: dict[str, int] = field(default_factory=dict)

    # ── Risk Manager Output ──
    risk_orders: list[dict[str, Any]] = field(default_factory=list)

    # ── Portfolio Manager Output ──
    pm_review: dict[str, Any] = field(default_factory=dict)

    # ── Verdicts ──
    verdicts: list[dict[str, Any]] = field(default_factory=list)

    # ── Executed Trades ──
    trades_executed: list[dict[str, Any]] = field(default_factory=list)

    # ── Trade Exits (from monitor) ──
    trade_exits: list[dict[str, Any]] = field(default_factory=list)

    # ── CEO Review ──
    ceo_review: dict[str, Any] = field(default_factory=dict)
    ceo_review_elapsed_ms: int = 0

    # ── Performance Stats ──
    team_stats: dict[str, Any] = field(default_factory=dict)
    agent_stats: dict[str, Any] = field(default_factory=dict)
    calibration: dict[str, Any] = field(default_factory=dict)

    # ── Team Weights ──
    team_weights: dict[str, float] = field(default_factory=dict)
    phase_info: dict[str, Any] = field(default_factory=dict)

    # ── Portfolio State ──
    portfolio_summary: dict[str, Any] = field(default_factory=dict)

    # ── Cycle Metadata ──
    coins_analyzed: int = 0
    signals_produced: int = 0
    orders_executed: int = 0
    duration_secs: float = 0
    llm_calls: int = 0

    def add_agent_signal(
        self,
        agent_class: str,
        team: str,
        symbol: str,
        action: str,
        confidence: float,
        conviction: int,
        reasoning: str,
        elapsed_ms: int,
        metadata: dict | None = None,
    ):
        self.agent_signals.append({
            "agent_class": agent_class,
            "team": team,
            "symbol": symbol,
            "action": action,
            "confidence": round(confidence, 4),
            "conviction": conviction,
            "reasoning": (reasoning or "")[:500],
            "elapsed_ms": elapsed_ms,
            "metadata": metadata or {},
        })

    def add_team_signal(
        self,
        team: str,
        symbol: str,
        action: str,
        confidence: float,
        agreement: float,
        reasoning: str,
        elapsed_ms: int,
    ):
        self.team_signals.append({
            "team": team,
            "symbol": symbol,
            "action": action,
            "confidence": round(confidence, 4),
            "agreement": round(agreement, 4),
            "reasoning": (reasoning or "")[:500],
            "elapsed_ms": elapsed_ms,
        })

    def add_aggregated_signal(
        self,
        symbol: str,
        action: str,
        confidence: float,
        consensus: float,
        weighted_scores: dict,
    ):
        # Filter internal keys but keep team scores
        scores = {k: v for k, v in weighted_scores.items() if not k.startswith("_")}
        quality = weighted_scores.get("_decision_quality", "")
        alerts = weighted_scores.get("_alerts", [])
        self.aggregated_signals.append({
            "symbol": symbol,
            "action": action,
            "confidence": round(confidence, 4),
            "consensus": round(consensus, 4),
            "team_scores": scores,
            "decision_quality": quality,
            "alerts": alerts[:5],
        })

    def add_verdict(self, symbol: str, action: str, confidence: float, consensus: float, blocked: bool, reason: str):
        self.verdicts.append({
            "symbol": symbol,
            "action": action,
            "confidence": round(confidence, 4),
            "consensus": round(consensus, 4),
            "blocked": blocked,
            "reason": reason,
        })

    def add_trade(self, symbol: str, side: str, price: float, quantity: float, stop_loss: float, take_profit: float):
        self.trades_executed.append({
            "symbol": symbol,
            "side": side,
            "price": price,
            "quantity": quantity,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
        })

    def add_trade_exit(self, symbol: str, exit_reason: str, exit_price: float, pnl_pct: float, pnl_usd: float, holding_hours: float):
        self.trade_exits.append({
            "symbol": symbol,
            "exit_reason": exit_reason,
            "exit_price": exit_price,
            "pnl_pct": round(pnl_pct, 4),
            "pnl_usd": round(pnl_usd, 2),
            "holding_hours": round(holding_hours, 1),
        })

    def save(self) -> str:
        """Save the full snapshot to data/cycles/cycle_{timestamp}.json. Returns the file path."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = Path("data/cycles") / f"cycle_{ts}.json"
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "timestamp": self.timestamp,
            "duration_secs": round(self.duration_secs, 1),
            "coins_analyzed": self.coins_analyzed,
            "signals_produced": self.signals_produced,
            "orders_executed": self.orders_executed,
            "llm_calls": self.llm_calls,
            "intel": _safe_serialize(self.intel),
            "btc_stats": _safe_serialize(self.btc_stats),
            "ceo_directive": self.ceo_directive,
            "ceo_elapsed_ms": self.ceo_elapsed_ms,
            "coo_selection": self.coo_selection,
            "coo_elapsed_ms": self.coo_elapsed_ms,
            "hot_coins": self.hot_coins,
            "cro_rules": self.cro_rules,
            "cro_reasoning": self.cro_reasoning,
            "cro_elapsed_ms": self.cro_elapsed_ms,
            "agent_signals": self.agent_signals,
            "team_signals": self.team_signals,
            "aggregated_signals": self.aggregated_signals,
            "disagreements": self.disagreements,
            "signal_funnel": self.signal_funnel,
            "risk_orders_count": len(self.risk_orders),
            "pm_review": self.pm_review,
            "verdicts": self.verdicts,
            "trades_executed": self.trades_executed,
            "trade_exits": self.trade_exits,
            "ceo_review": self.ceo_review,
            "ceo_review_elapsed_ms": self.ceo_review_elapsed_ms,
            "team_stats": self.team_stats,
            "agent_stats": self.agent_stats,
            "calibration": self.calibration,
            "team_weights": self.team_weights,
            "phase_info": self.phase_info,
            "portfolio_summary": self.portfolio_summary,
        }

        path.write_text(json.dumps(data, indent=2, default=str))
        return str(path)


def _safe_serialize(obj: Any) -> Any:
    """Make objects JSON-safe by converting non-serializable types."""
    if isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_serialize(v) for v in obj]
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    return str(obj)
