"""Historical data fetcher — backfill forecast-vs-actual pairs for calibration bootstrap.

Fetches recent historical ensemble forecasts from Open-Meteo's archive and
actual temperatures from Weather Underground/NWS to build the initial
calibration training set.
"""

from __future__ import annotations

import asyncio
import json
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import structlog

from syndicate.polymarket.constants import CITY_STATIONS
from syndicate.polymarket.data.wunderground import fetch_actual_high
from syndicate.polymarket.models import TemperatureUnit

logger = structlog.get_logger()

# ── Constants ────────────────────────────────────────────────────────────────

HISTORICAL_FORECAST_API = (
    "https://historical-forecast-api.open-meteo.com/v1/forecast"
)
HISTORICAL_MODELS = ["gfs_seamless", "ecmwf_ifs025", "icon_seamless"]
HISTORICAL_TIMEOUT = 60

# Rate limiter — shared across all cities to respect Open-Meteo free tier
_hist_semaphore = asyncio.Semaphore(1)
_HIST_REQUEST_GAP = 1.5  # seconds between requests


# ── Single-city backfill ─────────────────────────────────────────────────────


async def backfill_city(
    city: str,
    lat: float,
    lon: float,
    unit: TemperatureUnit,
    icao: str,
    wunderground_path: str,
    days_back: int = 30,
) -> list[dict]:
    """Backfill historical forecast-vs-actual pairs for a single city.

    For each of the last *days_back* days, fetches the ensemble forecast
    (mean + std from Open-Meteo's historical endpoint) and the actual high
    from WU/NWS.

    Args:
        city: City name (e.g., "New York").
        lat: Latitude of the forecast point.
        lon: Longitude of the forecast point.
        unit: Temperature unit for the city (fahrenheit / celsius).
        icao: ICAO station code for WU/NWS lookups.
        wunderground_path: WU URL path for scraping.
        days_back: Number of historical days to fetch.

    Returns:
        List of dicts, each containing:
            date, city, ensemble_mean, ensemble_std, actual, model_means
    """
    results: list[dict] = []
    today = datetime.now(timezone.utc).date()

    temp_unit = unit.value  # "fahrenheit" or "celsius"

    async with httpx.AsyncClient(timeout=HISTORICAL_TIMEOUT) as client:
        for offset in range(1, days_back + 1):
            target_date = today - timedelta(days=offset)
            date_str = target_date.isoformat()

            try:
                # Fetch historical ensemble forecast from Open-Meteo
                params = {
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "temperature_2m_max",
                    "models": ",".join(HISTORICAL_MODELS),
                    "start_date": date_str,
                    "end_date": date_str,
                    "temperature_unit": temp_unit,
                }
                # Rate-limited: serialize all historical requests globally
                async with _hist_semaphore:
                    await asyncio.sleep(_HIST_REQUEST_GAP)
                    resp = await client.get(HISTORICAL_FORECAST_API, params=params)
                resp.raise_for_status()
                data = resp.json()

                # Extract per-model forecasts
                daily = data.get("daily", {})
                model_means: dict[str, float] = {}

                for model in HISTORICAL_MODELS:
                    key = f"temperature_2m_max_{model}"
                    values = daily.get(key, [])
                    if values and values[0] is not None:
                        model_means[model] = float(values[0])

                if not model_means:
                    logger.debug(
                        "historical.no_forecast_data",
                        city=city,
                        date=date_str,
                    )
                    continue

                all_values = list(model_means.values())
                ensemble_mean = statistics.mean(all_values)
                ensemble_std = (
                    statistics.stdev(all_values) if len(all_values) > 1 else 0.0
                )

                # Fetch actual high temperature
                actual = await fetch_actual_high(
                    icao=icao,
                    wunderground_path=wunderground_path,
                    date=date_str,
                    unit=unit,
                )
                if actual is None:
                    logger.debug(
                        "historical.no_actual_data",
                        city=city,
                        date=date_str,
                    )
                    continue

                results.append({
                    "date": date_str,
                    "city": city,
                    "ensemble_mean": round(ensemble_mean, 2),
                    "ensemble_std": round(ensemble_std, 2),
                    "actual": actual,
                    "model_means": {
                        k: round(v, 2) for k, v in model_means.items()
                    },
                })

                logger.debug(
                    "historical.backfill_point",
                    city=city,
                    date=date_str,
                    mean=round(ensemble_mean, 2),
                    actual=actual,
                )

            except Exception:
                logger.warning(
                    "historical.backfill_failed",
                    city=city,
                    date=date_str,
                    exc_info=True,
                )
                continue

    logger.info(
        "historical.city_complete",
        city=city,
        points=len(results),
        days_attempted=days_back,
    )
    return results


# ── All-cities backfill ──────────────────────────────────────────────────────


async def backfill_all_cities(
    days_back: int = 30,
) -> dict[str, list[dict]]:
    """Backfill historical data for all cities, with concurrency control.

    Runs :func:`backfill_city` for every city in ``CITY_STATIONS`` in
    parallel, capped by a semaphore (max 5 concurrent) to avoid hammering
    the APIs.

    Args:
        days_back: Number of historical days per city.

    Returns:
        Mapping of city name to list of backfill records.
    """
    sem = asyncio.Semaphore(3)
    all_data: dict[str, list[dict]] = {}

    async def _limited(city: str, cfg) -> tuple[str, list[dict]]:
        async with sem:
            data = await backfill_city(
                city=city,
                lat=cfg.latitude,
                lon=cfg.longitude,
                unit=cfg.unit,
                icao=cfg.icao,
                wunderground_path=cfg.wunderground_url,
                days_back=days_back,
            )
            return city, data

    tasks = [
        _limited(name, cfg)
        for name, cfg in CITY_STATIONS.items()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, BaseException):
            logger.warning("historical.city_error", error=str(result))
            continue
        city, data = result
        all_data[city] = data

    total_points = sum(len(v) for v in all_data.values())
    logger.info(
        "historical.backfill_complete",
        cities=len(all_data),
        total_points=total_points,
    )
    return all_data


# ── Persistence ──────────────────────────────────────────────────────────────


def save_historical(data: dict[str, list[dict]], path: Path) -> None:
    """Save backfilled historical data to a JSON file.

    Args:
        data: City-keyed mapping of backfill records.
        path: Destination file path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))
    logger.info("historical.saved", path=str(path), cities=len(data))


def load_historical(path: Path) -> dict[str, list[dict]]:
    """Load previously saved historical data from JSON.

    Args:
        path: Source file path.

    Returns:
        City-keyed mapping, or empty dict if the file doesn't exist.
    """
    if not path.exists():
        logger.info("historical.no_file", path=str(path))
        return {}
    try:
        raw = json.loads(path.read_text())
        logger.info(
            "historical.loaded",
            path=str(path),
            cities=len(raw),
        )
        return raw
    except (json.JSONDecodeError, OSError):
        logger.warning("historical.load_failed", path=str(path), exc_info=True)
        return {}
