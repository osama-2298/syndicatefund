"""
Advanced HMM-based Regime Detector for the Risk Module.

Extends the basic executive regime detector with:
  - 4-feature HMM (returns, rolling vol, volume ratio, funding rates)
  - Kalman filter for smooth regime probability estimation
  - Regime transition probability matrix with duration statistics
  - Regime change alerts (probability of shift > 70%)
  - Historical regime timeline generation
  - Graceful fallback to rolling statistics when hmmlearn unavailable

3 HMM states: BULL, BEAR, RANGING  (with CRISIS override when BEAR + extreme fear).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog
from pydantic import BaseModel, Field

from syndicate.data.models import MarketRegime

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
#  Optional imports
# ---------------------------------------------------------------------------

try:
    import numpy as np
    from numpy.typing import NDArray

    NUMPY_AVAILABLE = True
except ImportError:  # pragma: no cover
    NUMPY_AVAILABLE = False

try:
    from hmmlearn.hmm import GaussianHMM  # type: ignore[import-untyped]

    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False

try:
    from scipy.linalg import inv as scipy_inv  # noqa: F401

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


# ---------------------------------------------------------------------------
#  Pydantic output models
# ---------------------------------------------------------------------------


class RegimeProbabilities(BaseModel):
    """Smoothed probability distribution across regimes."""

    bull: float = 0.0
    bear: float = 0.0
    ranging: float = 0.0

    @property
    def dominant(self) -> MarketRegime:
        mapping = {
            "bull": MarketRegime.BULL,
            "bear": MarketRegime.BEAR,
            "ranging": MarketRegime.RANGING,
        }
        best = max(mapping, key=lambda k: getattr(self, k))
        return mapping[best]

    @property
    def dominant_probability(self) -> float:
        return max(self.bull, self.bear, self.ranging)


class RegimeDurationStats(BaseModel):
    """Average and current duration (in days) for each regime."""

    bull_avg_days: float = 0.0
    bear_avg_days: float = 0.0
    ranging_avg_days: float = 0.0
    current_regime_days: int = 0


class RegimeTransitionMatrix(BaseModel):
    """Row = from-regime, col = to-regime.  3x3 stored as nested dict."""

    matrix: dict[str, dict[str, float]] = Field(default_factory=dict)

    def prob(self, from_regime: str, to_regime: str) -> float:
        return self.matrix.get(from_regime, {}).get(to_regime, 0.0)


class RegimeAlert(BaseModel):
    """Alert raised when regime shift probability exceeds threshold."""

    from_regime: MarketRegime
    to_regime: MarketRegime
    probability: float
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RegimeTimelineEntry(BaseModel):
    """Single entry in a historical regime timeline."""

    date: datetime
    regime: MarketRegime
    confidence: float
    probabilities: RegimeProbabilities


class RegimeDetectionResult(BaseModel):
    """Full output of a regime detection cycle."""

    regime: MarketRegime
    confidence: float
    probabilities: RegimeProbabilities
    transition_matrix: RegimeTransitionMatrix
    duration_stats: RegimeDurationStats
    alerts: list[RegimeAlert] = Field(default_factory=list)
    method: str = "hmm"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
#  Pure-Python helpers (no numpy required)
# ---------------------------------------------------------------------------

def _daily_returns(prices: list[float]) -> list[float]:
    out: list[float] = []
    for i in range(1, len(prices)):
        out.append((prices[i] - prices[i - 1]) / prices[i - 1] if prices[i - 1] != 0 else 0.0)
    return out


def _rolling_std(values: list[float], window: int = 20) -> list[float]:
    vols: list[float] = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        w = values[start: i + 1]
        if len(w) < 2:
            vols.append(0.0)
            continue
        m = sum(w) / len(w)
        var = sum((x - m) ** 2 for x in w) / (len(w) - 1)
        vols.append(math.sqrt(var))
    return vols


def _volume_ratios(volumes: list[float], window: int = 20) -> list[float]:
    """Volume / 20-day SMA of volume."""
    ratios: list[float] = []
    for i in range(len(volumes)):
        start = max(0, i - window + 1)
        w = volumes[start: i + 1]
        avg = sum(w) / len(w) if w else 1.0
        ratios.append(volumes[i] / avg if avg > 0 else 1.0)
    return ratios


# ---------------------------------------------------------------------------
#  Kalman filter for regime probability smoothing
# ---------------------------------------------------------------------------

class _KalmanSmoother:
    """Simple 1-D Kalman filter per regime dimension.

    Smooths noisy HMM posterior probabilities so that the reported
    regime distribution does not flip-flop on noisy days.

    State:  x_t  (smoothed probability)
    Observation: z_t  (raw HMM posterior)

    Parameters:
        process_noise (Q):     how fast the true regime can change  (default 0.01)
        measurement_noise (R): how noisy the HMM posterior is       (default 0.05)
    """

    def __init__(self, n_dim: int = 3, q: float = 0.01, r: float = 0.05) -> None:
        self.n = n_dim
        self.q = q
        self.r = r
        # State estimate and covariance per dimension
        self.x = [1.0 / n_dim] * n_dim
        self.p = [1.0] * n_dim

    def update(self, observation: list[float]) -> list[float]:
        """Run one predict-update cycle and return smoothed probabilities."""
        smoothed: list[float] = []
        for i in range(self.n):
            # Predict
            x_pred = self.x[i]
            p_pred = self.p[i] + self.q

            # Update
            k = p_pred / (p_pred + self.r)  # Kalman gain
            self.x[i] = x_pred + k * (observation[i] - x_pred)
            self.p[i] = (1 - k) * p_pred

            smoothed.append(max(0.0, self.x[i]))

        # Normalise so probabilities sum to 1
        total = sum(smoothed)
        if total > 0:
            smoothed = [s / total for s in smoothed]
        return smoothed


# ---------------------------------------------------------------------------
#  Regime duration tracker
# ---------------------------------------------------------------------------

@dataclass
class _DurationTracker:
    """Track how long each regime lasts to compute average durations."""

    current_regime: MarketRegime = MarketRegime.RANGING
    current_run: int = 0
    runs: dict[str, list[int]] = field(default_factory=lambda: {
        MarketRegime.BULL.value: [],
        MarketRegime.BEAR.value: [],
        MarketRegime.RANGING.value: [],
    })

    def step(self, regime: MarketRegime) -> None:
        if regime == self.current_regime:
            self.current_run += 1
        else:
            # Close out the previous run
            if self.current_run > 0:
                key = self.current_regime.value
                if key in self.runs:
                    self.runs[key].append(self.current_run)
            self.current_regime = regime
            self.current_run = 1

    def stats(self) -> RegimeDurationStats:
        def _avg(lst: list[int]) -> float:
            return sum(lst) / len(lst) if lst else 0.0

        return RegimeDurationStats(
            bull_avg_days=round(_avg(self.runs.get(MarketRegime.BULL.value, [])), 1),
            bear_avg_days=round(_avg(self.runs.get(MarketRegime.BEAR.value, [])), 1),
            ranging_avg_days=round(_avg(self.runs.get(MarketRegime.RANGING.value, [])), 1),
            current_regime_days=self.current_run,
        )


# ---------------------------------------------------------------------------
#  State ordering helper
# ---------------------------------------------------------------------------

_ORDERED_REGIMES = [MarketRegime.BEAR, MarketRegime.RANGING, MarketRegime.BULL]


def _ordered_regime(index: int) -> MarketRegime:
    if 0 <= index < len(_ORDERED_REGIMES):
        return _ORDERED_REGIMES[index]
    return MarketRegime.RANGING


# ---------------------------------------------------------------------------
#  Advanced Regime Detector
# ---------------------------------------------------------------------------


class AdvancedRegimeDetector:
    """HMM-based regime detector with Kalman smoothing, duration stats, and alerts.

    Features used (when available):
      0. Daily return
      1. 20-day rolling volatility
      2. Volume ratio (current / 20-day avg)
      3. Funding rate

    Falls back to rolling-statistics heuristics when hmmlearn is not installed.
    """

    CRISIS_FG_THRESHOLD = 15
    ALERT_SHIFT_THRESHOLD = 0.70  # alert when P(shift) > 70%

    def __init__(
        self,
        n_states: int = 3,
        random_seed: int = 42,
        kalman_q: float = 0.01,
        kalman_r: float = 0.05,
    ) -> None:
        self.n_states = n_states
        self._seed = random_seed
        self._fitted = False
        self._hmm_model: Any = None
        self._state_order: list[int] = list(range(n_states))
        self._kalman = _KalmanSmoother(n_dim=n_states, q=kalman_q, r=kalman_r)
        self._duration = _DurationTracker()
        self._last_probabilities: RegimeProbabilities = RegimeProbabilities()

    # ------------------------------------------------------------------
    #  Feature engineering
    # ------------------------------------------------------------------

    @staticmethod
    def build_features(
        prices: list[float],
        volumes: list[float] | None = None,
        funding_rates: list[float] | None = None,
    ) -> list[list[float]]:
        """Build the feature matrix from daily data.

        Returns one row per day (aligned to returns, so len = len(prices) - 1).
        """
        returns = _daily_returns(prices)
        n = len(returns)
        if n == 0:
            return []

        vols = _rolling_std(returns, window=20)

        # Volume ratio
        if volumes and len(volumes) >= len(prices):
            vol_ratios = _volume_ratios(volumes[1:], window=20)  # align with returns
        else:
            vol_ratios = [1.0] * n

        # Funding rates
        if funding_rates and len(funding_rates) >= len(prices):
            fr = funding_rates[1:]  # align
        else:
            fr = [0.0] * n

        features: list[list[float]] = []
        for i in range(n):
            features.append([
                returns[i],
                vols[i],
                vol_ratios[i] if i < len(vol_ratios) else 1.0,
                fr[i] if i < len(fr) else 0.0,
            ])
        return features

    # ------------------------------------------------------------------
    #  Fit
    # ------------------------------------------------------------------

    def fit(
        self,
        prices: list[float],
        volumes: list[float] | None = None,
        funding_rates: list[float] | None = None,
    ) -> None:
        """Fit the HMM on historical data.  Requires >= 30 daily prices."""
        if len(prices) < 30:
            logger.warning("regime_detector_insufficient_data", n_prices=len(prices))
            return

        features = self.build_features(prices, volumes, funding_rates)
        if not features:
            return

        if HMM_AVAILABLE and NUMPY_AVAILABLE:
            self._fit_hmm(features)
        else:
            self._fitted = True
            logger.info("regime_detector_fitted", method="rolling_stats_fallback")

    def _fit_hmm(self, features: list[list[float]]) -> None:
        X = np.array(features)  # noqa: N806
        model = GaussianHMM(
            n_components=self.n_states,
            covariance_type="full",
            n_iter=200,
            random_state=self._seed,
        )
        model.fit(X)
        self._hmm_model = model

        # Order states by mean daily return (col 0): BEAR < RANGING < BULL
        means = model.means_[:, 0]
        self._state_order = list(np.argsort(means))
        self._fitted = True
        logger.info(
            "regime_detector_fitted",
            method="hmm",
            n_features=X.shape[1],
            state_means=[float(means[i]) for i in self._state_order],
        )

    # ------------------------------------------------------------------
    #  Predict
    # ------------------------------------------------------------------

    def detect(
        self,
        recent_prices: list[float],
        volumes: list[float] | None = None,
        funding_rates: list[float] | None = None,
        fear_greed_value: float | None = None,
    ) -> RegimeDetectionResult:
        """Run full regime detection and return a comprehensive result."""
        if len(recent_prices) < 5:
            return RegimeDetectionResult(
                regime=MarketRegime.RANGING,
                confidence=0.0,
                probabilities=RegimeProbabilities(),
                transition_matrix=RegimeTransitionMatrix(),
                duration_stats=self._duration.stats(),
                method="insufficient_data",
            )

        if HMM_AVAILABLE and NUMPY_AVAILABLE and self._hmm_model is not None:
            result = self._detect_hmm(recent_prices, volumes, funding_rates)
        else:
            result = self._detect_fallback(recent_prices, volumes)

        # CRISIS override
        if (
            result.regime == MarketRegime.BEAR
            and fear_greed_value is not None
            and fear_greed_value < self.CRISIS_FG_THRESHOLD
        ):
            result.regime = MarketRegime.CRISIS
            logger.info(
                "regime_crisis_override",
                fear_greed=fear_greed_value,
            )

        # Update duration tracker
        base_regime = result.regime if result.regime != MarketRegime.CRISIS else MarketRegime.BEAR
        self._duration.step(base_regime)
        result.duration_stats = self._duration.stats()

        # Generate alerts
        result.alerts = self._check_alerts(result)

        self._last_probabilities = result.probabilities

        logger.info(
            "regime_detection",
            regime=result.regime.value,
            confidence=round(result.confidence, 3),
            method=result.method,
            current_days=result.duration_stats.current_regime_days,
            alerts=len(result.alerts),
        )
        return result

    def _detect_hmm(
        self,
        prices: list[float],
        volumes: list[float] | None,
        funding_rates: list[float] | None,
    ) -> RegimeDetectionResult:
        features = self.build_features(prices, volumes, funding_rates)
        if not features:
            return RegimeDetectionResult(
                regime=MarketRegime.RANGING,
                confidence=0.0,
                probabilities=RegimeProbabilities(),
                transition_matrix=RegimeTransitionMatrix(),
                duration_stats=self._duration.stats(),
                method="hmm_no_features",
            )

        X = np.array(features)  # noqa: N806
        hidden_states = self._hmm_model.predict(X)
        state_probs = self._hmm_model.predict_proba(X)

        raw_state = hidden_states[-1]
        ordered_idx = self._state_order.index(raw_state)
        regime = _ordered_regime(ordered_idx)

        # Raw probabilities reordered: [bear, ranging, bull]
        raw_probs_last = state_probs[-1]
        ordered_probs = [float(raw_probs_last[self._state_order[i]]) for i in range(self.n_states)]

        # Kalman smooth
        smoothed = self._kalman.update(ordered_probs)

        probs = RegimeProbabilities(
            bear=round(smoothed[0], 4),
            ranging=round(smoothed[1], 4),
            bull=round(smoothed[2], 4),
        )
        confidence = float(max(smoothed))

        # Transition matrix
        trans = self._build_transition_matrix()

        return RegimeDetectionResult(
            regime=regime,
            confidence=round(confidence, 4),
            probabilities=probs,
            transition_matrix=trans,
            duration_stats=self._duration.stats(),
            method="hmm",
        )

    def _detect_fallback(
        self,
        prices: list[float],
        volumes: list[float] | None,
    ) -> RegimeDetectionResult:
        """Rolling-statistics fallback when hmmlearn is not available."""
        returns = _daily_returns(prices)
        if not returns:
            return RegimeDetectionResult(
                regime=MarketRegime.RANGING,
                confidence=0.0,
                probabilities=RegimeProbabilities(),
                transition_matrix=RegimeTransitionMatrix(),
                duration_stats=self._duration.stats(),
                method="rolling_stats",
            )

        lookback = min(20, len(returns))
        recent = returns[-lookback:]
        cum_ret = 1.0
        for r in recent:
            cum_ret *= (1 + r)
        cum_ret -= 1.0

        vols = _rolling_std(returns, window=min(20, len(returns)))
        current_vol = vols[-1] if vols else 0.0

        # Volume boost: high volume during a move increases confidence
        vol_boost = 0.0
        if volumes and len(volumes) > 20:
            vr = _volume_ratios(volumes, window=20)
            if vr:
                vol_boost = max(0.0, (vr[-1] - 1.0) * 0.1)  # up to ~0.1 extra confidence

        bull_threshold = 0.08
        bear_threshold = -0.08

        if cum_ret > bull_threshold:
            regime = MarketRegime.BULL
            base_conf = min(1.0, 0.5 + (cum_ret - bull_threshold) * 3)
            bear_p = max(0.0, 0.1 - cum_ret * 0.5)
            ranging_p = max(0.0, 0.3 - cum_ret)
            bull_p = 1.0 - bear_p - ranging_p
        elif cum_ret < bear_threshold:
            regime = MarketRegime.BEAR
            base_conf = min(1.0, 0.5 + (bear_threshold - cum_ret) * 3)
            bull_p = max(0.0, 0.1 + cum_ret * 0.5)
            ranging_p = max(0.0, 0.3 + cum_ret)
            bear_p = 1.0 - bull_p - ranging_p
        else:
            regime = MarketRegime.RANGING
            base_conf = max(0.3, 1.0 - abs(cum_ret) * 8)
            ranging_p = base_conf
            remainder = 1.0 - ranging_p
            bull_p = remainder * (0.5 + cum_ret * 3) if cum_ret > 0 else remainder * 0.3
            bear_p = max(0.0, 1.0 - ranging_p - bull_p)

        confidence = min(1.0, base_conf + vol_boost)

        # Normalise
        total = bull_p + bear_p + ranging_p
        if total > 0:
            bull_p /= total
            bear_p /= total
            ranging_p /= total

        # Kalman smooth
        smoothed = self._kalman.update([bear_p, ranging_p, bull_p])
        probs = RegimeProbabilities(
            bear=round(smoothed[0], 4),
            ranging=round(smoothed[1], 4),
            bull=round(smoothed[2], 4),
        )

        # Heuristic transition matrix from vol
        vol_factor = min(current_vol * 10, 0.4)
        stay = max(0.4, 1.0 - vol_factor)
        leave = (1.0 - stay) / 2.0
        matrix: dict[str, dict[str, float]] = {}
        for r in [MarketRegime.BULL, MarketRegime.BEAR, MarketRegime.RANGING]:
            row: dict[str, float] = {}
            for t in [MarketRegime.BULL, MarketRegime.BEAR, MarketRegime.RANGING]:
                row[t.value] = round(stay, 4) if r == t else round(leave, 4)
            matrix[r.value] = row

        return RegimeDetectionResult(
            regime=regime,
            confidence=round(confidence, 4),
            probabilities=probs,
            transition_matrix=RegimeTransitionMatrix(matrix=matrix),
            duration_stats=self._duration.stats(),
            method="rolling_stats",
        )

    # ------------------------------------------------------------------
    #  Transition matrix
    # ------------------------------------------------------------------

    def _build_transition_matrix(self) -> RegimeTransitionMatrix:
        if not (HMM_AVAILABLE and self._hmm_model is not None):
            return RegimeTransitionMatrix()

        transmat = self._hmm_model.transmat_
        regime_names = [MarketRegime.BEAR.value, MarketRegime.RANGING.value, MarketRegime.BULL.value]

        matrix: dict[str, dict[str, float]] = {}
        for i, from_name in enumerate(regime_names):
            row: dict[str, float] = {}
            raw_from = self._state_order[i]
            for j, to_name in enumerate(regime_names):
                raw_to = self._state_order[j]
                row[to_name] = round(float(transmat[raw_from][raw_to]), 4)
            matrix[from_name] = row

        return RegimeTransitionMatrix(matrix=matrix)

    # ------------------------------------------------------------------
    #  Alerts
    # ------------------------------------------------------------------

    def _check_alerts(self, result: RegimeDetectionResult) -> list[RegimeAlert]:
        alerts: list[RegimeAlert] = []
        probs = result.probabilities
        current = result.regime if result.regime != MarketRegime.CRISIS else MarketRegime.BEAR

        # Check if any non-current regime has probability > threshold
        regime_prob_map = {
            MarketRegime.BULL: probs.bull,
            MarketRegime.BEAR: probs.bear,
            MarketRegime.RANGING: probs.ranging,
        }

        for target_regime, prob in regime_prob_map.items():
            if target_regime == current:
                continue
            if prob >= self.ALERT_SHIFT_THRESHOLD:
                alerts.append(RegimeAlert(
                    from_regime=current,
                    to_regime=target_regime,
                    probability=round(prob, 4),
                    message=(
                        f"Regime shift alert: {current.value} -> {target_regime.value} "
                        f"probability {prob:.1%} exceeds {self.ALERT_SHIFT_THRESHOLD:.0%} threshold"
                    ),
                ))
                logger.warning(
                    "regime_shift_alert",
                    from_regime=current.value,
                    to_regime=target_regime.value,
                    probability=round(prob, 4),
                )

        return alerts

    # ------------------------------------------------------------------
    #  Historical timeline
    # ------------------------------------------------------------------

    def generate_timeline(
        self,
        prices: list[float],
        dates: list[datetime],
        volumes: list[float] | None = None,
        funding_rates: list[float] | None = None,
    ) -> list[RegimeTimelineEntry]:
        """Generate a day-by-day regime classification over a historical period.

        Requires a fitted model.  Returns one entry per day (aligned with
        returns, so len = len(prices) - 1).
        """
        if len(prices) < 5 or len(dates) < len(prices):
            return []

        features = self.build_features(prices, volumes, funding_rates)
        if not features:
            return []

        timeline: list[RegimeTimelineEntry] = []

        if HMM_AVAILABLE and NUMPY_AVAILABLE and self._hmm_model is not None:
            X = np.array(features)  # noqa: N806
            hidden_states = self._hmm_model.predict(X)
            state_probs = self._hmm_model.predict_proba(X)

            smoother = _KalmanSmoother(n_dim=self.n_states)
            for i in range(len(features)):
                raw_state = hidden_states[i]
                ordered_idx = self._state_order.index(raw_state)
                regime = _ordered_regime(ordered_idx)

                raw_p = state_probs[i]
                ordered_p = [float(raw_p[self._state_order[k]]) for k in range(self.n_states)]
                sm = smoother.update(ordered_p)

                probs = RegimeProbabilities(
                    bear=round(sm[0], 4),
                    ranging=round(sm[1], 4),
                    bull=round(sm[2], 4),
                )
                timeline.append(RegimeTimelineEntry(
                    date=dates[i + 1],  # +1 because returns lose first element
                    regime=regime,
                    confidence=round(max(sm), 4),
                    probabilities=probs,
                ))
        else:
            # Fallback: rolling window classification
            returns = _daily_returns(prices)
            smoother = _KalmanSmoother(n_dim=self.n_states)
            for i in range(len(returns)):
                lookback = min(20, i + 1)
                window = returns[max(0, i - lookback + 1): i + 1]
                cum = 1.0
                for r in window:
                    cum *= (1 + r)
                cum -= 1.0

                if cum > 0.08:
                    regime = MarketRegime.BULL
                    raw_p = [0.05, 0.15, 0.80]
                elif cum < -0.08:
                    regime = MarketRegime.BEAR
                    raw_p = [0.80, 0.15, 0.05]
                else:
                    regime = MarketRegime.RANGING
                    raw_p = [0.15, 0.70, 0.15]

                sm = smoother.update(raw_p)
                probs = RegimeProbabilities(
                    bear=round(sm[0], 4),
                    ranging=round(sm[1], 4),
                    bull=round(sm[2], 4),
                )
                timeline.append(RegimeTimelineEntry(
                    date=dates[i + 1],
                    regime=regime,
                    confidence=round(max(sm), 4),
                    probabilities=probs,
                ))

        return timeline

    # ------------------------------------------------------------------
    #  Convenience: backward-compatible dict output
    # ------------------------------------------------------------------

    def predict(
        self,
        recent_prices: list[float],
        fear_greed_value: float | None = None,
        volumes: list[float] | None = None,
        funding_rates: list[float] | None = None,
    ) -> dict[str, Any]:
        """Backward-compatible predict interface returning a plain dict."""
        result = self.detect(
            recent_prices=recent_prices,
            volumes=volumes,
            funding_rates=funding_rates,
            fear_greed_value=fear_greed_value,
        )
        return {
            "regime": result.regime,
            "confidence": result.confidence,
            "probabilities": {
                "bull": result.probabilities.bull,
                "bear": result.probabilities.bear,
                "ranging": result.probabilities.ranging,
            },
            "transition_matrix": result.transition_matrix.matrix,
            "duration_stats": result.duration_stats.model_dump(),
            "alerts": [a.model_dump() for a in result.alerts],
            "method": result.method,
        }
