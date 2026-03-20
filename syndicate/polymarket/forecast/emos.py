"""EMOS (Ensemble Model Output Statistics) calibration.

Fits a calibrated Gaussian predictive distribution:
    mean = a + b * ensemble_mean  (bias correction)
    variance = c + d * ensemble_variance  (spread correction)

Parameters (a, b, c, d) are optimized by minimizing CRPS on a rolling
training window of forecast-vs-actual pairs.

Reference: Gneiting et al. (2005), "Calibrated Probabilistic Forecasting
Using Ensemble Model Output Statistics and Minimum CRPS Estimation"
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import structlog
from pydantic import BaseModel
from scipy.optimize import minimize
from scipy.stats import norm

log = structlog.get_logger(__name__)

# Rolling training window size (days)
TRAINING_WINDOW = 90

# Minimum training samples before fitting
MIN_TRAINING_SAMPLES = 10


class EMOSParams(BaseModel):
    """Fitted EMOS parameters for one city."""

    a: float = 0.0   # intercept for mean
    b: float = 1.0   # slope for mean (1.0 = no correction)
    c: float = 1.0   # intercept for variance
    d: float = 0.5   # slope for variance


def crps_gaussian(mu: float, sigma: float, observation: float) -> float:
    """Closed-form CRPS for a Gaussian predictive distribution.

    CRPS(N(mu, sigma^2), y) = sigma * (z * (2*Phi(z) - 1) + 2*phi(z) - 1/sqrt(pi))

    where z = (y - mu) / sigma, phi = standard normal PDF, Phi = standard normal CDF.

    Lower is better. Returns non-negative value.
    """
    if sigma <= 0:
        # Degenerate case: point forecast — CRPS = |mu - observation|
        return abs(mu - observation)

    z = (observation - mu) / sigma
    phi_z = norm.pdf(z)
    big_phi_z = norm.cdf(z)

    return sigma * (z * (2.0 * big_phi_z - 1.0) + 2.0 * phi_z - 1.0 / math.sqrt(math.pi))


class EMOSCalibrator:
    """EMOS calibrator that fits and applies Gaussian post-processing.

    Stores per-city parameters and training data. Parameters are optimized
    by minimizing mean CRPS over a rolling training window.
    """

    def __init__(self) -> None:
        self._params: dict[str, EMOSParams] = {}
        self._training_data: dict[str, list[tuple[float, float, float]]] = {}

    def get_params(self, city: str) -> EMOSParams:
        """Return current EMOS parameters for a city, or defaults."""
        return self._params.get(city, EMOSParams())

    def calibrate(
        self, city: str, ensemble_mean: float, ensemble_std: float
    ) -> tuple[float, float]:
        """Apply EMOS calibration to raw ensemble statistics.

        Args:
            city: City name for city-specific parameters.
            ensemble_mean: Raw ensemble mean temperature.
            ensemble_std: Raw ensemble standard deviation.

        Returns:
            (calibrated_mean, calibrated_std) — the parameters of the
            calibrated Gaussian predictive distribution.
        """
        p = self.get_params(city)

        calibrated_mean = p.a + p.b * ensemble_mean
        calibrated_var = p.c + p.d * (ensemble_std ** 2)

        # Enforce minimum variance to avoid degenerate distributions
        calibrated_var = max(calibrated_var, 0.01)
        calibrated_std = math.sqrt(calibrated_var)

        return calibrated_mean, calibrated_std

    def add_training_point(
        self, city: str, ensemble_mean: float, ensemble_std: float, actual: float
    ) -> None:
        """Add a forecast-vs-actual observation to the training set.

        Args:
            city: City name.
            ensemble_mean: Raw ensemble mean for this forecast.
            ensemble_std: Raw ensemble standard deviation.
            actual: Observed (actual) daily high temperature.
        """
        if city not in self._training_data:
            self._training_data[city] = []

        self._training_data[city].append((ensemble_mean, ensemble_std, actual))

        # Trim to rolling window
        if len(self._training_data[city]) > TRAINING_WINDOW:
            self._training_data[city] = self._training_data[city][-TRAINING_WINDOW:]

    def fit(self, training_data: list[tuple[float, float, float]]) -> EMOSParams:
        """Fit EMOS parameters on provided training data.

        Args:
            training_data: List of (ensemble_mean, ensemble_std, actual_value) tuples.

        Returns:
            Fitted EMOSParams.
        """
        if len(training_data) < MIN_TRAINING_SAMPLES:
            log.info(
                "emos.fit.insufficient_data",
                n_samples=len(training_data),
                min_required=MIN_TRAINING_SAMPLES,
            )
            return EMOSParams()

        def objective(params: list[float]) -> float:
            a, b, c, d = params
            total_crps = 0.0
            for ens_mean, ens_std, actual in training_data:
                mu = a + b * ens_mean
                var = c + d * (ens_std ** 2)
                var = max(var, 0.01)
                sigma = math.sqrt(var)
                total_crps += crps_gaussian(mu, sigma, actual)
            return total_crps / len(training_data)

        result = minimize(
            objective,
            x0=[0.0, 1.0, 1.0, 0.5],
            method="Nelder-Mead",
            options={"maxiter": 5000, "xatol": 1e-6, "fatol": 1e-8},
        )

        a, b, c, d = result.x
        # Enforce c > 0 (variance intercept must be non-negative)
        c = max(c, 0.0)
        d = max(d, 0.0)

        fitted = EMOSParams(a=float(a), b=float(b), c=float(c), d=float(d))

        log.info(
            "emos.fit.done",
            n_samples=len(training_data),
            mean_crps=round(result.fun, 4),
            params={"a": round(a, 4), "b": round(b, 4), "c": round(c, 4), "d": round(d, 4)},
        )

        return fitted

    def fit_city(self, city: str) -> None:
        """Fit EMOS parameters for a specific city using its training data."""
        data = self._training_data.get(city, [])
        self._params[city] = self.fit(data)

    def fit_all(self) -> None:
        """Fit EMOS parameters for all cities with training data."""
        for city in list(self._training_data.keys()):
            self.fit_city(city)

    def save(self, path: str | Path) -> None:
        """Save EMOS parameters and training data to JSON."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "params": {
                city: params.model_dump() for city, params in self._params.items()
            },
            "training_data": {
                city: [list(t) for t in points]
                for city, points in self._training_data.items()
            },
        }

        path.write_text(json.dumps(data, indent=2))
        log.info("emos.save", path=str(path), n_cities=len(self._params))

    def load(self, path: str | Path) -> None:
        """Load EMOS parameters and training data from JSON."""
        path = Path(path)
        if not path.exists():
            log.info("emos.load.not_found", path=str(path))
            return

        raw = json.loads(path.read_text())

        self._params = {
            city: EMOSParams(**params) for city, params in raw.get("params", {}).items()
        }
        self._training_data = {
            city: [(t[0], t[1], t[2]) for t in points]
            for city, points in raw.get("training_data", {}).items()
        }

        log.info(
            "emos.load",
            path=str(path),
            n_cities=len(self._params),
            n_training_cities=len(self._training_data),
        )
