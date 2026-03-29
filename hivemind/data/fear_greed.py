"""
Crypto Fear & Greed Index — from alternative.me.

Free, no auth. Updates once per day.
Value 0-100: 0 = Extreme Fear, 100 = Extreme Greed.
"""

from __future__ import annotations

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

API_URL = "https://api.alternative.me/fng/"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
def get_fear_greed(days: int = 7) -> dict:
    """
    Fetch Fear & Greed Index data.

    Returns:
        {
            "current_value": int (0-100),
            "current_label": str ("Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"),
            "history": [{"value": int, "label": str, "date": str}, ...],  # last N days
            "trend": str,  # "RISING", "FALLING", "STABLE"
        }
    """
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(API_URL, params={"limit": days})
        resp.raise_for_status()
        data = resp.json()

    entries = data.get("data", [])
    if not entries:
        return {
            "current_value": 50,
            "current_label": "Neutral",
            "history": [],
            "trend": "STABLE",
        }

    history = []
    for entry in entries:
        history.append({
            "value": int(entry["value"]),
            "label": entry["value_classification"],
            "timestamp": entry["timestamp"],
        })

    current = history[0]

    # Calculate staleness
    from datetime import datetime, timezone
    current_ts = int(current.get("timestamp", 0))
    if current_ts > 0:
        update_time = datetime.fromtimestamp(current_ts, tz=timezone.utc)
        hours_since = (datetime.now(timezone.utc) - update_time).total_seconds() / 3600
    else:
        hours_since = None

    # Calculate trend from history
    if len(history) >= 3:
        recent_avg = sum(h["value"] for h in history[:3]) / 3
        older_avg = sum(h["value"] for h in history[3:]) / max(len(history[3:]), 1) if len(history) > 3 else recent_avg
        diff = recent_avg - older_avg
        if diff > 5:
            trend = "RISING"
        elif diff < -5:
            trend = "FALLING"
        else:
            trend = "STABLE"
    else:
        trend = "STABLE"

    return {
        "current_value": current["value"],
        "current_label": current["label"],
        "history": history,
        "trend": trend,
        "hours_since_update": round(hours_since, 1) if hours_since is not None else None,
        "is_stale": hours_since > 24 if hours_since is not None else True,
    }
