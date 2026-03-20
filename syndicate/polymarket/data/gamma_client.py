"""Polymarket Gamma API client — discover active weather markets."""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from syndicate.polymarket.constants import (
    CITY_STATIONS,
    GAMMA_BASE,
    GAMMA_PAGE_LIMIT,
    GAMMA_TIMEOUT,
)
from syndicate.polymarket.models import CityConfig, TemperatureBin, TemperatureUnit, WeatherMarket

logger = structlog.get_logger()

# ── Regex patterns for parsing temperature bin labels ─────────────────────────
# Real Polymarket labels use ° symbol: "22°C or higher", "12°C or below", "13°C"
# Also handle without °: "22C or higher", "36-37F"

# Fahrenheit: "35°F or below", "36-37°F", "54°F or higher"
_RE_F_RANGE = re.compile(r"(\d+)\s*[-–]\s*(\d+)\s*°?\s*F", re.IGNORECASE)
_RE_F_BELOW = re.compile(r"(\d+)\s*°?\s*F\s+or\s+below", re.IGNORECASE)
_RE_F_ABOVE = re.compile(r"(\d+)\s*°?\s*F\s+or\s+(above|higher)", re.IGNORECASE)

# Celsius: "12°C or below", "13°C", "-3°C", "14-15°C", "22°C or higher"
_RE_C_RANGE = re.compile(r"(-?\d+)\s*[-–]\s*(-?\d+)\s*°?\s*C", re.IGNORECASE)
_RE_C_SINGLE = re.compile(r"^(-?\d+)\s*°?\s*C$", re.IGNORECASE)
_RE_C_BELOW = re.compile(r"(-?\d+)\s*°?\s*C\s+or\s+below", re.IGNORECASE)
_RE_C_ABOVE = re.compile(r"(-?\d+)\s*°?\s*C\s+or\s+(above|higher)", re.IGNORECASE)

# Title: "Highest temperature in London on March 19?"
# Also: "What will the high temperature be in New York City on March 20?"
_RE_TITLE_CITY_DATE = re.compile(
    r"(?:highest|high)\s+temperature\s+in\s+(.+?)\s+on\s+(.+?)[\?\.]?\s*$",
    re.IGNORECASE,
)

# Slug: "highest-temperature-in-london-on-march-19-2026"
_RE_SLUG_CITY_DATE = re.compile(
    r"highest?-temperature-in-(.+?)-on-(\w+-\d+(?:-\d+)?)",
    re.IGNORECASE,
)

# Date patterns in titles: "March 20", "March 20, 2026"
_MONTH_MAP: dict[str, int] = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def _parse_date_from_text(text: str) -> str | None:
    """Extract a YYYY-MM-DD date from natural language like 'March 20' or 'March 20, 2026'."""
    text = text.strip().rstrip("?.")
    # Try "Month Day, Year"
    m = re.match(r"(\w+)\s+(\d{1,2}),?\s+(\d{4})", text)
    if m:
        month_name, day, year = m.group(1).lower(), int(m.group(2)), int(m.group(3))
        month = _MONTH_MAP.get(month_name)
        if month:
            return f"{year:04d}-{month:02d}-{day:02d}"

    # Try "Month Day" (assume current year)
    m = re.match(r"(\w+)\s+(\d{1,2})", text)
    if m:
        month_name, day = m.group(1).lower(), int(m.group(2))
        month = _MONTH_MAP.get(month_name)
        if month:
            now = datetime.now(timezone.utc)
            year = now.year
            try:
                candidate = datetime(year, month, day, tzinfo=timezone.utc)
                if (candidate - now).days < -30:
                    year += 1
            except ValueError:
                pass
            return f"{year:04d}-{month:02d}-{day:02d}"

    return None


def _match_city(raw_city: str) -> tuple[str, CityConfig] | None:
    """Match a raw city string from a title/slug to a known station."""
    cleaned = raw_city.strip()

    # Exact match
    if cleaned in CITY_STATIONS:
        return cleaned, CITY_STATIONS[cleaned]

    # Case-insensitive match
    for key, cfg in CITY_STATIONS.items():
        if key.lower() == cleaned.lower():
            return key, cfg

    # Substring: "New York City" contains "New York", "NYC" → "New York"
    for key, cfg in CITY_STATIONS.items():
        if key.lower() in cleaned.lower() or cleaned.lower() in key.lower():
            return key, cfg

    # Common abbreviations
    abbrevs = {"nyc": "New York", "la": "Los Angeles", "sf": "San Francisco"}
    lower = cleaned.lower()
    if lower in abbrevs:
        canonical = abbrevs[lower]
        if canonical in CITY_STATIONS:
            return canonical, CITY_STATIONS[canonical]

    # Slug-style: "new-york-city" → "new york city"
    slug_cleaned = cleaned.replace("-", " ").replace("_", " ")
    for key, cfg in CITY_STATIONS.items():
        if key.lower() in slug_cleaned.lower() or slug_cleaned.lower() in key.lower():
            return key, cfg

    return None


def _parse_bin_label(label: str, unit: TemperatureUnit) -> tuple[float, float] | None:
    """Parse a temperature bin label into (lower_inclusive, upper_exclusive) bounds."""
    if unit == TemperatureUnit.FAHRENHEIT:
        m = _RE_F_BELOW.search(label)
        if m:
            return -math.inf, float(int(m.group(1)) + 1)

        m = _RE_F_ABOVE.search(label)
        if m:
            return float(int(m.group(1))), math.inf

        m = _RE_F_RANGE.search(label)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            return float(lo), float(hi + 1)

    else:  # Celsius
        m = _RE_C_BELOW.search(label)
        if m:
            return -math.inf, float(int(m.group(1)) + 1)

        m = _RE_C_ABOVE.search(label)
        if m:
            return float(int(m.group(1))), math.inf

        m = _RE_C_RANGE.search(label)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            return float(lo), float(hi + 1)

        # Single degree: "13°C" → (13, 14)
        m = _RE_C_SINGLE.search(label.strip())
        if m:
            val = int(m.group(1))
            return float(val), float(val + 1)

    return None


def _extract_market_price(market: dict) -> float:
    """Extract the YES price from a Gamma market object."""
    try:
        prices = market.get("outcomePrices", "")
        if isinstance(prices, str):
            prices = prices.strip("[]").split(",")
            return float(prices[0].strip().strip('"'))
        elif isinstance(prices, list) and len(prices) > 0:
            return float(prices[0])
    except (ValueError, IndexError):
        pass
    return 0.0


def _extract_token_id(market: dict) -> str:
    """Extract the YES token ID from a Gamma market object."""
    tokens = market.get("tokens", [])
    if isinstance(tokens, list):
        for token in tokens:
            if isinstance(token, dict):
                outcome = token.get("outcome", "").upper()
                if outcome == "YES":
                    return str(token.get("token_id", ""))
        if tokens and isinstance(tokens[0], dict):
            return str(tokens[0].get("token_id", ""))
    return ""


def _is_weather_event(event: dict) -> bool:
    """Quick check if an event is a weather temperature market."""
    title = event.get("title", "").lower()
    slug = event.get("slug", "").lower()
    return "temperature" in title or "temperature" in slug


def _parse_event_to_market(event: dict) -> WeatherMarket | None:
    """Parse a Gamma API event into a WeatherMarket object."""
    title = event.get("title", "")
    slug = event.get("slug", "")
    sub_markets = event.get("markets", [])

    if not sub_markets:
        return None

    # ── Extract city and date from title ──
    city_name: str | None = None
    city_config: CityConfig | None = None
    date_str: str | None = None

    m = _RE_TITLE_CITY_DATE.search(title)
    if m:
        raw_city, raw_date = m.group(1), m.group(2)
        result = _match_city(raw_city)
        if result:
            city_name, city_config = result
        date_str = _parse_date_from_text(raw_date)

    # Fallback: parse slug like "highest-temperature-in-london-on-march-19-2026"
    if not city_name or not date_str:
        m = _RE_SLUG_CITY_DATE.search(slug)
        if m:
            raw_city_slug = m.group(1).replace("-", " ")
            raw_date_slug = m.group(2).replace("-", " ")
            if not city_name:
                result = _match_city(raw_city_slug)
                if result:
                    city_name, city_config = result
            if not date_str:
                date_str = _parse_date_from_text(raw_date_slug)

    if not city_name or not city_config or not date_str:
        logger.debug(
            "weather_market.skip_unparseable",
            title=title,
            slug=slug,
            city=city_name,
            date=date_str,
        )
        return None

    unit = city_config.unit

    # ── Parse each sub-market into a temperature bin ──
    bins: list[TemperatureBin] = []
    total_volume = 0.0

    for idx, mkt in enumerate(sub_markets):
        # Use groupItemTitle for bin label (e.g., "22°C or higher", "13°C")
        label = mkt.get("groupItemTitle", "") or mkt.get("question", "")
        if not label:
            continue

        bounds = _parse_bin_label(label, unit)
        if bounds is None:
            logger.debug("weather_market.skip_bin", label=label, slug=slug)
            continue

        lower, upper = bounds
        token_id = _extract_token_id(mkt)
        price = _extract_market_price(mkt)

        vol = 0.0
        try:
            vol = float(mkt.get("volume", 0) or 0)
        except (ValueError, TypeError):
            pass
        total_volume += vol

        bins.append(
            TemperatureBin(
                index=idx,
                label=label,
                lower=lower,
                upper=upper,
                token_id=token_id,
                market_price=price,
            )
        )

    if not bins:
        logger.debug("weather_market.no_valid_bins", slug=slug)
        return None

    # Sort bins by temperature ascending, re-index
    bins.sort(key=lambda b: b.lower)
    for i, b in enumerate(bins):
        b.index = i

    # Use event ID as condition_id (market-level condition_id is often empty)
    condition_id = str(event.get("id", slug))

    return WeatherMarket(
        condition_id=condition_id,
        event_slug=slug,
        city=city_name,
        date=date_str,
        unit=unit,
        bins=bins,
        total_volume=total_volume,
        last_updated=datetime.now(timezone.utc),
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def _fetch_events_page(
    client: httpx.AsyncClient,
    offset: int = 0,
) -> list[dict]:
    """Fetch a page of events from the Gamma API."""
    params: dict[str, str | int] = {
        "active": "true",
        "closed": "false",
        "limit": GAMMA_PAGE_LIMIT,
        "offset": offset,
        "order": "volume24hr",
        "ascending": "false",
    }
    resp = await client.get(f"{GAMMA_BASE}/events", params=params)
    resp.raise_for_status()
    data = resp.json()

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return []


async def discover_weather_markets() -> list[WeatherMarket]:
    """Fetch all active weather/temperature markets from the Gamma API.

    The Gamma API doesn't reliably filter by tag, so we fetch all active events
    and filter client-side for temperature markets.
    """
    markets: dict[str, WeatherMarket] = {}  # condition_id → market (dedup)

    async with httpx.AsyncClient(timeout=GAMMA_TIMEOUT) as client:
        offset = 0
        empty_pages = 0
        while offset < 10_000:  # Safety cap
            try:
                events = await _fetch_events_page(client, offset)
            except Exception:
                logger.warning("gamma.fetch_failed", offset=offset, exc_info=True)
                break

            if not events:
                break

            # Filter to temperature events only, then parse
            weather_events = [e for e in events if _is_weather_event(e)]
            if not weather_events:
                empty_pages += 1
                # Stop after 3 consecutive pages with no weather events
                # (weather markets are high-volume, so they appear early)
                if empty_pages >= 3:
                    break
            else:
                empty_pages = 0

            for event in weather_events:
                parsed = _parse_event_to_market(event)
                if parsed and parsed.condition_id not in markets:
                    markets[parsed.condition_id] = parsed

            if len(events) < GAMMA_PAGE_LIMIT:
                break
            offset += GAMMA_PAGE_LIMIT

    result = sorted(markets.values(), key=lambda m: m.date)
    logger.info(
        "gamma.discovery_complete",
        markets_found=len(result),
        cities=list({m.city for m in result}),
    )
    return result
