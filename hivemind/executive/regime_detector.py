"""
HMM-based Regime Detector for crypto markets.

Uses a Hidden Markov Model to classify the current market regime into one of:
  BULL, BEAR, RANGING
with a special CRISIS override when BEAR + Fear & Greed < 15.

Features:
  - Daily BTC return
  - 20-day rolling volatility

If ``hmmlearn`` is installed, a proper Gaussian HMM is used.
Otherwise, a simple rolling-statistics fallback provides comparable output.
"""

from __future__ import annotations

import math
from typing import Any

import structlog

from hivemind.data.models import MarketRegime

logger = structlog.get_logger()

# Try to import hmmlearn; fall back gracefully
try:
    from hmmlearn.hmm import GaussianHMM  # type: ignore[import-untyped]
    import numpy as np

    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _daily_returns(prices: list[float]) -> list[float]:
    """Compute simple daily returns from a price series."""
    returns = []
    for i in range(1, len(prices)):
        if prices[i - 1] != 0:
            returns.append((prices[i] - prices[i - 1]) / prices[i - 1])
        else:
            returns.append(0.0)
    return returns


def _rolling_volatility(returns: list[float], window: int = 20) -> list[float]:
    """Compute rolling standard deviation of returns."""
    vols: list[float] = []
    for i in range(len(returns)):
        start = max(0, i - window + 1)
        window_returns = returns[start : i + 1]
        if len(window_returns) < 2:
            vols.append(0.0)
            continue
        mean = sum(window_returns) / len(window_returns)
        var = sum((r - mean) ** 2 for r in window_returns) / (len(window_returns) - 1)
        vols.append(math.sqrt(var))
    return vols


def _build_features(prices: list[float]) -> list[list[float]]:
    """Build feature matrix [daily_return, rolling_vol] from daily prices."""
    returns = _daily_returns(prices)
    vols = _rolling_volatility(returns, window=20)
    features = []
    for ret, vol in zip(returns, vols):
        features.append([ret, vol])
    return features


# ─────────────────────────────────────────────
#  State mapping
# ─────────────────────────────────────────────

_STATE_REGIMES = [MarketRegime.BEAR, MarketRegime.RANGING, MarketRegime.BULL]


def _map_state_to_regime(state_index: int) -> MarketRegime:
    """Map an HMM state index to a MarketRegime.

    States are ordered by their mean return:
      0 → lowest mean return → BEAR
      1 → middle → RANGING
      2 → highest → BULL
    """
    if 0 <= state_index < len(_STATE_REGIMES):
        return _STATE_REGIMES[state_index]
    return MarketRegime.RANGING


# ─────────────────────────────────────────────
#  HMM Regime Detector
# ─────────────────────────────────────────────


class HMMRegimeDetector:
    """Hidden Markov Model regime detection for crypto markets.

    3 states: BULL, BEAR, RANGING
    CRISIS = BEAR + F&G < 15
    Features: daily return, 20-day rolling vol
    """

    CRISIS_FG_THRESHOLD = 15

    def __init__(self, n_states: int = 3, random_seed: int = 42) -> None:
        self.n_states = n_states
        self._random_seed = random_seed
        self._fitted = False
        self._hmm_model: Any = None
        # State-to-regime mapping (reordered after fitting by mean return)
        self._state_order: list[int] = list(range(n_states))

    # ─────────────────────────────────────────
    #  Fit
    # ─────────────────────────────────────────

    def fit(self, btc_daily_prices: list[float]) -> None:
        """Fit the HMM on historical BTC daily prices.

        Requires at least 30 daily prices to produce meaningful results.
        """
        if len(btc_daily_prices) < 30:
            logger.warning(
                "regime_detector_insufficient_data",
                n_prices=len(btc_daily_prices),
            )
            return

        features = _build_features(btc_daily_prices)
        if not features:
            return

        if HMM_AVAILABLE:
            self._fit_hmm(features)
        else:
            # Fallback: no fitting needed — predict uses rolling stats
            self._fitted = True
            logger.info("regime_detector_fitted", method="rolling_stats_fallback")

    def _fit_hmm(self, features: list[list[float]]) -> None:
        """Fit a Gaussian HMM using hmmlearn."""
        X = np.array(features)  # noqa: N806
        model = GaussianHMM(
            n_components=self.n_states,
            covariance_type="full",
            n_iter=200,
            random_state=self._random_seed,
        )
        model.fit(X)
        self._hmm_model = model

        # Reorder states by mean daily return (column 0) so that:
        #   index 0 → lowest mean → BEAR
        #   index 1 → middle → RANGING
        #   index 2 → highest mean → BULL
        means = model.means_[:, 0]  # daily return means per state
        self._state_order = list(np.argsort(means))
        self._fitted = True
        logger.info(
            "regime_detector_fitted",
            method="hmm",
            state_means=[float(means[i]) for i in self._state_order],
        )

    # ─────────────────────────────────────────
    #  Predict
    # ─────────────────────────────────────────

    def predict(
        self,
        recent_prices: list[float],
        fear_greed_value: float | None = None,
    ) -> dict[str, Any]:
        """Predict the current market regime.

        Args:
            recent_prices: Recent daily BTC prices (at least 25 recommended).
            fear_greed_value: Fear & Greed index (0-100). If < 15 and regime
                is BEAR, overrides to CRISIS.

        Returns:
            dict with keys:
                regime: MarketRegime
                confidence: float (0-1)
                transition_probabilities: dict[str, float]
                method: str ("hmm" or "rolling_stats")
        """
        if len(recent_prices) < 5:
            return {
                "regime": MarketRegime.RANGING,
                "confidence": 0.0,
                "transition_probabilities": {},
                "method": "insufficient_data",
            }

        if HMM_AVAILABLE and self._hmm_model is not None:
            result = self._predict_hmm(recent_prices)
        else:
            result = self._predict_fallback(recent_prices)

        # CRISIS override: BEAR + extreme fear
        regime = result["regime"]
        if (
            regime == MarketRegime.BEAR
            and fear_greed_value is not None
            and fear_greed_value < self.CRISIS_FG_THRESHOLD
        ):
            result["regime"] = MarketRegime.CRISIS
            logger.info(
                "regime_crisis_override",
                fear_greed=fear_greed_value,
                original_regime=regime.value,
            )

        return result

    def _predict_hmm(self, recent_prices: list[float]) -> dict[str, Any]:
        """Predict using the fitted Gaussian HMM."""
        features = _build_features(recent_prices)
        if not features:
            return {
                "regime": MarketRegime.RANGING,
                "confidence": 0.0,
                "transition_probabilities": {},
                "method": "hmm_no_features",
            }

        X = np.array(features)  # noqa: N806
        hidden_states = self._hmm_model.predict(X)
        state_probs = self._hmm_model.predict_proba(X)

        # Current state is the last predicted state
        raw_state = hidden_states[-1]
        # Map raw state to ordered state (0=BEAR, 1=RANGING, 2=BULL)
        ordered_state = self._state_order.index(raw_state)
        regime = _map_state_to_regime(ordered_state)

        # Confidence = probability of the predicted state
        confidence = float(state_probs[-1][raw_state])

        # Transition probabilities from the current state
        transmat = self._hmm_model.transmat_
        trans_probs = {}
        for target_raw, target_ordered_idx in enumerate(self._state_order):
            target_regime = _map_state_to_regime(self._state_order.index(target_raw))
            trans_probs[target_regime.value] = float(transmat[raw_state][target_raw])

        return {
            "regime": regime,
            "confidence": confidence,
            "transition_probabilities": trans_probs,
            "method": "hmm",
        }

    def _predict_fallback(self, recent_prices: list[float]) -> dict[str, Any]:
        """Fallback regime detection using rolling statistics.

        Heuristic:
          - 20-day return > +8%  → BULL
          - 20-day return < -8%  → BEAR
          - otherwise            → RANGING
        Confidence is based on how far the return is from thresholds.
        """
        returns = _daily_returns(recent_prices)
        if not returns:
            return {
                "regime": MarketRegime.RANGING,
                "confidence": 0.0,
                "transition_probabilities": {},
                "method": "rolling_stats",
            }

        # Use the last 20 days (or fewer if not available)
        lookback = min(20, len(returns))
        recent_returns = returns[-lookback:]
        cumulative_return = 1.0
        for r in recent_returns:
            cumulative_return *= (1 + r)
        cumulative_return -= 1.0  # net return

        # Rolling volatility
        vols = _rolling_volatility(returns, window=min(20, len(returns)))
        current_vol = vols[-1] if vols else 0.0

        # Classify
        bull_threshold = 0.08
        bear_threshold = -0.08

        if cumulative_return > bull_threshold:
            regime = MarketRegime.BULL
            # Confidence scales with how far above threshold
            confidence = min(1.0, 0.5 + (cumulative_return - bull_threshold) * 3)
        elif cumulative_return < bear_threshold:
            regime = MarketRegime.BEAR
            confidence = min(1.0, 0.5 + (bear_threshold - cumulative_return) * 3)
        else:
            regime = MarketRegime.RANGING
            # Higher confidence when close to 0 return
            confidence = max(0.3, 1.0 - abs(cumulative_return) * 8)

        # Estimate naive transition probabilities based on momentum and vol
        # Higher vol → more likely to transition away from current state
        vol_factor = min(current_vol * 10, 0.4)  # cap at 40% transition prob
        stay_prob = max(0.4, 1.0 - vol_factor)
        leave_prob = (1.0 - stay_prob) / 2

        trans_probs = {}
        for r in [MarketRegime.BULL, MarketRegime.BEAR, MarketRegime.RANGING]:
            if r == regime:
                trans_probs[r.value] = round(stay_prob, 3)
            else:
                trans_probs[r.value] = round(leave_prob, 3)

        return {
            "regime": regime,
            "confidence": round(confidence, 3),
            "transition_probabilities": trans_probs,
            "method": "rolling_stats",
        }
