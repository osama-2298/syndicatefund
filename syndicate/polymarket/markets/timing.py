"""Model run timing — align scans to GFS/ECMWF release windows.

GFS runs at 00/06/12/18 UTC, available ~3.5h later.
ECMWF runs at 00/12 UTC, available ~7h later.

The highest-edge trades happen in the 5-30 minute window after
fresh model data becomes available, before the market reprices.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import structlog

log = structlog.get_logger(__name__)

# GFS availability: init_hour + 3.5 hours
GFS_INIT_HOURS = [0, 6, 12, 18]  # UTC
GFS_DELAY_HOURS = 3.5

# ECMWF availability: init_hour + 7 hours
ECMWF_INIT_HOURS = [0, 12]  # UTC
ECMWF_DELAY_HOURS = 7.0


def _all_release_times(reference_date: datetime) -> list[dict]:
    """Build a list of all model release times around a reference date.

    Generates releases for the day before, the current day, and the next day
    to handle edge cases around midnight.

    Returns:
        Sorted list of dicts with model, init_utc, available_at.
    """
    releases: list[dict] = []

    for day_offset in (-1, 0, 1):
        base = reference_date.replace(
            hour=0, minute=0, second=0, microsecond=0,
        ) + timedelta(days=day_offset)

        for init_hour in GFS_INIT_HOURS:
            available = base + timedelta(hours=init_hour + GFS_DELAY_HOURS)
            releases.append({
                "model": "gfs",
                "init_utc": f"{init_hour:02d}:00",
                "available_at": available,
            })

        for init_hour in ECMWF_INIT_HOURS:
            available = base + timedelta(hours=init_hour + ECMWF_DELAY_HOURS)
            releases.append({
                "model": "ecmwf",
                "init_utc": f"{init_hour:02d}:00",
                "available_at": available,
            })

    releases.sort(key=lambda r: r["available_at"])
    return releases


def next_model_release(now: datetime | None = None) -> dict:
    """Return info about the next model data release.

    Returns:
        {"model": "gfs"|"ecmwf", "init_utc": "HH:MM", "available_at": datetime,
         "minutes_until": float, "is_fresh": bool}
    """
    if now is None:
        now = datetime.now(timezone.utc)

    releases = _all_release_times(now)

    # Find the next release that hasn't happened yet
    for release in releases:
        if release["available_at"] > now:
            minutes_until = (release["available_at"] - now).total_seconds() / 60.0
            return {
                "model": release["model"],
                "init_utc": release["init_utc"],
                "available_at": release["available_at"],
                "minutes_until": minutes_until,
                "is_fresh": False,
            }

    # Shouldn't happen with 3 days of releases, but guard
    return {
        "model": "unknown",
        "init_utc": "00:00",
        "available_at": now + timedelta(hours=1),
        "minutes_until": 60.0,
        "is_fresh": False,
    }


def _most_recent_release(now: datetime) -> dict | None:
    """Find the most recent model release that has already happened."""
    releases = _all_release_times(now)

    # Find the most recent release that has already happened
    past_releases = [r for r in releases if r["available_at"] <= now]
    if not past_releases:
        return None
    return past_releases[-1]  # Already sorted, last one is most recent


def is_fresh_data_window(now: datetime | None = None, window_minutes: int = 30) -> bool:
    """Check if we're within the fresh-data window after a model release."""
    if now is None:
        now = datetime.now(timezone.utc)

    recent = _most_recent_release(now)
    if recent is None:
        return False

    elapsed = (now - recent["available_at"]).total_seconds() / 60.0
    return 0 <= elapsed <= window_minutes


def optimal_scan_interval(now: datetime | None = None) -> int:
    """Return optimal scan interval in seconds.

    - Within 30 min of model release: scan every 60 seconds (aggressive)
    - Within 2 hours of model release: scan every 120 seconds
    - Otherwise: scan every 300 seconds (default)
    """
    if now is None:
        now = datetime.now(timezone.utc)

    recent = _most_recent_release(now)
    if recent is None:
        return 300

    elapsed_minutes = (now - recent["available_at"]).total_seconds() / 60.0

    if 0 <= elapsed_minutes <= 30:
        return 60
    elif 0 <= elapsed_minutes <= 120:
        return 120
    else:
        return 300


def time_until_next_release(now: datetime | None = None) -> float:
    """Seconds until the next model data becomes available."""
    if now is None:
        now = datetime.now(timezone.utc)

    info = next_model_release(now)
    delta = (info["available_at"] - now).total_seconds()
    return max(0.0, delta)
