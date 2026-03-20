"""Open-Meteo ensemble API — fetch multi-model temperature forecasts.

Queries 4 NWP models in parallel for 173 total ensemble members:
  - GFS Seamless:   31 members (NOAA)
  - ECMWF IFS 0.25: 51 members (ECMWF deterministic + perturbations)
  - ECMWF AIFS 0.25: 51 members (ECMWF AI model)
  - ICON Seamless:  40 members (DWD)

Each member provides hourly 2m temperature. We extract the daily high
for the target date (max of 24 hourly values) to build a probability
distribution over temperature bins.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from syndicate.polymarket.constants import (
    ENSEMBLE_API,
    ENSEMBLE_FORECAST_DAYS,
    ENSEMBLE_MODELS,
    ENSEMBLE_TIMEOUT,
    FORECAST_CACHE_TTL_SECONDS,
    ModelConfig,
)
from syndicate.polymarket.models import EnsembleForecast, EnsembleMember, TemperatureUnit

logger = structlog.get_logger()

# ── Simple TTL cache for ensemble forecasts ───────────────────────────────────

_cache: dict[str, tuple[float, EnsembleForecast]] = {}  # key → (timestamp, forecast)


def _cache_key(city: str, target_date: str, model: str) -> str:
    return f"{city}:{target_date}:{model}"


def _get_cached(city: str, target_date: str) -> EnsembleForecast | None:
    """Return a cached composite forecast if all model entries are still fresh."""
    now = time.monotonic()
    members: list[EnsembleMember] = []
    all_found = True

    for model_cfg in ENSEMBLE_MODELS:
        key = _cache_key(city, target_date, model_cfg.name)
        entry = _cache.get(key)
        if entry is None or (now - entry[0]) > FORECAST_CACHE_TTL_SECONDS:
            all_found = False
            break
        members.extend(entry[1].members)

    if all_found and members:
        return EnsembleForecast(
            city=city,
            target_date=target_date,
            fetched_at=datetime.now(timezone.utc),
            members=members,
        )
    return None


def _put_cache(city: str, target_date: str, model_name: str, forecast: EnsembleForecast) -> None:
    """Cache a single model's forecast members."""
    _cache[_cache_key(city, target_date, model_name)] = (time.monotonic(), forecast)


# ── Per-model fetch ───────────────────────────────────────────────────────────


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    reraise=True,
)
async def _fetch_single_model(
    client: httpx.AsyncClient,
    model_cfg: ModelConfig,
    lat: float,
    lon: float,
    unit: TemperatureUnit,
    target_date: str,
) -> list[EnsembleMember]:
    """Fetch ensemble members for a single NWP model from Open-Meteo.

    Returns a list of EnsembleMember objects, one per member, each containing
    the daily high temperature for the target date.
    """
    temp_unit = "fahrenheit" if unit == TemperatureUnit.FAHRENHEIT else "celsius"

    # Open-Meteo uses different API model names than our internal names.
    # Map: "gfs" → "gfs_seamless", "ecmwf_ifs" → "ecmwf_ifs025", etc.
    api_model_name = {
        "gfs": "gfs_seamless",
        "ecmwf_ifs": "ecmwf_ifs025",
        "ecmwf_aifs": "ecmwf_aifs025",
        "icon": "icon_seamless",
    }.get(model_cfg.name, f"{model_cfg.name}_seamless")

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m",
        "models": api_model_name,
        "temperature_unit": temp_unit,
        "timezone": "auto",
        "forecast_days": ENSEMBLE_FORECAST_DAYS,
    }

    resp = await client.get(ENSEMBLE_API, params=params)
    resp.raise_for_status()
    data = resp.json()

    hourly = data.get("hourly", {})
    times: list[str] = hourly.get("time", [])

    if not times:
        logger.warning(
            "open_meteo.no_times",
            model=model_cfg.name,
            lat=lat,
            lon=lon,
        )
        return []

    # Find indices for the target date's hours.
    # Times are in ISO format like "2026-03-20T00:00", "2026-03-20T01:00", etc.
    target_indices: list[int] = []
    for i, t in enumerate(times):
        if t.startswith(target_date):
            target_indices.append(i)

    if not target_indices:
        logger.warning(
            "open_meteo.target_date_not_found",
            model=model_cfg.name,
            target_date=target_date,
            first_time=times[0] if times else None,
            last_time=times[-1] if times else None,
        )
        return []

    # Extract daily high for each ensemble member.
    # Member keys are like "temperature_2m_member0", "temperature_2m_member1", etc.
    members: list[EnsembleMember] = []
    for member_idx in range(model_cfg.members):
        key = f"temperature_2m_member{member_idx}"
        temps = hourly.get(key)
        if temps is None:
            continue

        # Extract temps for the target date hours only
        day_temps: list[float] = []
        for idx in target_indices:
            if idx < len(temps) and temps[idx] is not None:
                try:
                    day_temps.append(float(temps[idx]))
                except (ValueError, TypeError):
                    continue

        if not day_temps:
            continue

        daily_high = max(day_temps)
        members.append(
            EnsembleMember(
                model=model_cfg.name,
                member_index=member_idx,
                daily_high=daily_high,
            )
        )

    logger.debug(
        "open_meteo.model_fetched",
        model=model_cfg.name,
        members_parsed=len(members),
        expected=model_cfg.members,
        target_date=target_date,
    )
    return members


# ── Public API ────────────────────────────────────────────────────────────────


async def fetch_ensemble_forecast(
    city: str,
    lat: float,
    lon: float,
    unit: TemperatureUnit,
    target_date: str,
) -> EnsembleForecast:
    """Fetch ensemble forecasts from all 4 NWP models for a city and target date.

    Queries Open-Meteo in parallel for GFS, ECMWF IFS, ECMWF AIFS, and ICON.
    Returns an EnsembleForecast containing up to 173 daily-high temperature values.

    Results are cached for 30 minutes.

    Args:
        city: City name (for logging and cache key).
        lat: Latitude of the weather station.
        lon: Longitude of the weather station.
        unit: Temperature unit (FAHRENHEIT or CELSIUS).
        target_date: Date string in YYYY-MM-DD format.

    Returns:
        EnsembleForecast with all successfully fetched members.
    """
    # Check cache first
    cached = _get_cached(city, target_date)
    if cached is not None:
        logger.debug(
            "open_meteo.cache_hit",
            city=city,
            target_date=target_date,
            members=len(cached.members),
        )
        return cached

    # Fetch all 4 models in parallel
    async with httpx.AsyncClient(timeout=ENSEMBLE_TIMEOUT) as client:
        tasks = [
            _fetch_single_model(client, model_cfg, lat, lon, unit, target_date)
            for model_cfg in ENSEMBLE_MODELS
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Merge results, handling any individual model failures gracefully
    all_members: list[EnsembleMember] = []
    for model_cfg, result in zip(ENSEMBLE_MODELS, results):
        if isinstance(result, Exception):
            logger.warning(
                "open_meteo.model_failed",
                model=model_cfg.name,
                error=str(result),
            )
            continue

        all_members.extend(result)

        # Cache each model's result individually
        model_forecast = EnsembleForecast(
            city=city,
            target_date=target_date,
            fetched_at=datetime.now(timezone.utc),
            members=result,
        )
        _put_cache(city, target_date, model_cfg.name, model_forecast)

    forecast = EnsembleForecast(
        city=city,
        target_date=target_date,
        fetched_at=datetime.now(timezone.utc),
        members=all_members,
    )

    logger.info(
        "open_meteo.forecast_complete",
        city=city,
        target_date=target_date,
        total_members=len(all_members),
        models_ok=sum(
            1 for r in results if not isinstance(r, Exception)
        ),
        mean=round(forecast.mean, 1) if all_members else None,
        std=round(forecast.std, 1) if len(all_members) > 1 else None,
    )
    return forecast
