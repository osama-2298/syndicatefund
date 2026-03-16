"""
CEO Memory — Persistent cycle-to-cycle learning.

The CEO accumulates institutional knowledge across cycles:
- What directives were issued and what happened
- Which teams performed well/poorly under which conditions
- What strategy adjustments were made and whether they helped
- Pattern recognition: "last time F&G was 15 and I called BULL, what happened?"

This is the CEO's experience — it grows over time and makes the CEO
smarter with each cycle.

Storage: JSON file that persists between runs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

MAX_MEMORY_CYCLES = 50  # Keep last 50 cycles of memory


class CEOMemory:
    """
    Persistent memory for the CEO agent.
    Stores cycle history and extracts lessons for future decisions.
    """

    def __init__(self, storage_path: str = "data/ceo_memory.json") -> None:
        self._path = Path(storage_path)
        self._cycles: list[dict] = []
        self._load()

    def record_cycle(
        self,
        directive: dict,
        results: dict,
        feedback: dict,
    ) -> None:
        """
        Record a complete cycle: what was directed, what happened, what was learned.
        """
        cycle = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            # What the CEO directed
            "regime": directive.get("regime", ""),
            "risk_multiplier": directive.get("risk_multiplier", 1.0),
            "sector_weights": directive.get("sector_weights", {}),
            "focus_strategy": directive.get("focus_strategy", ""),
            # What happened
            "coins_analyzed": results.get("coins_analyzed", 0),
            "signals_generated": results.get("signals_generated", 0),
            "orders_executed": results.get("orders_executed", 0),
            "portfolio_return": results.get("portfolio_return", 0),
            "drawdown": results.get("drawdown", 0),
            # Key market conditions
            "fear_greed": results.get("fear_greed", 0),
            "btc_price": results.get("btc_price", 0),
            "btc_change_24h": results.get("btc_change_24h", 0),
            "btc_dominance": results.get("btc_dominance", 0),
            # CEO's post-cycle feedback
            "strategy_adjustment": feedback.get("strategy_adjustment", ""),
            "override_action": feedback.get("override_action", "NONE"),
            "regime_still_valid": feedback.get("regime_still_valid", True),
            "assessment": feedback.get("assessment", ""),
            "team_actions": feedback.get("team_actions", []),
        }

        self._cycles.append(cycle)

        # Trim to max size
        if len(self._cycles) > MAX_MEMORY_CYCLES:
            self._cycles = self._cycles[-MAX_MEMORY_CYCLES:]

        self._save()

    def get_last_feedback(self) -> dict | None:
        """Get the CEO's feedback from the most recent cycle."""
        if not self._cycles:
            return None
        last = self._cycles[-1]
        return {
            "strategy_adjustment": last.get("strategy_adjustment", ""),
            "assessment": last.get("assessment", ""),
            "override_action": last.get("override_action", "NONE"),
            "regime_called": last.get("regime", ""),
            "regime_was_valid": last.get("regime_still_valid", True),
            "portfolio_return": last.get("portfolio_return", 0),
        }

    def get_experience_summary(self) -> str:
        """
        Generate a summary of the CEO's accumulated experience.
        This goes into the CEO's prompt so it can reference past patterns.
        """
        if not self._cycles:
            return "No prior cycle history. This is the first cycle."

        n = len(self._cycles)
        recent = self._cycles[-5:]  # Last 5 cycles

        # Aggregate stats
        total_orders = sum(c.get("orders_executed", 0) for c in self._cycles)
        returns = [c.get("portfolio_return", 0) for c in self._cycles]
        avg_return = sum(returns) / len(returns) if returns else 0
        regimes_called = [c.get("regime", "") for c in self._cycles]
        regime_validity = [c.get("regime_still_valid", True) for c in self._cycles]
        regime_accuracy = sum(1 for v in regime_validity if v) / max(len(regime_validity), 1)

        # Build summary
        lines = [
            f"CEO EXPERIENCE: {n} cycles completed.",
            f"Regime accuracy: {regime_accuracy:.0%} ({sum(1 for v in regime_validity if v)}/{len(regime_validity)} correct).",
            f"Total orders executed: {total_orders}.",
            f"Average portfolio return: {avg_return:+.2f}%.",
        ]

        # Recent cycle summaries
        lines.append("\nLast 5 cycles:")
        for c in recent:
            ts = c.get("timestamp", "?")[:10]
            regime = c.get("regime", "?").upper()
            fg = c.get("fear_greed", 0)
            btc = c.get("btc_price", 0)
            orders = c.get("orders_executed", 0)
            ret = c.get("portfolio_return", 0)
            valid = "✓" if c.get("regime_still_valid", True) else "✗"
            lines.append(
                f"  {ts}: {regime} {valid} | F&G={fg} | BTC=${btc:,.0f} | "
                f"{orders} orders | return {ret:+.2f}%"
            )

        # Strategy evolution
        adjustments = [
            c.get("strategy_adjustment", "")
            for c in recent
            if c.get("strategy_adjustment", "")
        ]
        if adjustments:
            lines.append("\nRecent strategy adjustments:")
            for adj in adjustments[-3:]:
                if len(adj) > 80:
                    adj = adj[:79] + "…"
                lines.append(f"  - {adj}")

        # Lessons from wrong regime calls
        wrong_calls = [
            c for c in self._cycles
            if not c.get("regime_still_valid", True)
        ]
        if wrong_calls:
            lines.append(f"\nWrong regime calls: {len(wrong_calls)} times.")
            for wc in wrong_calls[-2:]:
                lines.append(
                    f"  Called {wc.get('regime', '?').upper()} when F&G={wc.get('fear_greed', 0)}, "
                    f"BTC ${wc.get('btc_price', 0):,.0f}"
                )

        return "\n".join(lines)

    @property
    def cycle_count(self) -> int:
        return len(self._cycles)

    def _load(self) -> None:
        if not self._path.exists():
            self._cycles = []
            return
        try:
            data = json.loads(self._path.read_text())
            self._cycles = data if isinstance(data, list) else []
        except Exception as e:
            logger.error("ceo_memory_load_failed", error=str(e))
            self._cycles = []

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._cycles, indent=2, default=str))
