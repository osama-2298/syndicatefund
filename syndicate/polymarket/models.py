"""
Pydantic v2 models for the Polymarket Weather Oracle.

Every piece of data flowing through the weather oracle pipeline is typed here:
market definitions, ensemble forecasts, bin probabilities, positions, and portfolio state.
"""

from __future__ import annotations

import statistics
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


# ── Enums ──────────────────────────────────────────────────────────────────


class TemperatureUnit(str, Enum):
    FAHRENHEIT = "fahrenheit"
    CELSIUS = "celsius"


# ── City / Station Config ──────────────────────────────────────────────────


class CityConfig(BaseModel):
    name: str
    icao: str
    latitude: float
    longitude: float
    unit: TemperatureUnit
    wunderground_url: str  # e.g., "us/ny/new-york-city/KLGA"


# ── Market Bins ────────────────────────────────────────────────────────────


class TemperatureBin(BaseModel):
    index: int
    label: str  # "40-41F" or "15C"
    lower: float  # inclusive
    upper: float  # exclusive (inf for last bin)
    token_id: str = ""
    market_price: float = 0.0  # current YES price


# ── Weather Market ─────────────────────────────────────────────────────────


class WeatherMarket(BaseModel):
    condition_id: str  # Polymarket condition ID
    event_slug: str
    city: str
    date: str  # YYYY-MM-DD
    unit: TemperatureUnit
    bins: list[TemperatureBin]
    total_volume: float = 0.0
    last_updated: datetime


# ── Ensemble Forecast ──────────────────────────────────────────────────────


class EnsembleMember(BaseModel):
    model: str  # "gfs", "ecmwf_ifs", "ecmwf_aifs", "icon"
    member_index: int
    daily_high: float  # in the market's unit


class EnsembleForecast(BaseModel):
    city: str
    target_date: str
    fetched_at: datetime
    members: list[EnsembleMember]

    @property
    def all_highs(self) -> list[float]:
        return [m.daily_high for m in self.members]

    @property
    def mean(self) -> float:
        highs = self.all_highs
        return sum(highs) / len(highs) if highs else 0.0

    @property
    def std(self) -> float:
        highs = self.all_highs
        return statistics.stdev(highs) if len(highs) > 1 else 0.0


# ── Analysis ───────────────────────────────────────────────────────────────


class BinProbability(BaseModel):
    bin_index: int
    label: str
    model_prob: float
    market_price: float
    edge: float  # model_prob - market_price


class MarketAnalysis(BaseModel):
    condition_id: str
    city: str
    date: str
    horizon_hours: float
    forecast_mean: float
    forecast_std: float
    bin_probabilities: list[BinProbability]
    best_edge: float
    best_edge_bin: int
    analyzed_at: datetime


# ── Positions & Portfolio ──────────────────────────────────────────────────


class WeatherPosition(BaseModel):
    condition_id: str
    token_id: str
    city: str
    date: str
    bin_label: str
    side: str = "YES"  # always YES for weather
    entry_price: float
    quantity: float  # USDC amount
    model_prob: float
    edge_at_entry: float
    placed_at: datetime
    resolved: bool = False
    outcome: bool | None = None  # True if won
    pnl: float = 0.0


class WeatherPortfolio(BaseModel):
    bankroll: float = 10_000.0
    cash: float = 10_000.0
    positions: list[WeatherPosition] = []
    total_pnl: float = 0.0
    total_bets: int = 0
    wins: int = 0
    losses: int = 0

    @property
    def win_rate(self) -> float:
        resolved = self.wins + self.losses
        return self.wins / resolved if resolved > 0 else 0.0

    @property
    def total_value(self) -> float:
        open_value = sum(p.quantity for p in self.positions if not p.resolved)
        return self.cash + open_value


# ── Calibration ────────────────────────────────────────────────────────────


class CalibrationRecord(BaseModel):
    """A single forecast-vs-actual observation for calibration tracking."""
    city: str
    date: str
    horizon_hours: float
    forecast_mean: float
    forecast_std: float
    bin_probs: list[float]  # model probability for each bin
    actual_high: float
    winning_bin: int  # index of bin that won
    recorded_at: datetime


class CalibrationSummary(BaseModel):
    """Calibration quality metrics."""
    brier_score: float = 0.0
    brier_by_city: dict[str, float] = {}
    brier_by_horizon: dict[str, float] = {}
    mae: float = 0.0
    total_records: int = 0
    calibration_ready: bool = False


# ── Oracle Status ──────────────────────────────────────────────────────────


class OracleStatus(BaseModel):
    running: bool = False
    last_scan: datetime | None = None
    markets_tracked: int = 0
    open_positions: int = 0
    portfolio_value: float = 0.0
    total_pnl: float = 0.0
    uptime_seconds: float = 0.0
    calibration_ready: bool = False
    scan_interval: int = 300
    fresh_data_window: bool = False
