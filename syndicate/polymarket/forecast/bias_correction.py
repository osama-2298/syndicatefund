"""Station-specific additive bias correction from rolling observation window."""

from __future__ import annotations

import json
from pathlib import Path

import structlog

log = structlog.get_logger(__name__)

# Default persistence path
DEFAULT_BIAS_PATH = "data/polymarket/bias_history.json"

# Rolling window size (number of observations)
DEFAULT_WINDOW_SIZE = 90

# Minimum observations before applying bias correction
MIN_OBSERVATIONS = 10


class BiasTracker:
    """Track and correct station-specific forecast bias.

    Maintains a rolling window of (forecast_mean, actual) pairs per city.
    Bias is computed as mean(actual - forecast) — a positive bias means the
    forecast consistently under-predicts, so the correction adds to the forecast.
    """

    def __init__(self, window_size: int = DEFAULT_WINDOW_SIZE) -> None:
        self._window_size = window_size
        # city -> list of (forecast_mean, actual) pairs
        self._history: dict[str, list[tuple[float, float]]] = {}

    def update(self, city: str, forecast_mean: float, actual: float) -> None:
        """Add a forecast-vs-actual observation for a city.

        Args:
            city: City name.
            forecast_mean: The forecast mean temperature.
            actual: The observed actual temperature.
        """
        if city not in self._history:
            self._history[city] = []

        self._history[city].append((forecast_mean, actual))

        # Trim to rolling window
        if len(self._history[city]) > self._window_size:
            self._history[city] = self._history[city][-self._window_size:]

    def get_bias(self, city: str) -> float:
        """Return mean additive bias for a city.

        Bias = mean(actual - forecast) over the rolling window.
        Returns 0.0 if fewer than MIN_OBSERVATIONS are available.

        Args:
            city: City name.

        Returns:
            The mean bias (positive means forecast under-predicts).
        """
        history = self._history.get(city, [])

        if len(history) < MIN_OBSERVATIONS:
            return 0.0

        errors = [actual - forecast for forecast, actual in history]
        return sum(errors) / len(errors)

    def correct(self, city: str, forecast_mean: float) -> float:
        """Apply bias correction to a forecast mean.

        Args:
            city: City name.
            forecast_mean: Raw forecast mean temperature.

        Returns:
            Bias-corrected forecast mean.
        """
        bias = self.get_bias(city)
        corrected = forecast_mean + bias

        if bias != 0.0:
            log.debug(
                "bias_correction.applied",
                city=city,
                raw=round(forecast_mean, 2),
                bias=round(bias, 2),
                corrected=round(corrected, 2),
                n_obs=len(self._history.get(city, [])),
            )

        return corrected

    def get_stats(self, city: str) -> dict:
        """Return diagnostic statistics for a city's bias history.

        Args:
            city: City name.

        Returns:
            Dict with bias, n_observations, and recent error trend.
        """
        history = self._history.get(city, [])
        n = len(history)

        if n == 0:
            return {"bias": 0.0, "n_observations": 0, "mae": 0.0}

        errors = [actual - forecast for forecast, actual in history]
        bias = sum(errors) / n
        mae = sum(abs(e) for e in errors) / n

        return {
            "bias": round(bias, 3),
            "n_observations": n,
            "mae": round(mae, 3),
        }

    def save(self, path: str | Path | None = None) -> None:
        """Save bias history to JSON.

        Args:
            path: File path. Defaults to data/polymarket/bias_history.json.
        """
        path = Path(path or DEFAULT_BIAS_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            city: [list(pair) for pair in pairs]
            for city, pairs in self._history.items()
        }

        path.write_text(json.dumps(data, indent=2))
        log.info("bias_tracker.save", path=str(path), n_cities=len(self._history))

    def load(self, path: str | Path | None = None) -> None:
        """Load bias history from JSON.

        Args:
            path: File path. Defaults to data/polymarket/bias_history.json.
        """
        path = Path(path or DEFAULT_BIAS_PATH)

        if not path.exists():
            log.info("bias_tracker.load.not_found", path=str(path))
            return

        raw = json.loads(path.read_text())

        self._history = {
            city: [(pair[0], pair[1]) for pair in pairs]
            for city, pairs in raw.items()
        }

        log.info(
            "bias_tracker.load",
            path=str(path),
            n_cities=len(self._history),
            total_obs=sum(len(v) for v in self._history.values()),
        )
