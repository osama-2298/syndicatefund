"""
Statistical analysis engine for agent performance.

Pure computation — no LLM calls. Feeds the Quantitative Researcher agent.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np

from syndicate.config import settings


def _load_records() -> list[dict]:
    """Load signal records from performance history JSON."""
    path_str = settings.performance_history_path
    if not path_str:
        # Fallback to data dir
        path = settings.data_dir / "performance_history.json"
    else:
        path = Path(path_str)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []


def rolling_accuracy(agent_id: str, window_days: int = 30) -> list[dict]:
    """Compute accuracy over a rolling window for an agent.

    Returns list of {date, accuracy, total, correct} dicts, one per day.
    """
    records = _load_records()
    agent_records = [
        r
        for r in records
        if r.get("agent_id") == agent_id
        and r.get("outcome") in ("CORRECT", "INCORRECT")
    ]

    if not agent_records:
        return []

    # Sort by timestamp
    for r in agent_records:
        r["_ts"] = (
            datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
            if isinstance(r["timestamp"], str)
            else r["timestamp"]
        )
    agent_records.sort(key=lambda r: r["_ts"])

    # Compute rolling accuracy per day
    results = []
    earliest = agent_records[0]["_ts"]
    latest = agent_records[-1]["_ts"]
    current = earliest.replace(hour=0, minute=0, second=0, microsecond=0)

    while current <= latest:
        window_start = current - timedelta(days=window_days)
        window_records = [
            r for r in agent_records if window_start <= r["_ts"] <= current
        ]

        if window_records:
            correct = sum(1 for r in window_records if r["outcome"] == "CORRECT")
            total = len(window_records)
            results.append(
                {
                    "date": current.isoformat(),
                    "accuracy": correct / total if total > 0 else 0,
                    "total": total,
                    "correct": correct,
                }
            )

        current += timedelta(days=1)

    return results


def accuracy_by_regime(agent_id: str) -> dict[str, dict]:
    """Accuracy broken down by market regime.

    Returns: {"bull": {"total": N, "correct": N, "accuracy": float}, ...}

    Note: requires ceo_memory.json to map timestamps to regimes.
    """
    records = _load_records()
    agent_records = [
        r
        for r in records
        if r.get("agent_id") == agent_id
        and r.get("outcome") in ("CORRECT", "INCORRECT")
    ]

    # Load CEO memory for regime data
    ceo_path = Path(settings.ceo_memory_path)
    regime_map = {}  # timestamp_range -> regime
    if ceo_path.exists():
        try:
            ceo_data = json.loads(ceo_path.read_text())
            cycles = ceo_data.get("cycles", [])
            for cycle in cycles:
                directive = cycle.get("directive", {})
                regime = directive.get("regime", "unknown")
                ts = cycle.get("timestamp", "")
                if ts:
                    regime_map[ts] = regime
        except Exception:
            pass

    # Simple fallback: group by most recent known regime
    result: dict[str, dict] = defaultdict(lambda: {"total": 0, "correct": 0})

    for r in agent_records:
        # Find closest regime (simplified)
        regime = "unknown"
        for ts, reg in sorted(regime_map.items(), reverse=True):
            if r.get("timestamp", "") >= ts:
                regime = reg
                break

        result[regime]["total"] += 1
        if r["outcome"] == "CORRECT":
            result[regime]["correct"] += 1

    for stats in result.values():
        stats["accuracy"] = (
            stats["correct"] / stats["total"] if stats["total"] > 0 else 0
        )

    return dict(result)


def accuracy_by_conviction(agent_id: str) -> dict[int, dict]:
    """Accuracy at each conviction level (0-10).

    Returns: {4: {"total": N, "correct": N, "accuracy": float}, ...}
    """
    records = _load_records()
    agent_records = [
        r
        for r in records
        if r.get("agent_id") == agent_id
        and r.get("outcome") in ("CORRECT", "INCORRECT")
    ]

    result: dict[int, dict] = defaultdict(lambda: {"total": 0, "correct": 0})

    for r in agent_records:
        conv = int(
            r.get("confidence", 0) * 10
        )  # confidence is 0-1, conviction is 0-10
        result[conv]["total"] += 1
        if r["outcome"] == "CORRECT":
            result[conv]["correct"] += 1

    for stats in result.values():
        stats["accuracy"] = (
            stats["correct"] / stats["total"] if stats["total"] > 0 else 0
        )

    return dict(sorted(result.items()))


def information_coefficient(agent_id: str) -> float:
    """Correlation between conviction and actual returns.

    IC > 0 means higher conviction correlates with better outcomes.
    IC ~ 0 means conviction is not calibrated.
    IC < 0 means conviction is inversely calibrated (bad).
    """
    records = _load_records()
    agent_records = [
        r
        for r in records
        if r.get("agent_id") == agent_id and r.get("pnl_pct") is not None
    ]

    if len(agent_records) < 10:
        return 0.0

    confidences = np.array([r["confidence"] for r in agent_records])
    pnls = np.array([r["pnl_pct"] for r in agent_records])

    # Adjust for direction (SHORT signals should have negative pnl for correct)
    for i, r in enumerate(agent_records):
        if r.get("action") in ("SHORT", "SELL"):
            pnls[i] = -pnls[i]  # Flip so positive = correct direction

    if np.std(confidences) == 0 or np.std(pnls) == 0:
        return 0.0

    return float(np.corrcoef(confidences, pnls)[0, 1])


def agent_correlation_matrix(agent_ids: list[str] | None = None) -> dict:
    """Pairwise signal correlation between agents.

    For each pair of agents, compute how often they agree on direction.

    Returns: {"agents": [...], "matrix": [[1.0, 0.8, ...], ...],
              "high_correlation_pairs": [...]}
    """
    records = _load_records()

    # Group signals by (symbol, approximate_timestamp)
    signals_by_context: dict[str, dict[str, str]] = defaultdict(
        dict
    )  # context -> {agent_id: direction}

    for r in records:
        if r.get("action") in ("BUY", "SHORT", "SELL", "COVER"):
            # Context key: symbol + date (group signals from same cycle)
            ts = r.get("timestamp", "")[:10]  # Just the date
            context = f"{r['symbol']}_{ts}"
            direction = (
                "BULLISH" if r["action"] in ("BUY", "COVER") else "BEARISH"
            )
            signals_by_context[context][r["agent_id"]] = direction

    # Get unique agent IDs
    all_agents: set[str] = set()
    for agents in signals_by_context.values():
        all_agents.update(agents.keys())

    if agent_ids:
        all_agents = all_agents.intersection(agent_ids)

    agents_list = sorted(all_agents)
    n = len(agents_list)

    if n < 2:
        return {
            "agents": agents_list,
            "matrix": [],
            "high_correlation_pairs": [],
        }

    # Compute agreement matrix
    matrix = np.zeros((n, n))
    counts = np.zeros((n, n))

    for context, agent_dirs in signals_by_context.items():
        for i, a1 in enumerate(agents_list):
            for j, a2 in enumerate(agents_list):
                if a1 in agent_dirs and a2 in agent_dirs:
                    counts[i][j] += 1
                    if agent_dirs[a1] == agent_dirs[a2]:
                        matrix[i][j] += 1

    # Normalize
    with np.errstate(divide="ignore", invalid="ignore"):
        agreement = np.where(counts > 0, matrix / counts, 0)

    # Find high correlation pairs (>80% agreement, at least 10 co-occurrences)
    high_pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            if counts[i][j] >= 10 and agreement[i][j] > 0.8:
                high_pairs.append(
                    {
                        "agent_1": agents_list[i],
                        "agent_2": agents_list[j],
                        "agreement": float(agreement[i][j]),
                        "co_occurrences": int(counts[i][j]),
                    }
                )

    return {
        "agents": agents_list,
        "matrix": agreement.tolist(),
        "high_correlation_pairs": sorted(
            high_pairs, key=lambda x: -x["agreement"]
        ),
    }


def signal_decay_test(agent_id: str, lookback_days: int = 90) -> dict:
    """Detect if an agent's accuracy is declining over time.

    Uses a simple comparison of recent vs older accuracy within the
    lookback period.

    Returns: {
        "agent_id": str,
        "decay_detected": bool,
        "recent_accuracy": float (last 30d),
        "older_accuracy": float (30-90d ago),
        "delta": float (recent - older, negative = decay),
        "sample_size_recent": int,
        "sample_size_older": int,
        "severity": "none" | "mild" | "moderate" | "severe",
    }
    """
    records = _load_records()
    agent_records = [
        r
        for r in records
        if r.get("agent_id") == agent_id
        and r.get("outcome") in ("CORRECT", "INCORRECT")
    ]

    now = datetime.now(timezone.utc)

    recent = [
        r for r in agent_records if _parse_ts(r) >= now - timedelta(days=30)
    ]
    older = [
        r
        for r in agent_records
        if now - timedelta(days=lookback_days)
        <= _parse_ts(r)
        < now - timedelta(days=30)
    ]

    recent_acc = sum(1 for r in recent if r["outcome"] == "CORRECT") / max(
        len(recent), 1
    )
    older_acc = sum(1 for r in older if r["outcome"] == "CORRECT") / max(
        len(older), 1
    )
    delta = recent_acc - older_acc

    # Determine severity
    if len(recent) < 5 or len(older) < 5:
        severity = "insufficient_data"
        decay = False
    elif delta < -0.20:
        severity = "severe"
        decay = True
    elif delta < -0.10:
        severity = "moderate"
        decay = True
    elif delta < -0.05:
        severity = "mild"
        decay = True
    else:
        severity = "none"
        decay = False

    return {
        "agent_id": agent_id,
        "decay_detected": decay,
        "recent_accuracy": recent_acc,
        "older_accuracy": older_acc,
        "delta": delta,
        "sample_size_recent": len(recent),
        "sample_size_older": len(older),
        "severity": severity,
    }


def team_contribution() -> dict[str, dict]:
    """How much alpha each team contributes.

    Returns: {"technical": {"total_signals": N, "correct": N,
              "accuracy": float, "avg_pnl_pct": float}, ...}
    """
    records = _load_records()

    result: dict[str, dict] = defaultdict(
        lambda: {
            "total_signals": 0,
            "correct": 0,
            "incorrect": 0,
            "pnl_sum": 0.0,
            "pnl_count": 0,
        }
    )

    for r in records:
        team = r.get("team", "unknown")
        if isinstance(team, dict):
            team = team.get("value", "unknown")

        if r.get("outcome") in ("CORRECT", "INCORRECT"):
            result[team]["total_signals"] += 1
            if r["outcome"] == "CORRECT":
                result[team]["correct"] += 1
            else:
                result[team]["incorrect"] += 1

        if r.get("pnl_pct") is not None:
            result[team]["pnl_sum"] += r["pnl_pct"]
            result[team]["pnl_count"] += 1

    for team, stats in result.items():
        stats["accuracy"] = (
            stats["correct"] / stats["total_signals"]
            if stats["total_signals"] > 0
            else 0
        )
        stats["avg_pnl_pct"] = (
            stats["pnl_sum"] / stats["pnl_count"]
            if stats["pnl_count"] > 0
            else 0
        )
        del stats["pnl_sum"]
        del stats["pnl_count"]

    return dict(result)


def full_report() -> dict[str, Any]:
    """Generate a complete agent statistics report.

    Returns all metrics in one call — useful for feeding to the Quant
    Researcher.
    """
    records = _load_records()

    # Get unique agent IDs
    agent_ids = list(
        set(r["agent_id"] for r in records if r.get("agent_id"))
    )

    # Per-agent stats
    agent_stats = {}
    decay_alerts = []

    for aid in agent_ids:
        agent_records = [
            r
            for r in records
            if r["agent_id"] == aid
            and r["outcome"] in ("CORRECT", "INCORRECT")
        ]
        if not agent_records:
            continue

        correct = sum(1 for r in agent_records if r["outcome"] == "CORRECT")
        total = len(agent_records)

        ic = information_coefficient(aid)
        decay = signal_decay_test(aid)

        agent_stats[aid] = {
            "total_signals": total,
            "correct": correct,
            "accuracy": correct / total if total > 0 else 0,
            "information_coefficient": ic,
            "decay": decay,
        }

        if decay["decay_detected"]:
            decay_alerts.append(
                f"{aid}: accuracy dropped {decay['delta']:.1%} "
                f"({decay['severity']})"
            )

    return {
        "total_signals": len(records),
        "decided_signals": len(
            [r for r in records if r["outcome"] in ("CORRECT", "INCORRECT")]
        ),
        "pending_signals": len(
            [r for r in records if r["outcome"] == "PENDING"]
        ),
        "agent_stats": agent_stats,
        "team_contribution": team_contribution(),
        "correlation": agent_correlation_matrix(agent_ids),
        "decay_alerts": decay_alerts,
    }


def _parse_ts(record: dict) -> datetime:
    """Parse timestamp from a record."""
    ts = record.get("timestamp", "")
    if isinstance(ts, str):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return ts
