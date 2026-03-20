"""Weather Underground — fetch actual observed temperatures for market resolution.

Two strategies, tried in order:
  1. NWS API (US stations only) — free, structured JSON, reliable.
  2. Weather Underground history page — scrape the daily summary table for
     the observed high temperature.

The actual high temperature is used to resolve markets after their target date
passes. Results are cached permanently since observed temps never change.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from syndicate.polymarket.constants import (
    NWS_API_BASE,
    NWS_TIMEOUT,
    WUNDERGROUND_BASE,
    WUNDERGROUND_TIMEOUT,
)
from syndicate.polymarket.models import TemperatureUnit

logger = structlog.get_logger()

# ── Permanent cache for observed temperatures ─────────────────────────────────
# Once a day's actual high is known it never changes, so we cache forever.

_actual_cache: dict[str, float] = {}  # "ICAO:YYYY-MM-DD" → daily high


def _cache_key(icao: str, date: str) -> str:
    return f"{icao}:{date}"


# ── NWS API (US stations only) ────────────────────────────────────────────────


def _is_us_station(icao: str) -> bool:
    """Check if an ICAO code is a US station (starts with K or P)."""
    return icao.startswith("K") or icao.startswith("P")


def _celsius_to_fahrenheit(c: float) -> float:
    return c * 9.0 / 5.0 + 32.0


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def _fetch_nws_observations(
    client: httpx.AsyncClient,
    icao: str,
    date: str,
) -> list[float]:
    """Fetch hourly observations from the NWS API for a US station.

    The NWS API returns observations in Celsius. We return raw Celsius values
    and let the caller convert.

    Args:
        client: httpx async client.
        icao: ICAO station code (e.g., "KLGA").
        date: Date string in YYYY-MM-DD format.

    Returns:
        List of observed temperatures in Celsius for all hours of the day.
    """
    # NWS wants ISO 8601 timestamps
    start = f"{date}T00:00:00Z"
    end = f"{date}T23:59:59Z"

    url = f"{NWS_API_BASE}/stations/{icao}/observations"
    params = {
        "start": start,
        "end": end,
    }
    headers = {
        "Accept": "application/geo+json",
        "User-Agent": "SyndicateFund/1.0 (weather-oracle)",
    }

    resp = await client.get(url, params=params, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    features = data.get("features", [])
    temps: list[float] = []

    for feature in features:
        props = feature.get("properties", {})
        temp_data = props.get("temperature", {})
        value = temp_data.get("value")
        if value is not None:
            try:
                temps.append(float(value))
            except (ValueError, TypeError):
                continue

    return temps


async def fetch_actual_high_nws(
    icao: str,
    date: str,
    unit: TemperatureUnit,
) -> float | None:
    """Fetch the observed daily high from the NWS API (US stations only).

    Args:
        icao: ICAO station code (e.g., "KLGA").
        date: Date string in YYYY-MM-DD format.
        unit: Desired temperature unit for the result.

    Returns:
        Daily high temperature in the requested unit, or None on failure.
    """
    if not _is_us_station(icao):
        return None

    try:
        async with httpx.AsyncClient(timeout=NWS_TIMEOUT) as client:
            temps_c = await _fetch_nws_observations(client, icao, date)

        if not temps_c:
            logger.warning("nws.no_observations", station=icao, date=date)
            return None

        high_c = max(temps_c)

        if unit == TemperatureUnit.FAHRENHEIT:
            return round(_celsius_to_fahrenheit(high_c), 1)
        return round(high_c, 1)

    except Exception:
        logger.warning("nws.fetch_failed", station=icao, date=date, exc_info=True)
        return None


# ── Weather Underground scraping ──────────────────────────────────────────────

# Regex patterns for finding the daily high in WU's history page HTML.
# The page includes a daily summary table with the high temperature.
# Pattern matches things like:
#   "Max</span><span ...>54</span>" or structured data in JSON-LD
_RE_DAILY_HIGH = re.compile(
    r'"maxTemperature"[:\s]*[{].*?"value"[:\s]*([0-9.]+)',
    re.DOTALL,
)

# Fallback: look for the temperature in the daily observations summary section.
# WU pages typically have a summary row with "Max" and a temperature value.
_RE_MAX_TEMP_SUMMARY = re.compile(
    r'<td[^>]*>\s*Max\s*</td>\s*<td[^>]*>\s*(\d+)\s*',
    re.IGNORECASE | re.DOTALL,
)

# Another fallback: look for the max temp in the daily summary JSON embedded in the page
_RE_SUMMARY_JSON = re.compile(
    r'"temperature":\s*\{\s*"high":\s*(\d+)',
)

# WU sometimes puts the daily high in a data attribute
_RE_DATA_HIGH = re.compile(
    r'data-high=["\'](\d+)["\']',
    re.IGNORECASE,
)


def _parse_wunderground_date(date: str) -> str:
    """Convert YYYY-MM-DD to WU's URL format: YYYY-M-D (no zero padding)."""
    parts = date.split("-")
    if len(parts) != 3:
        return date
    year, month, day = parts
    return f"{int(year)}-{int(month)}-{int(day)}"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def _fetch_wunderground_page(
    client: httpx.AsyncClient,
    wunderground_path: str,
    date: str,
) -> str:
    """Fetch the WU daily history page HTML."""
    wu_date = _parse_wunderground_date(date)
    url = f"{WUNDERGROUND_BASE}/history/daily/{wunderground_path}/date/{wu_date}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = await client.get(url, headers=headers, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def _extract_high_from_html(html: str) -> float | None:
    """Try multiple regex patterns to extract the daily high from WU HTML.

    Returns the temperature as a float, or None if parsing fails.
    """
    # Try structured JSON-LD maxTemperature
    m = _RE_DAILY_HIGH.search(html)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass

    # Try summary table
    m = _RE_MAX_TEMP_SUMMARY.search(html)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass

    # Try embedded JSON summary
    m = _RE_SUMMARY_JSON.search(html)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass

    # Try data attribute
    m = _RE_DATA_HIGH.search(html)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass

    # Last resort: look for the observation table rows and find the highest temp.
    # WU pages have hourly observations in a table. We can find all temperature
    # values and take the max.
    all_temps = re.findall(
        r'<span[^>]*class="[^"]*wu-value[^"]*"[^>]*>(\d+)</span>',
        html,
    )
    if all_temps:
        try:
            values = [float(t) for t in all_temps]
            if values:
                return max(values)
        except ValueError:
            pass

    return None


async def fetch_actual_high_wunderground(
    wunderground_path: str,
    date: str,
) -> float | None:
    """Fetch the observed daily high from Weather Underground by scraping.

    The temperature is returned in whatever unit WU displays for the station
    (Fahrenheit for US, Celsius for international in most cases). However, WU
    pages for specific stations follow the station's local convention, which
    matches our CITY_STATIONS unit mapping.

    Args:
        wunderground_path: WU URL path like "us/ny/new-york-city/KLGA".
        date: Date string in YYYY-MM-DD format.

    Returns:
        Daily high temperature, or None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=WUNDERGROUND_TIMEOUT) as client:
            html = await _fetch_wunderground_page(client, wunderground_path, date)

        high = _extract_high_from_html(html)
        if high is not None:
            logger.debug(
                "wunderground.parsed_high",
                path=wunderground_path,
                date=date,
                high=high,
            )
            return high

        logger.warning(
            "wunderground.parse_failed",
            path=wunderground_path,
            date=date,
            html_length=len(html),
        )
        return None

    except Exception:
        logger.warning(
            "wunderground.fetch_failed",
            path=wunderground_path,
            date=date,
            exc_info=True,
        )
        return None


# ── Unified public API ────────────────────────────────────────────────────────


async def fetch_actual_high(
    icao: str,
    wunderground_path: str,
    date: str,
    unit: TemperatureUnit,
) -> float | None:
    """Fetch the observed daily high temperature for a station and date.

    Tries NWS API first (for US stations), then falls back to Weather
    Underground scraping. Results are cached permanently.

    Args:
        icao: ICAO station code (e.g., "KLGA").
        wunderground_path: WU URL path (e.g., "us/ny/new-york-city/KLGA").
        date: Date string in YYYY-MM-DD format.
        unit: Expected temperature unit for the result.

    Returns:
        Daily high temperature in the station's unit, or None if unavailable.
    """
    # Check permanent cache
    key = _cache_key(icao, date)
    if key in _actual_cache:
        logger.debug("actual_high.cache_hit", station=icao, date=date)
        return _actual_cache[key]

    # Ensure the date is in the past (don't try to fetch future actuals)
    try:
        target = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if target.date() >= now.date():
            logger.debug("actual_high.future_date", station=icao, date=date)
            return None
    except ValueError:
        logger.warning("actual_high.invalid_date", date=date)
        return None

    high: float | None = None

    # Strategy 1: NWS API (US stations only)
    if _is_us_station(icao):
        high = await fetch_actual_high_nws(icao, date, unit)
        if high is not None:
            _actual_cache[key] = high
            logger.info(
                "actual_high.resolved_nws",
                station=icao,
                date=date,
                high=high,
                unit=unit.value,
            )
            return high

    # Strategy 2: Weather Underground scraping
    high = await fetch_actual_high_wunderground(wunderground_path, date)
    if high is not None:
        _actual_cache[key] = high
        logger.info(
            "actual_high.resolved_wunderground",
            station=icao,
            date=date,
            high=high,
        )
        return high

    logger.warning(
        "actual_high.all_sources_failed",
        station=icao,
        date=date,
    )
    return None
