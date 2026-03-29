"""Signal decay analysis — measuring the half-life and optimal holding period of signals.

Quantifies how quickly a trading signal loses predictive power over time,
which directly determines position sizing and holding period:

- Half-life of signal predictive power
- Forward-looking decay curve (t+1h to t+7d)
- Optimal holding period by signal type
- Confidence reweighting as time progresses
- Autocorrelation function of signals
"""

from __future__ import annotations

import math

import numpy as np
from pydantic import BaseModel, Field
from scipy import optimize as sp_optimize
from scipy import stats as sp_stats


# ---------------------------------------------------------------------------
# Pydantic output models
# ---------------------------------------------------------------------------

class DecayPoint(BaseModel):
    """Single point on the decay curve."""

    horizon: str = Field(description="Human-readable horizon label (e.g., '1h', '1d')")
    horizon_hours: float = Field(description="Horizon in hours")
    ic: float = Field(description="Information coefficient at this horizon")
    ic_std: float = Field(description="Std dev of IC (from rolling windows)")
    t_stat: float = Field(description="t-stat for H0: IC=0 at this horizon")
    p_value: float
    n_observations: int


class HalfLifeResult(BaseModel):
    """Half-life of signal predictive power."""

    half_life_hours: float = Field(
        description="Time for IC to decay to half its initial value",
    )
    decay_rate: float = Field(description="Exponential decay rate lambda")
    initial_ic: float = Field(description="Fitted IC at t=0")
    r_squared: float = Field(description="Goodness of fit for exponential decay model")
    decay_curve: list[DecayPoint] = Field(description="IC at each measured horizon")


class OptimalHoldingPeriod(BaseModel):
    """Optimal holding period for a signal type."""

    signal_type: str
    optimal_hours: float = Field(
        description="Holding period that maximises risk-adjusted IC",
    )
    optimal_ic: float = Field(description="IC at optimal horizon")
    sharpe_per_hour: float = Field(
        description="IC / sqrt(horizon) — risk-adjusted decay metric",
    )
    holding_periods_tested: list[float] = Field(description="Horizons tested (hours)")
    risk_adjusted_ic: list[float] = Field(
        description="IC / sqrt(hours) at each horizon",
    )


class ConfidenceWeight(BaseModel):
    """Confidence weight as a function of time since signal."""

    hours_since_signal: float
    weight: float = Field(description="Recommended position weight [0,1]")
    remaining_ic_pct: float = Field(
        description="Percentage of initial IC remaining",
    )


class ConfidenceReweightingResult(BaseModel):
    """Position sizing weights that decay with signal age."""

    weights: list[ConfidenceWeight]
    half_life_hours: float
    decay_model: str = Field(description="Decay model used: 'exponential' or 'linear'")


class SignalAutocorrelationResult(BaseModel):
    """Autocorrelation structure of the signal itself."""

    lags_hours: list[float]
    autocorrelations: list[float]
    first_zero_crossing_hours: float | None = Field(
        description="First lag where autocorrelation crosses zero (regime change)",
    )
    persistence_score: float = Field(
        description="Mean absolute autocorrelation over first 5 lags (0-1)",
    )


class SignalDecayReport(BaseModel):
    """Complete signal decay analysis."""

    half_life: HalfLifeResult
    optimal_holding: OptimalHoldingPeriod
    confidence_reweighting: ConfidenceReweightingResult
    signal_autocorrelation: SignalAutocorrelationResult


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def compute_decay_curve(
    signals: np.ndarray | list[float],
    forward_returns: dict[str, np.ndarray | list[float]],
    horizons_hours: list[float] | None = None,
    window_size: int = 50,
) -> list[DecayPoint]:
    """Compute the Information Coefficient at multiple forward horizons.

    For each horizon h, measures rank(signal_t, return_{t,t+h}) to see
    how predictive the signal is at different look-ahead periods.

    Args:
        signals: Signal values at each time step.
        forward_returns: Dict mapping horizon label -> return array.
            Each array should have returns realised h periods ahead.
            E.g., ``{"1h": returns_1h, "4h": returns_4h, "1d": returns_1d}``.
        horizons_hours: Hours corresponding to each key in forward_returns.
            If None, inferred from keys (e.g., "1h" -> 1.0).
        window_size: Rolling window for IC estimation.

    Returns:
        List of DecayPoint, one per horizon.
    """
    sig = np.asarray(signals, dtype=np.float64)
    horizon_labels = list(forward_returns.keys())

    if horizons_hours is None:
        horizons_hours = [_parse_horizon_hours(label) for label in horizon_labels]

    decay_points: list[DecayPoint] = []

    for label, hours in zip(horizon_labels, horizons_hours):
        fwd = np.asarray(forward_returns[label], dtype=np.float64)
        n = min(len(sig), len(fwd))

        if n < 20:
            decay_points.append(DecayPoint(
                horizon=label, horizon_hours=hours,
                ic=0.0, ic_std=0.0, t_stat=0.0, p_value=1.0, n_observations=n,
            ))
            continue

        sig_t = sig[:n]
        fwd_t = fwd[:n]

        # Rolling IC
        ic_values: list[float] = []
        for start in range(0, n - window_size + 1, max(1, window_size // 2)):
            end = start + window_size
            s_win = sig_t[start:end]
            r_win = fwd_t[start:end]
            if np.std(s_win) > 0 and np.std(r_win) > 0:
                rho, _ = sp_stats.spearmanr(s_win, r_win)
                ic_values.append(float(rho))

        if not ic_values:
            decay_points.append(DecayPoint(
                horizon=label, horizon_hours=hours,
                ic=0.0, ic_std=0.0, t_stat=0.0, p_value=1.0, n_observations=n,
            ))
            continue

        ic_arr = np.array(ic_values)
        mean_ic = float(np.mean(ic_arr))
        std_ic = float(np.std(ic_arr, ddof=1)) if len(ic_arr) > 1 else 0.0
        n_ic = len(ic_arr)
        t_stat = mean_ic / (std_ic / math.sqrt(n_ic)) if std_ic > 0 else 0.0
        p_value = float(2.0 * sp_stats.t.sf(abs(t_stat), df=max(n_ic - 1, 1)))

        decay_points.append(DecayPoint(
            horizon=label,
            horizon_hours=hours,
            ic=round(mean_ic, 6),
            ic_std=round(std_ic, 6),
            t_stat=round(t_stat, 4),
            p_value=round(p_value, 6),
            n_observations=n,
        ))

    return decay_points


def estimate_half_life(
    decay_curve: list[DecayPoint],
) -> HalfLifeResult:
    """Fit an exponential decay model to the IC decay curve and estimate half-life.

    Model: IC(t) = IC_0 * exp(-lambda * t)
    Half-life: t_{1/2} = ln(2) / lambda

    Args:
        decay_curve: Output from compute_decay_curve.

    Returns:
        HalfLifeResult with half-life and fitted parameters.
    """
    if len(decay_curve) < 2:
        return HalfLifeResult(
            half_life_hours=float("inf"),
            decay_rate=0.0,
            initial_ic=0.0,
            r_squared=0.0,
            decay_curve=decay_curve,
        )

    hours = np.array([dp.horizon_hours for dp in decay_curve], dtype=np.float64)
    ics = np.array([dp.ic for dp in decay_curve], dtype=np.float64)

    # Use absolute IC for decay fitting (sign may flip at long horizons)
    abs_ics = np.abs(ics)

    if np.max(abs_ics) == 0:
        return HalfLifeResult(
            half_life_hours=float("inf"),
            decay_rate=0.0,
            initial_ic=0.0,
            r_squared=0.0,
            decay_curve=decay_curve,
        )

    # Fit IC(t) = a * exp(-lambda * t) using nonlinear least squares
    def _decay_model(t: np.ndarray, a: float, lam: float) -> np.ndarray:
        return a * np.exp(-lam * t)

    try:
        popt, _ = sp_optimize.curve_fit(
            _decay_model, hours, abs_ics,
            p0=[float(abs_ics[0]), 0.01],
            bounds=([0.0, 1e-8], [10.0, 10.0]),
            maxfev=5000,
        )
        ic_0 = float(popt[0])
        lam = float(popt[1])
    except (RuntimeError, ValueError):
        # Fallback: log-linear fit
        positive_mask = abs_ics > 1e-8
        if np.sum(positive_mask) < 2:
            return HalfLifeResult(
                half_life_hours=float("inf"),
                decay_rate=0.0,
                initial_ic=float(abs_ics[0]),
                r_squared=0.0,
                decay_curve=decay_curve,
            )
        log_ics = np.log(abs_ics[positive_mask])
        h_pos = hours[positive_mask]
        slope, intercept, _, _, _ = sp_stats.linregress(h_pos, log_ics)
        ic_0 = math.exp(intercept)
        lam = max(-slope, 1e-8)

    half_life = math.log(2.0) / lam if lam > 0 else float("inf")

    # R-squared
    fitted = ic_0 * np.exp(-lam * hours)
    ss_res = float(np.sum((abs_ics - fitted) ** 2))
    ss_tot = float(np.sum((abs_ics - np.mean(abs_ics)) ** 2))
    r_sq = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return HalfLifeResult(
        half_life_hours=round(half_life, 2),
        decay_rate=round(lam, 8),
        initial_ic=round(ic_0, 6),
        r_squared=round(max(r_sq, 0.0), 6),
        decay_curve=decay_curve,
    )


def optimal_holding_period(
    decay_curve: list[DecayPoint],
    signal_type: str = "default",
) -> OptimalHoldingPeriod:
    """Determine the optimal holding period by maximising risk-adjusted IC.

    The risk-adjusted IC metric is IC(h) / sqrt(h), which accounts for the
    fact that longer horizons carry more risk (wider return dispersion).
    The optimal holding period maximises this ratio.

    Args:
        decay_curve: Output from compute_decay_curve.
        signal_type: Label for the signal type.

    Returns:
        OptimalHoldingPeriod with optimal horizon and diagnostics.
    """
    if not decay_curve:
        return OptimalHoldingPeriod(
            signal_type=signal_type,
            optimal_hours=0.0,
            optimal_ic=0.0,
            sharpe_per_hour=0.0,
            holding_periods_tested=[],
            risk_adjusted_ic=[],
        )

    hours = [dp.horizon_hours for dp in decay_curve]
    ics = [dp.ic for dp in decay_curve]

    # Risk-adjusted IC: IC / sqrt(h)
    risk_adj: list[float] = []
    for h, ic in zip(hours, ics):
        if h > 0:
            risk_adj.append(ic / math.sqrt(h))
        else:
            risk_adj.append(ic)

    # Find the maximum
    best_idx = int(np.argmax(risk_adj))

    return OptimalHoldingPeriod(
        signal_type=signal_type,
        optimal_hours=hours[best_idx],
        optimal_ic=round(ics[best_idx], 6),
        sharpe_per_hour=round(risk_adj[best_idx], 6),
        holding_periods_tested=hours,
        risk_adjusted_ic=[round(x, 6) for x in risk_adj],
    )


def confidence_reweighting(
    half_life_hours: float,
    max_hours: float = 168.0,
    n_steps: int = 50,
    decay_model: str = "exponential",
    min_weight: float = 0.05,
) -> ConfidenceReweightingResult:
    """Generate position weight schedule that decays with signal age.

    As a signal ages, its predictive power diminishes. This function
    produces a weight curve for dynamically sizing positions based on
    how long ago the signal was generated.

    Args:
        half_life_hours: Signal half-life (from estimate_half_life).
        max_hours: Maximum time horizon to compute weights for.
        n_steps: Number of time steps to output.
        decay_model: ``"exponential"`` or ``"linear"``.
        min_weight: Minimum weight floor (never go below this).

    Returns:
        ConfidenceReweightingResult with weight schedule.
    """
    if half_life_hours <= 0 or half_life_hours == float("inf"):
        half_life_hours = max_hours  # No decay: constant weights

    time_steps = np.linspace(0, max_hours, n_steps)
    weights: list[ConfidenceWeight] = []

    if decay_model == "exponential":
        lam = math.log(2.0) / half_life_hours
        for t in time_steps:
            remaining_pct = math.exp(-lam * t) * 100.0
            w = max(math.exp(-lam * t), min_weight)
            weights.append(ConfidenceWeight(
                hours_since_signal=round(float(t), 2),
                weight=round(w, 6),
                remaining_ic_pct=round(remaining_pct, 2),
            ))
    else:  # linear
        for t in time_steps:
            remaining_pct = max(1.0 - t / (2.0 * half_life_hours), 0.0) * 100.0
            w = max(remaining_pct / 100.0, min_weight)
            weights.append(ConfidenceWeight(
                hours_since_signal=round(float(t), 2),
                weight=round(w, 6),
                remaining_ic_pct=round(remaining_pct, 2),
            ))

    return ConfidenceReweightingResult(
        weights=weights,
        half_life_hours=round(half_life_hours, 2),
        decay_model=decay_model,
    )


def signal_autocorrelation(
    signals: np.ndarray | list[float],
    max_lag: int = 20,
    hours_per_step: float = 1.0,
) -> SignalAutocorrelationResult:
    """Compute the autocorrelation function of the signal itself.

    High signal autocorrelation means:
    - Signals are persistent (positions don't need frequent rebalancing)
    - Turnover can be reduced by waiting for regime changes
    - New signals carry less incremental information vs the previous signal

    Args:
        signals: Signal time series.
        max_lag: Maximum number of lags to compute.
        hours_per_step: Time between consecutive signal observations.

    Returns:
        SignalAutocorrelationResult with ACF and persistence metrics.
    """
    sig = np.asarray(signals, dtype=np.float64)
    n = len(sig)

    if n < max_lag + 5:
        return SignalAutocorrelationResult(
            lags_hours=[],
            autocorrelations=[],
            first_zero_crossing_hours=None,
            persistence_score=0.0,
        )

    # Compute sample autocorrelations
    mean_s = np.mean(sig)
    demeaned = sig - mean_s
    var = float(np.sum(demeaned**2))

    if var == 0:
        return SignalAutocorrelationResult(
            lags_hours=[float(k * hours_per_step) for k in range(1, max_lag + 1)],
            autocorrelations=[0.0] * max_lag,
            first_zero_crossing_hours=None,
            persistence_score=0.0,
        )

    lags_hours: list[float] = []
    acf_values: list[float] = []
    first_zero_crossing: float | None = None

    for k in range(1, max_lag + 1):
        rho = float(np.sum(demeaned[:n - k] * demeaned[k:])) / var
        lag_h = k * hours_per_step
        lags_hours.append(round(lag_h, 2))
        acf_values.append(round(rho, 6))

        # Detect first zero crossing
        if first_zero_crossing is None and len(acf_values) >= 2:
            if acf_values[-2] > 0 and acf_values[-1] <= 0:
                # Linear interpolation for crossing point
                prev_rho = acf_values[-2]
                curr_rho = acf_values[-1]
                frac = prev_rho / (prev_rho - curr_rho) if prev_rho != curr_rho else 0.5
                first_zero_crossing = round(
                    (k - 1 + frac) * hours_per_step, 2
                )

    # Persistence: mean |ACF| over first 5 lags
    n_persist = min(5, len(acf_values))
    persistence = float(np.mean(np.abs(acf_values[:n_persist])))

    return SignalAutocorrelationResult(
        lags_hours=lags_hours,
        autocorrelations=acf_values,
        first_zero_crossing_hours=first_zero_crossing,
        persistence_score=round(persistence, 6),
    )


def run_signal_decay_report(
    signals: np.ndarray | list[float],
    forward_returns: dict[str, np.ndarray | list[float]],
    horizons_hours: list[float] | None = None,
    signal_type: str = "default",
    hours_per_step: float = 1.0,
) -> SignalDecayReport:
    """Run a complete signal decay analysis.

    Args:
        signals: Signal values at each time step.
        forward_returns: Dict of horizon_label -> forward return arrays.
        horizons_hours: Hours for each horizon (auto-parsed from labels if None).
        signal_type: Label for the signal type.
        hours_per_step: Time between consecutive signal observations.

    Returns:
        SignalDecayReport with all analyses.
    """
    # Decay curve
    decay = compute_decay_curve(signals, forward_returns, horizons_hours)

    # Half-life
    hl = estimate_half_life(decay)

    # Optimal holding
    opt = optimal_holding_period(decay, signal_type=signal_type)

    # Confidence reweighting
    cw = confidence_reweighting(hl.half_life_hours)

    # Signal autocorrelation
    sa = signal_autocorrelation(signals, hours_per_step=hours_per_step)

    return SignalDecayReport(
        half_life=hl,
        optimal_holding=opt,
        confidence_reweighting=cw,
        signal_autocorrelation=sa,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_horizon_hours(label: str) -> float:
    """Parse a horizon label like '1h', '4h', '1d', '7d' into hours."""
    label = label.strip().lower()
    if label.endswith("h"):
        return float(label[:-1])
    if label.endswith("d"):
        return float(label[:-1]) * 24.0
    if label.endswith("m"):
        return float(label[:-1]) / 60.0
    # Fallback: assume hours
    try:
        return float(label)
    except ValueError:
        return 1.0
