"""Polymarket Weather Oracle — Data Layer.

Three data sources:
  - Gamma API: discover active weather markets on Polymarket
  - Open-Meteo: fetch 173-member ensemble temperature forecasts
  - Weather Underground / NWS: fetch actual observed temperatures for resolution
"""

from syndicate.polymarket.data.gamma_client import discover_weather_markets
from syndicate.polymarket.data.open_meteo import fetch_ensemble_forecast
from syndicate.polymarket.data.wunderground import (
    fetch_actual_high,
    fetch_actual_high_nws,
    fetch_actual_high_wunderground,
)

__all__ = [
    "discover_weather_markets",
    "fetch_ensemble_forecast",
    "fetch_actual_high",
    "fetch_actual_high_nws",
    "fetch_actual_high_wunderground",
]
