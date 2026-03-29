"""Overfitting detection for backtest results.

Quantifies the probability that a backtest's performance is due to
overfitting rather than genuine predictive skill:

- Combinatorial Purged Cross-Validation (CPCV)
- Probability of Backtest Overfitting (PBO)
- Walk-forward efficiency ratio (OOS/IS Sharpe)
- Parameter sensitivity heatmap data
- Haircut Sharpe Ratio (Harvey & Liu)
"""

from __future__ import annotations

import itertools
import math
from typing import Any, Callable

import numpy as np
from pydantic import BaseModel, Field
from scipy import stats as sp_stats


# ---------------------------------------------------------------------------
# Pydantic output models
# ---------------------------------------------------------------------------

class CPCVFold(BaseModel):
    """Results from a single CPCV fold."""

    fold_index: int
    train_indices: list[int] = Field(description="Group indices used for training")
    test_indices: list[int] = Field(description="Group indices used for testing")
    is_sharpe: float = Field(description="In-sample Sharpe ratio")
    oos_sharpe: float = Field(description="Out-of-sample Sharpe ratio")
    is_return_pct: float
    oos_return_pct: float


class CPCVResult(BaseModel):
    """Combinatorial Purged Cross-Validation results."""

    n_groups: int = Field(description="Number of time-series groups")
    n_test_groups: int = Field(description="Number of groups used for testing per fold")
    n_folds: int = Field(description="Total number of combinatorial folds")
    purge_length: int = Field(description="Purge buffer between train/test in samples")
    folds: list[CPCVFold]
    mean_oos_sharpe: float
    std_oos_sharpe: float
    mean_is_sharpe: float
    degradation_ratio: float = Field(
        description="mean_oos / mean_is -- below 0.5 suggests overfitting",
    )


class PBOResult(BaseModel):
    """Probability of Backtest Overfitting."""

    pbo: float = Field(
        description="Probability that the best IS strategy underperforms OOS (0-1)",
    )
    pbo_interpretation: str = Field(
        description="Human-readable assessment of overfitting risk",
    )
    n_combinations: int
    logit_distribution: list[float] = Field(
        description="Distribution of logit(lambda) values across combinations",
    )
    mean_logit: float
    median_logit: float


class WalkForwardEfficiency(BaseModel):
    """Walk-forward efficiency: how much IS performance survives OOS."""

    efficiency_ratio: float = Field(
        description="OOS Sharpe / IS Sharpe -- 1.0 is perfect, <0.5 is concerning",
    )
    is_sharpe: float
    oos_sharpe: float
    is_return_pct: float
    oos_return_pct: float
    n_windows: int
    per_window_efficiency: list[float] = Field(
        description="Efficiency ratio for each walk-forward window",
    )
    verdict: str


class SensitivityPoint(BaseModel):
    """Single point in the parameter sensitivity analysis."""

    param_1_value: float
    param_2_value: float
    metric_value: float


class ParameterSensitivityResult(BaseModel):
    """Parameter sensitivity heatmap data."""

    param_1_name: str
    param_2_name: str
    metric_name: str
    grid: list[SensitivityPoint]
    param_1_values: list[float]
    param_2_values: list[float]
    metric_matrix: list[list[float]] = Field(
        description="2D matrix [p1_idx][p2_idx] of metric values for heatmap",
    )
    sensitivity_score: float = Field(
        description="Coefficient of variation of metric across grid (high = sensitive = bad)",
    )
    verdict: str


class HaircutSharpeResult(BaseModel):
    """Haircut Sharpe Ratio (Harvey & Liu 2015).

    Adjusts the Sharpe for three sources of inflation:
    1. Non-normality of returns (fat tails, skewness)
    2. Multiple testing (number of strategies tried)
    3. Data snooping (p-hacking, survivorship bias)
    """

    observed_sharpe: float
    haircut_sharpe: float = Field(
        description="Sharpe after all haircuts applied",
    )
    haircut_pct: float = Field(
        description="Percentage reduction from observed Sharpe",
    )
    non_normality_haircut: float = Field(
        description="Reduction due to skewness/kurtosis",
    )
    multiple_testing_haircut: float = Field(
        description="Reduction due to number of trials",
    )
    n_trials: int


class OverfittingReport(BaseModel):
    """Complete overfitting detection report."""

    cpcv: CPCVResult | None = None
    pbo: PBOResult | None = None
    walk_forward_efficiency: WalkForwardEfficiency | None = None
    parameter_sensitivity: ParameterSensitivityResult | None = None
    haircut_sharpe: HaircutSharpeResult | None = None
    overall_risk: str = Field(
        default="unknown",
        description="Overall overfitting risk: LOW, MODERATE, HIGH, CRITICAL",
    )


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def combinatorial_purged_cv(
    daily_returns: np.ndarray | list[float],
    n_groups: int = 10,
    n_test_groups: int = 2,
    purge_length: int = 5,
    ann_factor: int = 365,
    max_folds: int = 200,
) -> CPCVResult:
    """Combinatorial Purged Cross-Validation (CPCV).

    Unlike standard k-fold CV, CPCV tests all C(n_groups, n_test_groups)
    combinations of train/test splits, giving a full distribution of OOS
    performance rather than a single point estimate.

    The "purge" removes samples adjacent to the train/test boundary to
    prevent information leakage from overlapping labels.

    Args:
        daily_returns: Array of daily returns.
        n_groups: Number of contiguous time groups to split data into.
        n_test_groups: Number of groups to hold out for testing per fold.
        purge_length: Number of samples to purge at each train/test boundary.
        ann_factor: Annualisation factor.
        max_folds: Maximum folds to evaluate (caps combinatorial explosion).

    Returns:
        CPCVResult with per-fold and aggregate statistics.
    """
    r = np.asarray(daily_returns, dtype=np.float64)
    n = len(r)

    if n < n_groups * 5:
        return CPCVResult(
            n_groups=n_groups, n_test_groups=n_test_groups,
            n_folds=0, purge_length=purge_length,
            folds=[], mean_oos_sharpe=0.0, std_oos_sharpe=0.0,
            mean_is_sharpe=0.0, degradation_ratio=0.0,
        )

    # Split data into contiguous groups
    group_size = n // n_groups
    groups: list[np.ndarray] = []
    for i in range(n_groups):
        start = i * group_size
        end = start + group_size if i < n_groups - 1 else n
        groups.append(r[start:end])

    # Generate all combinations of test groups
    all_combos = list(itertools.combinations(range(n_groups), n_test_groups))
    if len(all_combos) > max_folds:
        # Subsample deterministically
        rng = np.random.default_rng(42)
        indices = rng.choice(len(all_combos), size=max_folds, replace=False)
        indices.sort()
        all_combos = [all_combos[i] for i in indices]

    folds: list[CPCVFold] = []

    for fold_idx, test_group_indices in enumerate(all_combos):
        train_group_indices = [i for i in range(n_groups) if i not in test_group_indices]

        # Build train and test arrays with purging
        train_parts: list[np.ndarray] = []
        test_parts: list[np.ndarray] = []

        test_set = set(test_group_indices)
        for gi in train_group_indices:
            g = groups[gi]
            # Purge: if adjacent to a test group, trim edges
            trim_start = purge_length if (gi - 1) in test_set else 0
            trim_end = len(g) - purge_length if (gi + 1) in test_set else len(g)
            trim_end = max(trim_end, trim_start)
            train_parts.append(g[trim_start:trim_end])

        for gi in test_group_indices:
            test_parts.append(groups[gi])

        train_r = np.concatenate(train_parts) if train_parts else np.array([])
        test_r = np.concatenate(test_parts) if test_parts else np.array([])

        is_sharpe = _compute_sharpe(train_r, ann_factor)
        oos_sharpe = _compute_sharpe(test_r, ann_factor)
        is_ret = float(np.prod(1.0 + train_r) - 1.0) * 100.0 if len(train_r) > 0 else 0.0
        oos_ret = float(np.prod(1.0 + test_r) - 1.0) * 100.0 if len(test_r) > 0 else 0.0

        folds.append(CPCVFold(
            fold_index=fold_idx,
            train_indices=list(train_group_indices),
            test_indices=list(test_group_indices),
            is_sharpe=round(is_sharpe, 6),
            oos_sharpe=round(oos_sharpe, 6),
            is_return_pct=round(is_ret, 4),
            oos_return_pct=round(oos_ret, 4),
        ))

    if not folds:
        return CPCVResult(
            n_groups=n_groups, n_test_groups=n_test_groups,
            n_folds=0, purge_length=purge_length,
            folds=[], mean_oos_sharpe=0.0, std_oos_sharpe=0.0,
            mean_is_sharpe=0.0, degradation_ratio=0.0,
        )

    oos_sharpes = np.array([f.oos_sharpe for f in folds])
    is_sharpes = np.array([f.is_sharpe for f in folds])
    mean_oos = float(np.mean(oos_sharpes))
    mean_is = float(np.mean(is_sharpes))
    degradation = mean_oos / mean_is if mean_is != 0 else 0.0

    return CPCVResult(
        n_groups=n_groups,
        n_test_groups=n_test_groups,
        n_folds=len(folds),
        purge_length=purge_length,
        folds=folds,
        mean_oos_sharpe=round(mean_oos, 6),
        std_oos_sharpe=round(float(np.std(oos_sharpes, ddof=1)), 6) if len(folds) > 1 else 0.0,
        mean_is_sharpe=round(mean_is, 6),
        degradation_ratio=round(degradation, 6),
    )


def probability_of_backtest_overfitting(
    is_sharpes_matrix: np.ndarray | list[list[float]],
    oos_sharpes_matrix: np.ndarray | list[list[float]],
) -> PBOResult:
    """Probability of Backtest Overfitting (PBO) per Bailey et al. (2017).

    Given IS and OOS Sharpe ratios for multiple strategy variants across
    multiple CV folds, PBO estimates the probability that selecting the
    best IS strategy leads to below-median OOS performance.

    Args:
        is_sharpes_matrix: Shape (n_strategies, n_folds) of IS Sharpe ratios.
        oos_sharpes_matrix: Shape (n_strategies, n_folds) of OOS Sharpe ratios.

    Returns:
        PBOResult with overfitting probability.
    """
    is_mat = np.asarray(is_sharpes_matrix, dtype=np.float64)
    oos_mat = np.asarray(oos_sharpes_matrix, dtype=np.float64)

    if is_mat.ndim != 2 or oos_mat.ndim != 2:
        return PBOResult(
            pbo=0.0, pbo_interpretation="Insufficient data",
            n_combinations=0, logit_distribution=[], mean_logit=0.0, median_logit=0.0,
        )

    n_strategies, n_folds = is_mat.shape
    if n_strategies < 2 or n_folds < 2:
        return PBOResult(
            pbo=0.0, pbo_interpretation="Insufficient data (need >= 2 strategies and folds)",
            n_combinations=0, logit_distribution=[], mean_logit=0.0, median_logit=0.0,
        )

    logit_values: list[float] = []

    for fold_idx in range(n_folds):
        is_col = is_mat[:, fold_idx]
        oos_col = oos_mat[:, fold_idx]

        # Find the best IS strategy for this fold
        best_is_idx = int(np.argmax(is_col))
        best_oos_sharpe = oos_col[best_is_idx]

        # Rank of the best IS strategy in OOS
        oos_rank = float(np.mean(oos_col <= best_oos_sharpe))

        # Logit transformation: logit(rank) = log(rank / (1 - rank))
        # Clamp rank to avoid log(0) or log(inf)
        oos_rank = max(min(oos_rank, 1.0 - 1e-6), 1e-6)
        logit_val = math.log(oos_rank / (1.0 - oos_rank))
        logit_values.append(logit_val)

    logit_arr = np.array(logit_values)

    # PBO = fraction of combinations where logit < 0
    # (i.e., best IS strategy ranks below median OOS)
    pbo = float(np.mean(logit_arr < 0))
    mean_logit = float(np.mean(logit_arr))
    median_logit = float(np.median(logit_arr))

    # Interpretation
    if pbo < 0.10:
        interpretation = "LOW RISK: Strategy selection is robust (PBO < 10%)"
    elif pbo < 0.25:
        interpretation = "MODERATE RISK: Some overfitting detected (PBO 10-25%)"
    elif pbo < 0.50:
        interpretation = "HIGH RISK: Significant overfitting likely (PBO 25-50%)"
    else:
        interpretation = "CRITICAL: Strategy is almost certainly overfit (PBO >= 50%)"

    return PBOResult(
        pbo=round(pbo, 6),
        pbo_interpretation=interpretation,
        n_combinations=n_folds,
        logit_distribution=[round(float(v), 6) for v in logit_arr],
        mean_logit=round(mean_logit, 6),
        median_logit=round(median_logit, 6),
    )


def walk_forward_efficiency(
    is_sharpes: list[float],
    oos_sharpes: list[float],
    is_returns_pct: list[float] | None = None,
    oos_returns_pct: list[float] | None = None,
) -> WalkForwardEfficiency:
    """Compute walk-forward efficiency ratio: OOS/IS performance.

    A ratio near 1.0 means IS performance translates well to OOS.
    Below 0.5 indicates significant degradation (overfitting).
    Below 0 means the strategy is destructive OOS.

    Args:
        is_sharpes: In-sample Sharpe for each walk-forward window.
        oos_sharpes: Out-of-sample Sharpe for each walk-forward window.
        is_returns_pct: Optional IS returns per window.
        oos_returns_pct: Optional OOS returns per window.

    Returns:
        WalkForwardEfficiency with efficiency ratio and diagnosis.
    """
    n_windows = min(len(is_sharpes), len(oos_sharpes))

    if n_windows == 0:
        return WalkForwardEfficiency(
            efficiency_ratio=0.0, is_sharpe=0.0, oos_sharpe=0.0,
            is_return_pct=0.0, oos_return_pct=0.0, n_windows=0,
            per_window_efficiency=[], verdict="No data",
        )

    is_arr = np.array(is_sharpes[:n_windows])
    oos_arr = np.array(oos_sharpes[:n_windows])

    mean_is = float(np.mean(is_arr))
    mean_oos = float(np.mean(oos_arr))
    ratio = mean_oos / mean_is if mean_is != 0 else 0.0

    # Per-window efficiency
    per_window: list[float] = []
    for i in range(n_windows):
        if is_arr[i] != 0:
            per_window.append(round(float(oos_arr[i] / is_arr[i]), 6))
        else:
            per_window.append(0.0)

    # Returns
    is_ret = float(np.mean(is_returns_pct[:n_windows])) if is_returns_pct else 0.0
    oos_ret = float(np.mean(oos_returns_pct[:n_windows])) if oos_returns_pct else 0.0

    # Verdict
    if ratio >= 0.8:
        verdict = "EXCELLENT: IS performance translates well to OOS (ratio >= 0.8)"
    elif ratio >= 0.5:
        verdict = "ACCEPTABLE: Moderate degradation IS -> OOS (ratio 0.5-0.8)"
    elif ratio >= 0.0:
        verdict = "POOR: Significant degradation suggests overfitting (ratio 0-0.5)"
    else:
        verdict = "DESTRUCTIVE: Strategy loses money OOS — likely overfit (ratio < 0)"

    return WalkForwardEfficiency(
        efficiency_ratio=round(ratio, 6),
        is_sharpe=round(mean_is, 6),
        oos_sharpe=round(mean_oos, 6),
        is_return_pct=round(is_ret, 4),
        oos_return_pct=round(oos_ret, 4),
        n_windows=n_windows,
        per_window_efficiency=per_window,
        verdict=verdict,
    )


def parameter_sensitivity(
    param_1_name: str,
    param_1_values: list[float],
    param_2_name: str,
    param_2_values: list[float],
    metric_fn: Callable[[float, float], float],
    metric_name: str = "sharpe_ratio",
) -> ParameterSensitivityResult:
    """Generate parameter sensitivity heatmap data.

    Evaluates a metric over a 2D grid of parameter values to visualise
    how sensitive the strategy is to parameter choices. High sensitivity
    indicates fragility and overfitting risk.

    Args:
        param_1_name: Name of the first parameter.
        param_1_values: Grid values for parameter 1.
        param_2_name: Name of the second parameter.
        param_2_values: Grid values for parameter 2.
        metric_fn: Function(p1, p2) -> metric_value.
        metric_name: Label for the evaluated metric.

    Returns:
        ParameterSensitivityResult with grid data and sensitivity score.
    """
    grid: list[SensitivityPoint] = []
    metric_matrix: list[list[float]] = []
    all_values: list[float] = []

    for p1 in param_1_values:
        row: list[float] = []
        for p2 in param_2_values:
            try:
                val = metric_fn(p1, p2)
            except Exception:
                val = 0.0
            grid.append(SensitivityPoint(
                param_1_value=p1,
                param_2_value=p2,
                metric_value=round(val, 6),
            ))
            row.append(round(val, 6))
            all_values.append(val)
        metric_matrix.append(row)

    # Coefficient of variation as sensitivity score
    arr = np.array(all_values)
    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    cv = abs(std_val / mean_val) if mean_val != 0 else float("inf") if std_val > 0 else 0.0

    # Verdict
    if cv < 0.10:
        verdict = "ROBUST: Metric is insensitive to parameter changes (CV < 10%)"
    elif cv < 0.30:
        verdict = "MODERATE: Some parameter sensitivity detected (CV 10-30%)"
    elif cv < 0.60:
        verdict = "FRAGILE: High parameter sensitivity — overfitting risk (CV 30-60%)"
    else:
        verdict = "CRITICAL: Extreme parameter sensitivity — almost certainly overfit (CV > 60%)"

    return ParameterSensitivityResult(
        param_1_name=param_1_name,
        param_2_name=param_2_name,
        metric_name=metric_name,
        grid=grid,
        param_1_values=param_1_values,
        param_2_values=param_2_values,
        metric_matrix=metric_matrix,
        sensitivity_score=round(cv, 6),
        verdict=verdict,
    )


def haircut_sharpe_ratio(
    daily_returns: np.ndarray | list[float],
    n_trials: int = 1,
    ann_factor: int = 365,
) -> HaircutSharpeResult:
    """Haircut Sharpe Ratio after Harvey & Liu (2015).

    Applies two haircuts to the observed Sharpe ratio:
    1. Non-normality adjustment: Penalises strategies with negative skew
       or excess kurtosis (common in crypto).
    2. Multiple testing: Penalises for the number of strategies tried.

    Args:
        daily_returns: Daily strategy returns.
        n_trials: Number of strategy variants tested.
        ann_factor: Annualisation factor.

    Returns:
        HaircutSharpeResult with adjusted Sharpe and breakdown.
    """
    r = np.asarray(daily_returns, dtype=np.float64)
    n = len(r)

    if n < 10:
        return HaircutSharpeResult(
            observed_sharpe=0.0, haircut_sharpe=0.0, haircut_pct=0.0,
            non_normality_haircut=0.0, multiple_testing_haircut=0.0,
            n_trials=n_trials,
        )

    mean_r = float(np.mean(r))
    std_r = float(np.std(r, ddof=1))
    if std_r == 0:
        return HaircutSharpeResult(
            observed_sharpe=0.0, haircut_sharpe=0.0, haircut_pct=0.0,
            non_normality_haircut=0.0, multiple_testing_haircut=0.0,
            n_trials=n_trials,
        )

    daily_sr = mean_r / std_r
    ann_sr = daily_sr * math.sqrt(ann_factor)

    # 1. Non-normality haircut
    # SR_adjusted = SR * [1 - skew/3 * SR + (kurt-3)/24 * SR^2]^{-1}
    skew = float(sp_stats.skew(r))
    kurt = float(sp_stats.kurtosis(r, fisher=True))  # excess kurtosis

    adjustment = 1.0 - (skew / 3.0) * daily_sr + ((kurt) / 24.0) * daily_sr**2
    adjustment = max(adjustment, 0.1)  # Prevent sign flip
    sr_after_nonnorm = daily_sr / adjustment
    non_norm_haircut = abs(daily_sr - sr_after_nonnorm) * math.sqrt(ann_factor)

    # 2. Multiple testing haircut
    # Deduct expected max Sharpe from N independent trials
    n_trials = max(n_trials, 1)
    if n_trials > 1:
        gamma_em = 0.5772156649
        z = math.sqrt(2.0 * math.log(n_trials))
        expected_max_sr = (z - (gamma_em + math.log(math.pi / 2.0)) / (2.0 * z)) / math.sqrt(n)
        mt_haircut = expected_max_sr * math.sqrt(ann_factor)
    else:
        mt_haircut = 0.0

    # Final haircut Sharpe
    haircut_sr = sr_after_nonnorm * math.sqrt(ann_factor) - mt_haircut
    haircut_sr = max(haircut_sr, 0.0)  # Floor at zero

    total_haircut_pct = (1.0 - haircut_sr / ann_sr) * 100.0 if ann_sr > 0 else 0.0

    return HaircutSharpeResult(
        observed_sharpe=round(ann_sr, 6),
        haircut_sharpe=round(haircut_sr, 6),
        haircut_pct=round(max(total_haircut_pct, 0.0), 2),
        non_normality_haircut=round(non_norm_haircut, 6),
        multiple_testing_haircut=round(mt_haircut, 6),
        n_trials=n_trials,
    )


def run_overfitting_report(
    daily_returns: np.ndarray | list[float],
    n_trials: int = 1,
    is_sharpes: list[float] | None = None,
    oos_sharpes: list[float] | None = None,
    is_returns_pct: list[float] | None = None,
    oos_returns_pct: list[float] | None = None,
    ann_factor: int = 365,
) -> OverfittingReport:
    """Run a comprehensive overfitting detection analysis.

    Args:
        daily_returns: Daily strategy returns.
        n_trials: Number of strategy variants tested.
        is_sharpes: In-sample Sharpe per walk-forward window (optional).
        oos_sharpes: Out-of-sample Sharpe per walk-forward window (optional).
        is_returns_pct: IS return per window (optional).
        oos_returns_pct: OOS return per window (optional).
        ann_factor: Annualisation factor.

    Returns:
        OverfittingReport with all detection results.
    """
    r = np.asarray(daily_returns, dtype=np.float64)

    # CPCV
    cpcv = combinatorial_purged_cv(r, ann_factor=ann_factor)

    # Walk-forward efficiency
    wfe = None
    if is_sharpes and oos_sharpes:
        wfe = walk_forward_efficiency(
            is_sharpes, oos_sharpes, is_returns_pct, oos_returns_pct,
        )

    # Haircut Sharpe
    hs = haircut_sharpe_ratio(r, n_trials=n_trials, ann_factor=ann_factor)

    # Overall risk assessment
    risk_signals: list[str] = []

    if cpcv.degradation_ratio < 0.3:
        risk_signals.append("CRITICAL")
    elif cpcv.degradation_ratio < 0.5:
        risk_signals.append("HIGH")
    elif cpcv.degradation_ratio < 0.7:
        risk_signals.append("MODERATE")
    else:
        risk_signals.append("LOW")

    if wfe is not None:
        if wfe.efficiency_ratio < 0:
            risk_signals.append("CRITICAL")
        elif wfe.efficiency_ratio < 0.3:
            risk_signals.append("HIGH")
        elif wfe.efficiency_ratio < 0.5:
            risk_signals.append("MODERATE")
        else:
            risk_signals.append("LOW")

    if hs.haircut_pct > 60:
        risk_signals.append("HIGH")
    elif hs.haircut_pct > 30:
        risk_signals.append("MODERATE")
    else:
        risk_signals.append("LOW")

    # Aggregate: worst signal wins
    risk_order = {"CRITICAL": 4, "HIGH": 3, "MODERATE": 2, "LOW": 1}
    worst = max(risk_signals, key=lambda x: risk_order.get(x, 0))

    return OverfittingReport(
        cpcv=cpcv,
        pbo=None,  # Requires multi-strategy matrix; set via PBO function directly
        walk_forward_efficiency=wfe,
        haircut_sharpe=hs,
        overall_risk=worst,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_sharpe(returns: np.ndarray, ann_factor: int) -> float:
    """Compute annualised Sharpe ratio from an array of returns."""
    if len(returns) < 2:
        return 0.0
    std = float(np.std(returns, ddof=1))
    if std == 0:
        return 0.0
    return float(np.mean(returns)) / std * math.sqrt(ann_factor)
