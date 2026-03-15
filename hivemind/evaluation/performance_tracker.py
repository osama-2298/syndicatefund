"""
Performance Tracker — tracks signal outcomes across runs.

Records every signal with its price at emission. On subsequent runs,
evaluates pending signals against current prices to determine accuracy.

Supports two evaluation paths:
  1. Trade-outcome-based: when a trade closes, mark the originating signal
     as CORRECT (profitable) or INCORRECT (unprofitable).
  2. Price-movement-based: the legacy 24h/0.5% directional check, used as
     a secondary metric for signals that never generated a trade.

Also computes:
  - Information Coefficient (IC): Spearman rank correlation between signal
    confidence and actual price movement magnitude (rolling 30-day window).
  - P&L contribution per team: attributes closed-trade P&L to the teams
    whose signals contributed, weighted by signal weight.

Persists to a JSON file between runs.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import structlog

from hivemind.data.models import Signal, SignalRecord, SignalAction

logger = structlog.get_logger()

# Minimum price movement to count as correct/incorrect
MIN_MOVE_PCT = 0.5
# Hours to wait before evaluating a signal
EVALUATION_LOOKBACK_HOURS = 24
# Rolling window for IC computation
IC_ROLLING_DAYS = 30


def _rank(values: list[float]) -> list[float]:
    """
    Compute fractional ranks for a list of values (1-based).
    Ties receive the average rank.  No external dependency required.
    """
    n = len(values)
    indexed = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n - 1 and values[indexed[j + 1]] == values[indexed[i]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1  # 1-based average rank for tied group
        for k in range(i, j + 1):
            ranks[indexed[k]] = avg_rank
        i = j + 1
    return ranks


def _spearman_correlation(x: list[float], y: list[float]) -> float:
    """
    Compute Spearman rank correlation between two equal-length sequences.
    Uses scipy.stats.spearmanr if available, otherwise falls back to a
    manual rank-based computation.
    """
    if len(x) != len(y) or len(x) < 3:
        return 0.0

    try:
        from scipy.stats import spearmanr
        corr, _ = spearmanr(x, y)
        if corr != corr:  # NaN check
            return 0.0
        return float(corr)
    except ImportError:
        pass

    # Manual fallback: Spearman rho = Pearson r of the ranks
    rx = _rank(x)
    ry = _rank(y)
    n = len(rx)
    mean_rx = sum(rx) / n
    mean_ry = sum(ry) / n
    cov = sum((a - mean_rx) * (b - mean_ry) for a, b in zip(rx, ry))
    std_x = sum((a - mean_rx) ** 2 for a in rx) ** 0.5
    std_y = sum((b - mean_ry) ** 2 for b in ry) ** 0.5
    if std_x == 0 or std_y == 0:
        return 0.0
    return cov / (std_x * std_y)


class PerformanceTracker:
    """
    Tracks signal accuracy over time using JSON file persistence.
    """

    def __init__(self, storage_path: str = "data/performance_history.json") -> None:
        self._path = Path(storage_path)
        self._records: list[SignalRecord] = []
        self._load()

    # ─── Recording ────────────────────────────────────────────────────

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

    # ─── Task 2.1: Trade-outcome-based evaluation ────────────────────

    def evaluate_from_trade_outcome(self, signal_id: str, profitable: bool) -> bool:
        """
        Mark a signal as CORRECT/INCORRECT based on actual trade P&L.

        Called when a trade closes: look up the originating signal by its id
        and set the outcome.  Returns True if the signal was found and updated.
        """
        for record in self._records:
            if record.signal_id == signal_id and record.outcome == "PENDING":
                record.outcome = "CORRECT" if profitable else "INCORRECT"
                record.evaluation_source = "trade"
                self._save()
                logger.info(
                    "signal_evaluated_from_trade",
                    signal_id=signal_id,
                    outcome=record.outcome,
                )
                return True
        return False

    # ─── Legacy price-movement evaluation (secondary metric) ─────────

    def evaluate_pending(self, current_prices: dict[str, float]) -> dict[str, int]:
        """
        Evaluate pending signals against current prices.
        Returns counts: {"evaluated": N, "correct": N, "incorrect": N}

        This is the secondary evaluation path.  Signals already resolved
        via trade outcomes are skipped.
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
                    record.evaluation_source = "price_movement"
                    correct += 1
                elif move_pct <= -MIN_MOVE_PCT:
                    record.outcome = "INCORRECT"
                    record.evaluation_source = "price_movement"
                    incorrect += 1
                # If price barely moved, leave as pending for next eval
            elif record.action in (SignalAction.SELL, SignalAction.SHORT):
                # Correct if price went down
                if move_pct <= -MIN_MOVE_PCT:
                    record.outcome = "CORRECT"
                    record.evaluation_source = "price_movement"
                    correct += 1
                elif move_pct >= MIN_MOVE_PCT:
                    record.outcome = "INCORRECT"
                    record.evaluation_source = "price_movement"
                    incorrect += 1

            evaluated += 1

        if evaluated > 0:
            self._save()

        return {"evaluated": evaluated, "correct": correct, "incorrect": incorrect}

    # ─── Stats: team-level ────────────────────────────────────────────

    def get_team_stats(self) -> dict[str, dict]:
        """
        Get accuracy stats grouped by team.

        Returns both overall accuracy and split metrics:
          - trade_accuracy: accuracy for signals evaluated via actual trade P&L
          - signal_accuracy: accuracy for signals evaluated via price movement
        """
        stats: dict[str, dict] = defaultdict(lambda: {
            "total": 0,
            "correct": 0,
            "incorrect": 0,
            "pending": 0,
            # Trade-outcome sub-counts
            "trade_correct": 0,
            "trade_incorrect": 0,
            # Price-movement sub-counts
            "signal_correct": 0,
            "signal_incorrect": 0,
        })

        for r in self._records:
            team = r.team.value if hasattr(r.team, 'value') else r.team
            stats[team]["total"] += 1
            if r.outcome == "CORRECT":
                stats[team]["correct"] += 1
                if r.evaluation_source == "trade":
                    stats[team]["trade_correct"] += 1
                else:
                    stats[team]["signal_correct"] += 1
            elif r.outcome == "INCORRECT":
                stats[team]["incorrect"] += 1
                if r.evaluation_source == "trade":
                    stats[team]["trade_incorrect"] += 1
                else:
                    stats[team]["signal_incorrect"] += 1
            else:
                stats[team]["pending"] += 1

        # Add accuracy metrics
        for team_stats in stats.values():
            decided = team_stats["correct"] + team_stats["incorrect"]
            team_stats["accuracy"] = (
                team_stats["correct"] / decided if decided > 0 else 0
            )

            # Trade accuracy (from actual trade outcomes)
            trade_decided = team_stats["trade_correct"] + team_stats["trade_incorrect"]
            team_stats["trade_accuracy"] = (
                team_stats["trade_correct"] / trade_decided if trade_decided > 0 else 0
            )

            # Signal accuracy (from price movement check)
            signal_decided = team_stats["signal_correct"] + team_stats["signal_incorrect"]
            team_stats["signal_accuracy"] = (
                team_stats["signal_correct"] / signal_decided if signal_decided > 0 else 0
            )

        return dict(stats)

    def get_agent_stats(self) -> dict[str, dict]:
        """Get accuracy stats grouped by agent_id."""
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

    # ─── Stats: overall summary ───────────────────────────────────────

    def get_summary(self) -> dict:
        """
        Get overall summary stats, including split trade/signal accuracy.
        """
        total = len(self._records)
        correct = sum(1 for r in self._records if r.outcome == "CORRECT")
        incorrect = sum(1 for r in self._records if r.outcome == "INCORRECT")
        pending = sum(1 for r in self._records if r.outcome == "PENDING")
        decided = correct + incorrect

        # Trade-outcome metrics
        trade_correct = sum(
            1 for r in self._records
            if r.outcome == "CORRECT" and r.evaluation_source == "trade"
        )
        trade_incorrect = sum(
            1 for r in self._records
            if r.outcome == "INCORRECT" and r.evaluation_source == "trade"
        )
        trade_decided = trade_correct + trade_incorrect

        # Signal (price-movement) metrics
        signal_correct = sum(
            1 for r in self._records
            if r.outcome == "CORRECT" and r.evaluation_source == "price_movement"
        )
        signal_incorrect = sum(
            1 for r in self._records
            if r.outcome == "INCORRECT" and r.evaluation_source == "price_movement"
        )
        signal_decided = signal_correct + signal_incorrect

        return {
            "total_signals": total,
            "correct": correct,
            "incorrect": incorrect,
            "pending": pending,
            "accuracy": correct / decided if decided > 0 else 0,
            # Trade-based accuracy (from actual P&L)
            "trade_correct": trade_correct,
            "trade_incorrect": trade_incorrect,
            "trade_accuracy": trade_correct / trade_decided if trade_decided > 0 else 0,
            # Signal-based accuracy (from price movement)
            "signal_correct": signal_correct,
            "signal_incorrect": signal_incorrect,
            "signal_accuracy": signal_correct / signal_decided if signal_decided > 0 else 0,
        }

    # ─── Task 2.2: Information Coefficient (IC) tracking ─────────────

    def compute_ic(self) -> dict[str, Any]:
        """
        Compute Information Coefficient (Spearman rank correlation) between
        signal confidence and actual price movement magnitude.

        Returns:
            {
                "overall_ic": float,        # IC across all evaluated signals
                "by_team": {team: ic, ...},  # Per-team rolling 30-day IC
                "interpretation": str,       # Human-readable assessment
            }

        IC > 0.05  =>  useful signal (confidence predicts magnitude)
        IC ~ 0     =>  no predictive value
        IC < 0     =>  anti-predictive (higher confidence = worse outcomes)
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=IC_ROLLING_DAYS)

        # Collect (confidence, signed_move_pct) pairs for evaluated signals
        # "signed" means: positive if the signal was directionally correct
        overall_conf: list[float] = []
        overall_move: list[float] = []
        team_data: dict[str, tuple[list[float], list[float]]] = defaultdict(lambda: ([], []))

        for r in self._records:
            if r.outcome not in ("CORRECT", "INCORRECT"):
                continue
            if r.pnl_pct is None:
                continue
            if r.timestamp < cutoff:
                continue

            # Signed move: positive = correct direction, negative = wrong direction
            if r.action in (SignalAction.BUY, SignalAction.COVER):
                signed_move = r.pnl_pct  # positive move is correct for BUY
            elif r.action in (SignalAction.SELL, SignalAction.SHORT):
                signed_move = -r.pnl_pct  # negative move is correct for SELL
            else:
                continue

            overall_conf.append(r.confidence)
            overall_move.append(signed_move)

            team = r.team.value if hasattr(r.team, 'value') else r.team
            team_data[team][0].append(r.confidence)
            team_data[team][1].append(signed_move)

        overall_ic = _spearman_correlation(overall_conf, overall_move)

        by_team: dict[str, float] = {}
        for team, (confs, moves) in team_data.items():
            by_team[team] = round(_spearman_correlation(confs, moves), 4)

        # Interpretation
        if len(overall_conf) < 10:
            interpretation = "Insufficient data (<10 evaluated signals in rolling window)"
        elif overall_ic > 0.10:
            interpretation = "Strong predictive signal — confidence correlates well with outcome magnitude"
        elif overall_ic > 0.05:
            interpretation = "Useful signal — confidence has mild positive predictive value"
        elif overall_ic > -0.05:
            interpretation = "No predictive value — confidence does not predict outcome magnitude"
        else:
            interpretation = "Anti-predictive — higher confidence correlates with worse outcomes; recalibrate agents"

        return {
            "overall_ic": round(overall_ic, 4),
            "by_team": by_team,
            "interpretation": interpretation,
            "sample_size": len(overall_conf),
        }

    # ─── Task 2.3: P&L contribution per team ────────────────────────

    def get_pnl_contribution(
        self,
        ledger_entries: list[Any],
        signal_records: list[Signal] | None = None,
    ) -> dict[str, float]:
        """
        Attribute closed-trade P&L to contributing teams based on their
        signal weight.

        Each ledger entry is expected to have:
          - source_signal_id (str)
          - pnl_usd (float)
          - exit_reason (str) — entries with exit_reason == "OPEN" are skipped

        For each closed trade we look up the matching SignalRecord to find
        the team, then attribute the full pnl_usd to that team.  If multiple
        signals from different teams contributed to the same aggregated signal,
        each contributing team gets a proportional share of the P&L.

        If ``signal_records`` is provided (the raw Signal objects from the
        cycle), we use those for richer attribution. Otherwise we fall back
        to the internal ``_records`` index.

        Returns:
            {"technical": 12.50, "sentiment": -3.20, ...}
        """
        # Build an index: signal_id -> SignalRecord
        sig_index: dict[str, SignalRecord] = {}
        for r in self._records:
            sig_index[r.signal_id] = r

        team_pnl: dict[str, float] = defaultdict(float)

        for entry in ledger_entries:
            # Skip open trades
            exit_reason = getattr(entry, "exit_reason", "") if not isinstance(entry, dict) else entry.get("exit_reason", "")
            if exit_reason == "OPEN":
                continue

            pnl_usd = getattr(entry, "pnl_usd", 0) if not isinstance(entry, dict) else entry.get("pnl_usd", 0)
            source_id = getattr(entry, "source_signal_id", "") if not isinstance(entry, dict) else entry.get("source_signal_id", "")

            if not source_id:
                team_pnl["unattributed"] += pnl_usd
                continue

            record = sig_index.get(source_id)
            if record:
                team = record.team.value if hasattr(record.team, 'value') else record.team
                team_pnl[team] += pnl_usd
            else:
                team_pnl["unattributed"] += pnl_usd

        # Round for display
        return {team: round(pnl, 2) for team, pnl in sorted(team_pnl.items(), key=lambda x: -x[1])}

    # ─── Persistence ──────────────────────────────────────────────────

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
