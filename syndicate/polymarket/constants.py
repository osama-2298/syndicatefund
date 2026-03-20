"""
Polymarket Weather Oracle — Constants & Station Mappings.

Station mappings for 26 cities to their ICAO codes and lat/lon coordinates.
These are airport weather stations that Weather Underground uses for resolution.

Model configs, edge thresholds, Kelly criterion parameters, and bankroll limits.
"""

from __future__ import annotations

from dataclasses import dataclass

from syndicate.polymarket.models import CityConfig, TemperatureUnit


# ── City → Airport Weather Station Mappings ────────────────────────────────
# Every station is an airport ICAO code used by Weather Underground for
# official high-temperature resolution.

CITY_STATIONS: dict[str, CityConfig] = {
    "New York": CityConfig(
        name="New York",
        icao="KLGA",
        latitude=40.7769,
        longitude=-73.8740,
        unit=TemperatureUnit.FAHRENHEIT,
        wunderground_url="us/ny/new-york-city/KLGA",
    ),
    "London": CityConfig(
        name="London",
        icao="EGLC",
        latitude=51.5053,
        longitude=0.0553,
        unit=TemperatureUnit.CELSIUS,
        wunderground_url="gb/london/EGLC",
    ),
    "Paris": CityConfig(
        name="Paris",
        icao="LFPG",
        latitude=49.0097,
        longitude=2.5479,
        unit=TemperatureUnit.CELSIUS,
        wunderground_url="fr/paris/LFPG",
    ),
    "Tokyo": CityConfig(
        name="Tokyo",
        icao="RJTT",
        latitude=35.5494,
        longitude=139.7798,
        unit=TemperatureUnit.CELSIUS,
        wunderground_url="jp/tokyo/RJTT",
    ),
    "Seoul": CityConfig(
        name="Seoul",
        icao="RKSI",
        latitude=37.4602,
        longitude=126.4407,
        unit=TemperatureUnit.CELSIUS,
        wunderground_url="kr/seoul/RKSI",
    ),
    "Tel Aviv": CityConfig(
        name="Tel Aviv",
        icao="LLBG",
        latitude=32.0114,
        longitude=34.8867,
        unit=TemperatureUnit.CELSIUS,
        wunderground_url="il/tel-aviv/LLBG",
    ),
    "Dallas": CityConfig(
        name="Dallas",
        icao="KDFW",
        latitude=32.8998,
        longitude=-97.0403,
        unit=TemperatureUnit.FAHRENHEIT,
        wunderground_url="us/tx/dallas/KDFW",
    ),
    "Miami": CityConfig(
        name="Miami",
        icao="KMIA",
        latitude=25.7959,
        longitude=-80.2870,
        unit=TemperatureUnit.FAHRENHEIT,
        wunderground_url="us/fl/miami/KMIA",
    ),
    "Atlanta": CityConfig(
        name="Atlanta",
        icao="KATL",
        latitude=33.6407,
        longitude=-84.4277,
        unit=TemperatureUnit.FAHRENHEIT,
        wunderground_url="us/ga/atlanta/KATL",
    ),
    "Chicago": CityConfig(
        name="Chicago",
        icao="KORD",
        latitude=41.9742,
        longitude=-87.9073,
        unit=TemperatureUnit.FAHRENHEIT,
        wunderground_url="us/il/chicago/KORD",
    ),
    "Los Angeles": CityConfig(
        name="Los Angeles",
        icao="KLAX",
        latitude=33.9425,
        longitude=-118.4081,
        unit=TemperatureUnit.FAHRENHEIT,
        wunderground_url="us/ca/los-angeles/KLAX",
    ),
    "Denver": CityConfig(
        name="Denver",
        icao="KDEN",
        latitude=39.8561,
        longitude=-104.6737,
        unit=TemperatureUnit.FAHRENHEIT,
        wunderground_url="us/co/denver/KDEN",
    ),
    "Toronto": CityConfig(
        name="Toronto",
        icao="CYYZ",
        latitude=43.6777,
        longitude=-79.6248,
        unit=TemperatureUnit.CELSIUS,
        wunderground_url="ca/on/toronto/CYYZ",
    ),
    "Buenos Aires": CityConfig(
        name="Buenos Aires",
        icao="SAEZ",
        latitude=-34.8222,
        longitude=-58.5358,
        unit=TemperatureUnit.CELSIUS,
        wunderground_url="ar/buenos-aires/SAEZ",
    ),
    "Sao Paulo": CityConfig(
        name="Sao Paulo",
        icao="SBGR",
        latitude=-23.4356,
        longitude=-46.4731,
        unit=TemperatureUnit.CELSIUS,
        wunderground_url="br/sao-paulo/SBGR",
    ),
    "Shanghai": CityConfig(
        name="Shanghai",
        icao="ZSPD",
        latitude=31.1434,
        longitude=121.8052,
        unit=TemperatureUnit.CELSIUS,
        wunderground_url="cn/shanghai/ZSPD",
    ),
    "Hong Kong": CityConfig(
        name="Hong Kong",
        icao="VHHH",
        latitude=22.3080,
        longitude=113.9185,
        unit=TemperatureUnit.CELSIUS,
        wunderground_url="hk/hong-kong/VHHH",
    ),
    "Singapore": CityConfig(
        name="Singapore",
        icao="WSSS",
        latitude=1.3502,
        longitude=103.9940,
        unit=TemperatureUnit.CELSIUS,
        wunderground_url="sg/singapore/WSSS",
    ),
    "Madrid": CityConfig(
        name="Madrid",
        icao="LEMD",
        latitude=40.4936,
        longitude=-3.5668,
        unit=TemperatureUnit.CELSIUS,
        wunderground_url="es/madrid/LEMD",
    ),
    "Munich": CityConfig(
        name="Munich",
        icao="EDDM",
        latitude=48.3538,
        longitude=11.7861,
        unit=TemperatureUnit.CELSIUS,
        wunderground_url="de/munich/EDDM",
    ),
    "Milan": CityConfig(
        name="Milan",
        icao="LIMC",
        latitude=45.6306,
        longitude=8.7281,
        unit=TemperatureUnit.CELSIUS,
        wunderground_url="it/milan/LIMC",
    ),
    "Warsaw": CityConfig(
        name="Warsaw",
        icao="EPWA",
        latitude=52.1657,
        longitude=20.9671,
        unit=TemperatureUnit.CELSIUS,
        wunderground_url="pl/warsaw/EPWA",
    ),
    "Taipei": CityConfig(
        name="Taipei",
        icao="RCTP",
        latitude=25.0797,
        longitude=121.2342,
        unit=TemperatureUnit.CELSIUS,
        wunderground_url="tw/taipei/RCTP",
    ),
    "Wellington": CityConfig(
        name="Wellington",
        icao="NZWN",
        latitude=-41.3272,
        longitude=174.8053,
        unit=TemperatureUnit.CELSIUS,
        wunderground_url="nz/wellington/NZWN",
    ),
    "Ankara": CityConfig(
        name="Ankara",
        icao="LTAC",
        latitude=40.1281,
        longitude=32.9951,
        unit=TemperatureUnit.CELSIUS,
        wunderground_url="tr/ankara/LTAC",
    ),
    "Lucknow": CityConfig(
        name="Lucknow",
        icao="VILK",
        latitude=26.7606,
        longitude=80.8893,
        unit=TemperatureUnit.CELSIUS,
        wunderground_url="in/lucknow/VILK",
    ),
    "Seattle": CityConfig(
        name="Seattle",
        icao="KSEA",
        latitude=47.4502,
        longitude=-122.3088,
        unit=TemperatureUnit.FAHRENHEIT,
        wunderground_url="us/wa/seattle/KSEA",
    ),
}


# Reverse lookup: ICAO code → city name
ICAO_TO_CITY: dict[str, str] = {cfg.icao: name for name, cfg in CITY_STATIONS.items()}


# ── Ensemble Model Configs ─────────────────────────────────────────────────


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for a single NWP ensemble model."""

    name: str
    members: int
    source: str  # API/data source identifier


GFS = ModelConfig(name="gfs", members=31, source="open-meteo")
ECMWF_IFS = ModelConfig(name="ecmwf_ifs", members=51, source="open-meteo")
ECMWF_AIFS = ModelConfig(name="ecmwf_aifs", members=51, source="open-meteo")
ICON = ModelConfig(name="icon", members=40, source="open-meteo")

ENSEMBLE_MODELS: list[ModelConfig] = [GFS, ECMWF_IFS, ECMWF_AIFS, ICON]

TOTAL_ENSEMBLE_MEMBERS: int = sum(m.members for m in ENSEMBLE_MODELS)  # 173


# ── Edge Thresholds by Forecast Horizon ────────────────────────────────────
# Minimum edge required to place a bet, increasing with uncertainty at longer
# horizons. Anything beyond 72 hours is skipped entirely.

EDGE_THRESHOLDS: dict[str, float] = {
    "0-24h": 0.05,   # Was 0.08 — too conservative, missing profitable trades
    "25-48h": 0.08,   # Was 0.12 — 8% edge at 1-2 day horizon is solid
    "49-72h": 0.12,   # Was 0.15 — 12% for longer horizon
}

MAX_HORIZON_HOURS: int = 72  # Skip markets beyond this horizon


def min_edge_for_horizon(horizon_hours: float) -> float:
    """Return the minimum edge threshold for a given forecast horizon."""
    if horizon_hours <= 24:
        return EDGE_THRESHOLDS["0-24h"]
    elif horizon_hours <= 48:
        return EDGE_THRESHOLDS["25-48h"]
    elif horizon_hours <= 72:
        return EDGE_THRESHOLDS["49-72h"]
    else:
        return float("inf")  # Never bet beyond 72h


# ── Kelly Criterion Configuration ──────────────────────────────────────────

KELLY_FRACTIONAL: float = 0.25  # Use quarter-Kelly for safety
KELLY_MAX_FRACTION: float = 0.25  # Max fraction of bankroll per bet
KELLY_MAX_PER_CITY: float = 0.15  # Max exposure to any single city
KELLY_MAX_PER_DAY: float = 0.30  # Max total deployment in a single day


# ── Bankroll Allocation ────────────────────────────────────────────────────

MIN_BANKROLL: float = 100.0  # Don't trade below this
MAX_BET_SIZE: float = 2_500.0  # Hard cap on any single position
MIN_BET_SIZE: float = 5.0  # Minimum bet worth placing


# ── Gamma API ─────────────────────────────────────────────────────────────────

GAMMA_BASE: str = "https://gamma-api.polymarket.com"
GAMMA_TIMEOUT: int = 30
GAMMA_PAGE_LIMIT: int = 100


# ── Open-Meteo Ensemble API ──────────────────────────────────────────────────

ENSEMBLE_API: str = "https://ensemble-api.open-meteo.com/v1/ensemble"
ENSEMBLE_TIMEOUT: int = 60
ENSEMBLE_FORECAST_DAYS: int = 7


# ── Forecast Cache ────────────────────────────────────────────────────────────

FORECAST_CACHE_TTL_SECONDS: int = 30 * 60  # 30 minutes


# ── Weather Underground ───────────────────────────────────────────────────────

WUNDERGROUND_BASE: str = "https://www.wunderground.com"
WUNDERGROUND_TIMEOUT: int = 30


# ── NWS API (US stations) ────────────────────────────────────────────────────

NWS_API_BASE: str = "https://api.weather.gov"
NWS_TIMEOUT: int = 20
