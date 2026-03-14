"""
Performance Tracker — tracks signal outcomes across runs.

Records every signal with its price at emission. On subsequent runs,
evaluates pending signals against current prices to determine accuracy.

Persists to a JSON file between runs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import structlog

from hivemind.data.models import Signal, SignalRecord, SignalAction

logger = structlog.get_logger()

# Minimum price movement to count as correct/incorrect
MIN_MOVE_PCT = 0.5
# Hours to wait before evaluating a signal
EVALUATION_LOOKBACK_HOURS = 24


class PerformanceTracker:
    """
    Tracks signal accuracy over time using JSON file persistence.
    """

    def __init__(self, storage_path: str = "data/performance_history.json") -> None:
        self._path = Path(storage_path)
        self._records: list[SignalRecord] = []
        self._load()

    def record_signals(self, signals: list[Signal], prices: dict[str, float]) -> None:
        """Record new signals from a completed cycle."""
        for sig in signals:
            if sig.action == SignalAction.HOLD:
                continue  # Don't track HOLD signals
            price = prices.get(sig.symbol, 0)
            if price <= 0:
                continue

            record = SignalRecord(
                signal_id=sig.id,
                agent_id=sig.agent_id,
                symbol=sig.symbol,
                team=sig.team,
                action=sig.action,
                confidence=sig.confidence,
                price_at_signal=price,
                timestamp=sig.timestamp,
            )
            self._records.append(record)

        self._save()

    def evaluate_pending(self, current_prices: dict[str, float]) -> dict[str, int]:
        """
        Evaluate pending signals against current prices.
        Returns counts: {"evaluated": N, "correct": N, "incorrect": N}
        """
        now = datetime.now(timezone.utc)
        evaluated = 0
        correct = 0
        incorrect = 0

        for record in self._records:
            if record.outcome != "PENDING":
                continue

            # Check if enough time has passed
            age_hours = (now - record.timestamp).total_seconds() / 3600
            if age_hours < EVALUATION_LOOKBACK_HOURS:
                continue

            current_price = current_prices.get(record.symbol)
            if current_price is None or current_price <= 0:
                continue

            # Calculate price movement
            move_pct = ((current_price - record.price_at_signal) / record.price_at_signal) * 100
            record.price_at_evaluation = current_price
            record.pnl_pct = move_pct

            # Evaluate correctness
            if record.action in (SignalAction.BUY, SignalAction.COVER):
                # Correct if price went up by at least MIN_MOVE_PCT
                if move_pct >= MIN_MOVE_PCT:
                    record.outcome = "CORRECT"
                    correct += 1
                elif move_pct <= -MIN_MOVE_PCT:
                    record.outcome = "INCORRECT"
                    incorrect += 1
                # If price barely moved, leave as pending for next eval
            elif record.action in (SignalAction.SELL, SignalAction.SHORT):
                # Correct if price went down
                if move_pct <= -MIN_MOVE_PCT:
                    record.outcome = "CORRECT"
                    correct += 1
                elif move_pct >= MIN_MOVE_PCT:
                    record.outcome = "INCORRECT"
                    incorrect += 1

            evaluated += 1

        if evaluated > 0:
            self._save()

        return {"evaluated": evaluated, "correct": correct, "incorrect": incorrect}

    def get_team_stats(self) -> dict[str, dict]:
        """Get accuracy stats grouped by team."""
        from collections import defaultdict
        stats: dict[str, dict] = defaultdict(lambda: {"total": 0, "correct": 0, "incorrect": 0, "pending": 0})

        for r in self._records:
            team = r.team.value
            stats[team]["total"] += 1
            if r.outcome == "CORRECT":
                stats[team]["correct"] += 1
            elif r.outcome == "INCORRECT":
                stats[team]["incorrect"] += 1
            else:
                stats[team]["pending"] += 1

        # Add accuracy
        for team_stats in stats.values():
            decided = team_stats["correct"] + team_stats["incorrect"]
            team_stats["accuracy"] = (
                team_stats["correct"] / decided if decided > 0 else 0
            )

        return dict(stats)

    def get_agent_stats(self) -> dict[str, dict]:
        """Get accuracy stats grouped by agent_id."""
        from collections import defaultdict
        stats: dict[str, dict] = defaultdict(
            lambda: {"total": 0, "correct": 0, "incorrect": 0}
        )
        for r in self._records:
            aid = r.agent_id
            stats[aid]["total"] += 1
            if r.outcome == "CORRECT":
                stats[aid]["correct"] += 1
            elif r.outcome == "INCORRECT":
                stats[aid]["incorrect"] += 1
        for s in stats.values():
            decided = s["correct"] + s["incorrect"]
            s["accuracy"] = s["correct"] / decided if decided > 0 else 0
        return dict(stats)

    def get_summary(self) -> dict:
        """Get overall summary stats."""
        total = len(self._records)
        correct = sum(1 for r in self._records if r.outcome == "CORRECT")
        incorrect = sum(1 for r in self._records if r.outcome == "INCORRECT")
        pending = sum(1 for r in self._records if r.outcome == "PENDING")
        decided = correct + incorrect

        return {
            "total_signals": total,
            "correct": correct,
            "incorrect": incorrect,
            "pending": pending,
            "accuracy": correct / decided if decided > 0 else 0,
        }

    def _load(self) -> None:
        """Load records from JSON file."""
        if not self._path.exists():
            self._records = []
            return

        try:
            data = json.loads(self._path.read_text())
            self._records = [SignalRecord.model_validate(r) for r in data]
        except Exception as e:
            logger.error("performance_tracker_load_failed", error=str(e))
            self._records = []

    def _save(self) -> None:
        """Save records to JSON file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [r.model_dump(mode="json") for r in self._records]
        self._path.write_text(json.dumps(data, indent=2, default=str))
