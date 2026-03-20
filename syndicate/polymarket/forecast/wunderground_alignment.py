"""Align forecast daily high with Weather Underground's observation window.

WU uses METAR hourly observations and reports the maximum. Their "day"
is midnight-to-midnight local time. We need to extract the max temperature
from the same window in the ensemble forecast data.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog

log = structlog.get_logger(__name__)


# ── City Timezone Offsets ─────────────────────────────────────────────────────
# UTC offset in hours for each city. These are standard time offsets.
# DST is NOT applied — WU uses the station's local civil time, which shifts
# with DST. For production accuracy, a full tz database (e.g., zoneinfo) is
# preferred, but hardcoded offsets cover the 90%+ case and avoid dependencies.
#
# NOTE: For cities that observe DST, the offset here is standard time.
# A future enhancement can use zoneinfo for DST-aware windows.

CITY_UTC_OFFSETS: dict[str, float] = {
    # North America (standard time)
    "New York": -5.0,       # EST (EDT = -4)
    "Dallas": -6.0,         # CST (CDT = -5)
    "Miami": -5.0,          # EST (EDT = -4)
    "Atlanta": -5.0,        # EST (EDT = -4)
    "Chicago": -6.0,        # CST (CDT = -5)
    "Los Angeles": -8.0,    # PST (PDT = -7)
    "Denver": -7.0,         # MST (MDT = -6)
    "Seattle": -8.0,        # PST (PDT = -7)
    "Toronto": -5.0,        # EST (EDT = -4)
    # South America
    "Buenos Aires": -3.0,   # ART (no DST)
    "Sao Paulo": -3.0,      # BRT (no DST since 2019)
    # Europe (standard time)
    "London": 0.0,          # GMT (BST = +1)
    "Paris": 1.0,           # CET (CEST = +2)
    "Madrid": 1.0,          # CET (CEST = +2)
    "Munich": 1.0,          # CET (CEST = +2)
    "Milan": 1.0,           # CET (CEST = +2)
    "Warsaw": 1.0,          # CET (CEST = +2)
    # Middle East
    "Tel Aviv": 2.0,        # IST (IDT = +3)
    "Ankara": 3.0,          # TRT (no DST)
    # South Asia
    "Lucknow": 5.5,         # IST (no DST)
    # East Asia
    "Tokyo": 9.0,           # JST (no DST)
    "Seoul": 9.0,           # KST (no DST)
    "Shanghai": 8.0,        # CST (no DST)
    "Hong Kong": 8.0,       # HKT (no DST)
    "Taipei": 8.0,          # CST (no DST)
    "Singapore": 8.0,       # SGT (no DST)
    # Oceania
    "Wellington": 12.0,     # NZST (NZDT = +13)
}


def get_wu_observation_window(city: str, date: str) -> tuple[str, str]:
    """Return the UTC time window for WU's midnight-to-midnight local day.

    WU reports the daily high as the maximum temperature observed between
    midnight and midnight local time. This function converts that window
    to UTC ISO timestamps.

    Args:
        city: City name (must be in CITY_UTC_OFFSETS).
        date: Target date as YYYY-MM-DD string.

    Returns:
        (start_iso, end_iso) — UTC ISO 8601 timestamps for the window.

    Raises:
        ValueError: If city is not in the timezone mapping.
    """
    if city not in CITY_UTC_OFFSETS:
        raise ValueError(
            f"Unknown city '{city}'. Add UTC offset to CITY_UTC_OFFSETS in "
            f"wunderground_alignment.py"
        )

    utc_offset_hours = CITY_UTC_OFFSETS[city]

    # Parse the target date
    target = datetime.strptime(date, "%Y-%m-%d")

    # Midnight local time in UTC = midnight - offset
    # e.g., New York EST (-5): midnight local = 05:00 UTC
    local_tz = timezone(timedelta(hours=utc_offset_hours))
    local_midnight = target.replace(hour=0, minute=0, second=0, tzinfo=local_tz)
    local_end = local_midnight + timedelta(days=1)

    # Convert to UTC
    start_utc = local_midnight.astimezone(timezone.utc)
    end_utc = local_end.astimezone(timezone.utc)

    start_iso = start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    log.debug(
        "wu_alignment.window",
        city=city,
        date=date,
        utc_offset=utc_offset_hours,
        start_utc=start_iso,
        end_utc=end_iso,
    )

    return start_iso, end_iso


def extract_daily_high_wu_aligned(
    hourly_temps: list[float],
    hourly_times: list[str],
    city: str,
    date: str,
) -> float:
    """Extract the daily high temperature from the WU-aligned time window.

    Open-Meteo returns hourly data — this function filters to only the hours
    that fall within WU's midnight-to-midnight local time window, then returns
    the maximum temperature.

    Args:
        hourly_temps: List of hourly temperature values from Open-Meteo.
        hourly_times: List of ISO 8601 time strings corresponding to hourly_temps.
        city: City name for timezone lookup.
        date: Target date as YYYY-MM-DD.

    Returns:
        Maximum temperature within the WU observation window.

    Raises:
        ValueError: If no temperatures fall within the window, or if
                    hourly_temps and hourly_times have different lengths.
    """
    if len(hourly_temps) != len(hourly_times):
        raise ValueError(
            f"hourly_temps ({len(hourly_temps)}) and hourly_times "
            f"({len(hourly_times)}) must have the same length"
        )

    start_iso, end_iso = get_wu_observation_window(city, date)

    # Parse window boundaries
    start_utc = datetime.strptime(start_iso, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    end_utc = datetime.strptime(end_iso, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )

    # Filter temperatures to the WU window
    temps_in_window: list[float] = []
    for temp, time_str in zip(hourly_temps, hourly_times):
        # Handle both "2025-03-20T14:00" and "2025-03-20T14:00:00Z" formats
        time_str_clean = time_str.rstrip("Z")
        if len(time_str_clean) == 16:
            # "YYYY-MM-DDTHH:MM" format (Open-Meteo local time)
            # Open-Meteo returns local time by default — convert using city offset
            dt_naive = datetime.strptime(time_str_clean, "%Y-%m-%dT%H:%M")
            utc_offset_hours = CITY_UTC_OFFSETS[city]
            local_tz = timezone(timedelta(hours=utc_offset_hours))
            dt_local = dt_naive.replace(tzinfo=local_tz)
            dt_utc = dt_local.astimezone(timezone.utc)
        else:
            # Full ISO format with seconds
            dt_naive = datetime.strptime(time_str_clean, "%Y-%m-%dT%H:%M:%S")
            dt_utc = dt_naive.replace(tzinfo=timezone.utc)

        if start_utc <= dt_utc < end_utc:
            temps_in_window.append(temp)

    if not temps_in_window:
        raise ValueError(
            f"No temperatures found in WU window for {city} on {date} "
            f"(window: {start_iso} to {end_iso}, "
            f"data range: {hourly_times[0] if hourly_times else 'empty'} "
            f"to {hourly_times[-1] if hourly_times else 'empty'})"
        )

    daily_high = max(temps_in_window)

    log.debug(
        "wu_alignment.daily_high",
        city=city,
        date=date,
        daily_high=round(daily_high, 1),
        n_hours_in_window=len(temps_in_window),
    )

    return daily_high
