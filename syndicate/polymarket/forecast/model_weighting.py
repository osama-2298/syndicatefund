"""BMA-lite: weight NWP models by recent CRPS performance."""

from __future__ import annotations

import json
from pathlib import Path

import structlog

from syndicate.polymarket.forecast.emos import crps_gaussian

log = structlog.get_logger(__name__)

# Default persistence path
DEFAULT_WEIGHTS_PATH = "data/polymarket/model_weights.json"

# Minimum observations per model before using performance-based weights
MIN_OBSERVATIONS_PER_MODEL = 20

# Minimum weight floor per model (prevents any model from being zeroed out)
WEIGHT_FLOOR = 0.05

# Rolling window for CRPS history
CRPS_WINDOW = 90


class ModelWeightTracker:
    """Track per-model CRPS performance and compute Bayesian-style weights.

    Models with lower recent CRPS (better calibration) receive higher weight.
    Until sufficient observations accumulate, equal weights are returned.

    Weight formula: w_i = (1 / crps_i) / sum(1 / crps_j), floored at 0.05.
    """

    def __init__(self) -> None:
        # model_name -> list of CRPS values (most recent last)
        self._crps_history: dict[str, list[float]] = {}

    def update(
        self, model: str, forecast_mean: float, forecast_std: float, actual: float
    ) -> None:
        """Record a CRPS observation for a model.

        Args:
            model: Model name (e.g., "gfs", "ecmwf_ifs").
            forecast_mean: Model's forecast mean temperature.
            forecast_std: Model's forecast standard deviation.
            actual: Observed actual temperature.
        """
        crps = crps_gaussian(forecast_mean, forecast_std, actual)

        if model not in self._crps_history:
            self._crps_history[model] = []

        self._crps_history[model].append(crps)

        # Trim to rolling window
        if len(self._crps_history[model]) > CRPS_WINDOW:
            self._crps_history[model] = self._crps_history[model][-CRPS_WINDOW:]

    def get_weights(self) -> dict[str, float]:
        """Compute normalized model weights inversely proportional to mean CRPS.

        Returns equal weights if any model has fewer than MIN_OBSERVATIONS_PER_MODEL
        observations. Otherwise, computes w_i = (1/crps_i) / sum(1/crps_j) with
        a floor of WEIGHT_FLOOR per model.

        Returns:
            Dict mapping model name to weight (sums to 1.0).
        """
        models = list(self._crps_history.keys())

        if not models:
            return {}

        # Check if all models have sufficient data
        for model in models:
            if len(self._crps_history[model]) < MIN_OBSERVATIONS_PER_MODEL:
                # Return equal weights
                n = len(models)
                equal_weight = 1.0 / n
                log.debug(
                    "model_weights.equal",
                    reason="insufficient_data",
                    model=model,
                    n_obs=len(self._crps_history[model]),
                    min_required=MIN_OBSERVATIONS_PER_MODEL,
                )
                return {m: equal_weight for m in models}

        # Compute mean CRPS per model
        mean_crps: dict[str, float] = {}
        for model in models:
            history = self._crps_history[model]
            mean_crps[model] = sum(history) / len(history)

        # Inverse CRPS weighting with floor
        inverse_crps: dict[str, float] = {}
        for model, mc in mean_crps.items():
            # Guard against zero or negative CRPS (shouldn't happen, but be safe)
            if mc <= 0:
                mc = 1e-6
            inverse_crps[model] = 1.0 / mc

        total_inverse = sum(inverse_crps.values())

        # Normalize
        raw_weights = {model: ic / total_inverse for model, ic in inverse_crps.items()}

        # Apply floor and re-normalize
        floored_weights: dict[str, float] = {}
        for model, w in raw_weights.items():
            floored_weights[model] = max(w, WEIGHT_FLOOR)

        total_floored = sum(floored_weights.values())
        normalized = {model: w / total_floored for model, w in floored_weights.items()}

        log.info(
            "model_weights.computed",
            weights={m: round(w, 4) for m, w in normalized.items()},
            mean_crps={m: round(c, 3) for m, c in mean_crps.items()},
        )

        return normalized

    def get_stats(self) -> dict[str, dict]:
        """Return diagnostic statistics per model.

        Returns:
            Dict mapping model name to stats dict with n_obs, mean_crps, weight.
        """
        weights = self.get_weights()
        stats: dict[str, dict] = {}

        for model, history in self._crps_history.items():
            mean_crps = sum(history) / len(history) if history else 0.0
            stats[model] = {
                "n_observations": len(history),
                "mean_crps": round(mean_crps, 4),
                "weight": round(weights.get(model, 0.0), 4),
            }

        return stats

    def save(self, path: str | Path | None = None) -> None:
        """Save CRPS history to JSON.

        Args:
            path: File path. Defaults to data/polymarket/model_weights.json.
        """
        path = Path(path or DEFAULT_WEIGHTS_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            model: [round(c, 6) for c in history]
            for model, history in self._crps_history.items()
        }

        path.write_text(json.dumps(data, indent=2))
        log.info("model_weights.save", path=str(path), n_models=len(self._crps_history))

    def load(self, path: str | Path | None = None) -> None:
        """Load CRPS history from JSON.

        Args:
            path: File path. Defaults to data/polymarket/model_weights.json.
        """
        path = Path(path or DEFAULT_WEIGHTS_PATH)

        if not path.exists():
            log.info("model_weights.load.not_found", path=str(path))
            return

        raw = json.loads(path.read_text())

        self._crps_history = {
            model: list(history) for model, history in raw.items()
        }

        log.info(
            "model_weights.load",
            path=str(path),
            n_models=len(self._crps_history),
            total_obs=sum(len(v) for v in self._crps_history.values()),
        )
