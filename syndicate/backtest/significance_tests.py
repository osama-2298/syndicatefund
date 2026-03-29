"""Statistical significance testing for backtest results.

Implements rigorous hypothesis tests to determine whether observed
performance metrics are statistically distinguishable from noise:

- Sharpe ratio significance (Lo 2002 autocorrelation-adjusted)
- Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014)
- Binomial win rate test
- Ljung-Box autocorrelation test
- Bootstrap confidence intervals
- Multiple testing correction (Bonferroni, Holm)
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from pydantic import BaseModel, Field
from scipy import stats as sp_stats


# ---------------------------------------------------------------------------
# Pydantic output models
# ---------------------------------------------------------------------------

class SharpeSignificanceResult(BaseModel):
    """Result of Sharpe ratio significance test (Lo 2002)."""

    observed_sharpe: float = Field(description="Annualised Sharpe ratio")
    se_sharpe: float = Field(description="Standard error of Sharpe (IID assumption)")
    se_sharpe_adjusted: float = Field(
        description="Autocorrelation-adjusted standard error (Lo 2002)",
    )
    t_stat: float = Field(description="t-statistic for H0: Sharpe = 0")
    p_value: float = Field(description="Two-sided p-value")
    significant_at_05: bool = Field(description="Significant at alpha=0.05")
    significant_at_01: bool = Field(description="Significant at alpha=0.01")
    n_observations: int = 0


class DeflatedSharpeResult(BaseModel):
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014)."""

    observed_sharpe: float
    deflated_sharpe: float = Field(
        description="Sharpe ratio after deflation for multiple testing",
    )
    p_value: float = Field(description="Probability that Sharpe is due to luck")
    n_trials: int = Field(description="Number of strategy trials / backtests")
    expected_max_sharpe: float = Field(
        description="Expected maximum Sharpe under null (Euler-Mascheroni)",
    )
    significant: bool


class WinRateTestResult(BaseModel):
    """Binomial test for win rate significance."""

    observed_win_rate: float
    n_trades: int
    p_value: float = Field(description="Two-sided p-value vs H0: win_rate=0.5")
    ci_lower: float = Field(description="95% CI lower bound")
    ci_upper: float = Field(description="95% CI upper bound")
    significant_at_05: bool


class LjungBoxResult(BaseModel):
    """Ljung-Box test for autocorrelation in returns."""

    test_statistic: float
    p_value: float
    n_lags: int
    has_autocorrelation: bool = Field(
        description="True if significant autocorrelation detected at 5%",
    )
    autocorrelations: list[float] = Field(
        description="Sample autocorrelations at each lag",
    )


class BootstrapCIResult(BaseModel):
    """Bootstrap confidence intervals for a metric."""

    metric_name: str
    point_estimate: float
    ci_5: float = Field(description="5th percentile")
    ci_25: float = Field(description="25th percentile")
    ci_50: float = Field(description="Median (50th percentile)")
    ci_75: float = Field(description="75th percentile")
    ci_95: float = Field(description="95th percentile")
    n_bootstrap: int


class MultipleTestingResult(BaseModel):
    """Corrected p-values for multiple testing."""

    method: str = Field(description="Correction method: bonferroni or holm")
    original_p_values: list[float]
    corrected_p_values: list[float]
    rejected: list[bool] = Field(
        description="Which hypotheses are rejected at alpha=0.05 after correction",
    )
    alpha: float = 0.05


class SignificanceReport(BaseModel):
    """Full significance report aggregating all tests."""

    sharpe_test: SharpeSignificanceResult
    deflated_sharpe: DeflatedSharpeResult | None = None
    win_rate_test: WinRateTestResult | None = None
    ljung_box: LjungBoxResult
    bootstrap_sharpe: BootstrapCIResult
    bootstrap_max_dd: BootstrapCIResult
    bootstrap_returns: BootstrapCIResult


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def sharpe_significance(
    daily_returns: np.ndarray | list[float],
    ann_factor: int = 365,
    max_lag: int = 5,
) -> SharpeSignificanceResult:
    """Test whether the observed Sharpe ratio is significantly different from zero.

    Uses the Lo (2002) method that adjusts the standard error for serial
    autocorrelation in returns -- critical for high-frequency crypto strategies
    where returns exhibit positive autocorrelation at short horizons.

    Args:
        daily_returns: Array of fractional daily returns.
        ann_factor: Annualisation factor (365 for crypto, 252 for equities).
        max_lag: Maximum lag for autocorrelation adjustment.

    Returns:
        SharpeSignificanceResult with t-stat and p-value.
    """
    r = np.asarray(daily_returns, dtype=np.float64)
    n = len(r)
    if n < 10:
        return SharpeSignificanceResult(
            observed_sharpe=0.0,
            se_sharpe=float("inf"),
            se_sharpe_adjusted=float("inf"),
            t_stat=0.0,
            p_value=1.0,
            significant_at_05=False,
            significant_at_01=False,
            n_observations=n,
        )

    mean_r = float(np.mean(r))
    std_r = float(np.std(r, ddof=1))
    if std_r == 0:
        return SharpeSignificanceResult(
            observed_sharpe=0.0,
            se_sharpe=float("inf"),
            se_sharpe_adjusted=float("inf"),
            t_stat=0.0,
            p_value=1.0,
            significant_at_05=False,
            significant_at_01=False,
            n_observations=n,
        )

    daily_sharpe = mean_r / std_r
    ann_sharpe = daily_sharpe * math.sqrt(ann_factor)

    # IID standard error: SE(SR) = sqrt((1 + SR^2/2) / n)
    se_iid = math.sqrt((1.0 + 0.5 * daily_sharpe**2) / n)

    # Lo (2002) autocorrelation adjustment
    # Compute sample autocorrelations
    rho = _sample_autocorrelations(r, max_lag)
    # Adjustment factor: eta = 1 + 2 * sum_{k=1}^{q} (1 - k/(q+1)) * rho_k
    eta = 1.0
    q = min(max_lag, n - 1)
    for k in range(1, q + 1):
        eta += 2.0 * (1.0 - k / (q + 1)) * rho[k - 1]
    eta = max(eta, 0.1)  # Prevent degenerate cases

    se_adjusted = se_iid * math.sqrt(eta)

    # Annualise the standard errors
    se_iid_ann = se_iid * math.sqrt(ann_factor)
    se_adjusted_ann = se_adjusted * math.sqrt(ann_factor)

    # t-statistic using adjusted SE
    t_stat = ann_sharpe / se_adjusted_ann if se_adjusted_ann > 0 else 0.0
    p_value = float(2.0 * sp_stats.norm.sf(abs(t_stat)))

    return SharpeSignificanceResult(
        observed_sharpe=round(ann_sharpe, 6),
        se_sharpe=round(se_iid_ann, 6),
        se_sharpe_adjusted=round(se_adjusted_ann, 6),
        t_stat=round(t_stat, 6),
        p_value=round(p_value, 6),
        significant_at_05=p_value < 0.05,
        significant_at_01=p_value < 0.01,
        n_observations=n,
    )


def deflated_sharpe_ratio(
    daily_returns: np.ndarray | list[float],
    n_trials: int,
    ann_factor: int = 365,
) -> DeflatedSharpeResult:
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014).

    Adjusts the Sharpe ratio for the number of strategy configurations
    tested (multiple testing bias). The key insight: if you try N strategies,
    the best one's Sharpe is inflated by approximately sqrt(2 * ln(N)).

    Args:
        daily_returns: Returns of the selected (best) strategy.
        n_trials: Total number of strategy variants tested.
        ann_factor: Annualisation factor.

    Returns:
        DeflatedSharpeResult with deflated Sharpe and p-value.
    """
    r = np.asarray(daily_returns, dtype=np.float64)
    n = len(r)
    n_trials = max(n_trials, 1)

    if n < 10:
        return DeflatedSharpeResult(
            observed_sharpe=0.0,
            deflated_sharpe=0.0,
            p_value=1.0,
            n_trials=n_trials,
            expected_max_sharpe=0.0,
            significant=False,
        )

    mean_r = float(np.mean(r))
    std_r = float(np.std(r, ddof=1))
    if std_r == 0:
        return DeflatedSharpeResult(
            observed_sharpe=0.0,
            deflated_sharpe=0.0,
            p_value=1.0,
            n_trials=n_trials,
            expected_max_sharpe=0.0,
            significant=False,
        )

    daily_sharpe = mean_r / std_r
    ann_sharpe = daily_sharpe * math.sqrt(ann_factor)

    # Expected maximum Sharpe under the null (all strategies have SR=0)
    # E[max(SR)] ~ sqrt(2 * ln(N)) - (gamma + ln(pi/2)) / (2 * sqrt(2 * ln(N)))
    # where gamma ~ 0.5772 (Euler-Mascheroni constant)
    gamma_em = 0.5772156649
    if n_trials > 1:
        z = math.sqrt(2.0 * math.log(n_trials))
        expected_max_sr = z - (gamma_em + math.log(math.pi / 2.0)) / (2.0 * z)
    else:
        expected_max_sr = 0.0

    # Annualise
    expected_max_sr_ann = expected_max_sr * math.sqrt(ann_factor / n)

    # Standard error of Sharpe accounting for skewness and kurtosis
    skew = float(sp_stats.skew(r))
    kurt = float(sp_stats.kurtosis(r, fisher=True))

    se_sr = math.sqrt(
        (1.0 - skew * daily_sharpe + ((kurt - 1) / 4.0) * daily_sharpe**2) / (n - 1)
    )

    # Deflated Sharpe = (observed - expected_max) / SE
    deflated = (daily_sharpe - expected_max_sr / math.sqrt(n)) / se_sr if se_sr > 0 else 0.0

    # p-value: probability that the observed Sharpe is due to luck
    p_value = float(sp_stats.norm.sf(deflated))

    return DeflatedSharpeResult(
        observed_sharpe=round(ann_sharpe, 6),
        deflated_sharpe=round(deflated, 6),
        p_value=round(min(p_value, 1.0), 6),
        n_trials=n_trials,
        expected_max_sharpe=round(expected_max_sr_ann, 6),
        significant=p_value < 0.05,
    )


def win_rate_significance(
    n_wins: int,
    n_total: int,
    null_rate: float = 0.5,
) -> WinRateTestResult:
    """Binomial test for whether the win rate is significantly different from chance.

    Args:
        n_wins: Number of winning trades.
        n_total: Total number of trades.
        null_rate: Null hypothesis win rate (default 50%).

    Returns:
        WinRateTestResult with p-value and confidence interval.
    """
    if n_total == 0:
        return WinRateTestResult(
            observed_win_rate=0.0,
            n_trades=0,
            p_value=1.0,
            ci_lower=0.0,
            ci_upper=1.0,
            significant_at_05=False,
        )

    observed_rate = n_wins / n_total

    # Exact binomial test (two-sided)
    result = sp_stats.binomtest(n_wins, n_total, null_rate, alternative="two-sided")
    p_value = float(result.pvalue)

    # Wilson score confidence interval (better than normal approx for small n)
    ci = result.proportion_ci(confidence_level=0.95, method="wilson")

    return WinRateTestResult(
        observed_win_rate=round(observed_rate, 6),
        n_trades=n_total,
        p_value=round(p_value, 6),
        ci_lower=round(ci.low, 6),
        ci_upper=round(ci.high, 6),
        significant_at_05=p_value < 0.05,
    )


def ljung_box_test(
    daily_returns: np.ndarray | list[float],
    n_lags: int = 10,
) -> LjungBoxResult:
    """Ljung-Box test for autocorrelation in returns.

    Significant autocorrelation in returns suggests:
    - Exploitable patterns (good for momentum strategies)
    - Non-independent observations (inflated Sharpe SE)
    - Potential look-ahead bias in backtest

    Args:
        daily_returns: Array of fractional daily returns.
        n_lags: Number of lags to test.

    Returns:
        LjungBoxResult with test statistic and p-value.
    """
    r = np.asarray(daily_returns, dtype=np.float64)
    n = len(r)

    if n < n_lags + 5:
        return LjungBoxResult(
            test_statistic=0.0,
            p_value=1.0,
            n_lags=n_lags,
            has_autocorrelation=False,
            autocorrelations=[0.0] * n_lags,
        )

    # Compute sample autocorrelations
    rho = _sample_autocorrelations(r, n_lags)

    # Ljung-Box Q statistic: Q = n(n+2) * sum_{k=1}^{m} rho_k^2 / (n - k)
    q_stat = 0.0
    for k in range(1, n_lags + 1):
        q_stat += rho[k - 1] ** 2 / (n - k)
    q_stat *= n * (n + 2)

    # Under H0 (no autocorrelation), Q ~ chi-squared(n_lags)
    p_value = float(sp_stats.chi2.sf(q_stat, df=n_lags))

    return LjungBoxResult(
        test_statistic=round(q_stat, 6),
        p_value=round(p_value, 6),
        n_lags=n_lags,
        has_autocorrelation=p_value < 0.05,
        autocorrelations=[round(float(rho[k]), 6) for k in range(n_lags)],
    )


def bootstrap_confidence_interval(
    daily_returns: np.ndarray | list[float],
    metric_fn: Any,
    metric_name: str = "metric",
    n_bootstrap: int = 10_000,
    block_size: int = 5,
    seed: int | None = 42,
) -> BootstrapCIResult:
    """Block bootstrap confidence intervals for any metric.

    Uses a circular block bootstrap to preserve serial dependence in returns,
    which is critical for autocorrelated crypto returns.

    Args:
        daily_returns: Array of fractional daily returns.
        metric_fn: Callable that takes an array of returns and returns a scalar.
        metric_name: Label for the metric.
        n_bootstrap: Number of bootstrap replications.
        block_size: Block size for block bootstrap (preserves autocorrelation).
        seed: Random seed for reproducibility.

    Returns:
        BootstrapCIResult with percentile confidence bands.
    """
    r = np.asarray(daily_returns, dtype=np.float64)
    n = len(r)

    if n < 10:
        point = float(metric_fn(r)) if n > 0 else 0.0
        return BootstrapCIResult(
            metric_name=metric_name,
            point_estimate=round(point, 6),
            ci_5=round(point, 6),
            ci_25=round(point, 6),
            ci_50=round(point, 6),
            ci_75=round(point, 6),
            ci_95=round(point, 6),
            n_bootstrap=0,
        )

    rng = np.random.default_rng(seed)
    point_estimate = float(metric_fn(r))

    # Circular block bootstrap
    n_blocks = math.ceil(n / block_size)
    boot_stats = np.empty(n_bootstrap, dtype=np.float64)

    for b in range(n_bootstrap):
        # Sample random block start indices
        starts = rng.integers(0, n, size=n_blocks)
        # Build bootstrap sample from consecutive blocks (circular)
        indices = np.concatenate(
            [np.arange(s, s + block_size) % n for s in starts]
        )[:n]
        boot_sample = r[indices]
        boot_stats[b] = metric_fn(boot_sample)

    return BootstrapCIResult(
        metric_name=metric_name,
        point_estimate=round(point_estimate, 6),
        ci_5=round(float(np.percentile(boot_stats, 5)), 6),
        ci_25=round(float(np.percentile(boot_stats, 25)), 6),
        ci_50=round(float(np.percentile(boot_stats, 50)), 6),
        ci_75=round(float(np.percentile(boot_stats, 75)), 6),
        ci_95=round(float(np.percentile(boot_stats, 95)), 6),
        n_bootstrap=n_bootstrap,
    )


def multiple_testing_correction(
    p_values: list[float],
    method: str = "holm",
    alpha: float = 0.05,
) -> MultipleTestingResult:
    """Correct p-values for multiple hypothesis testing.

    When running many significance tests (e.g., testing multiple strategies
    or multiple metrics), the probability of at least one false positive
    increases. This function controls the family-wise error rate.

    Args:
        p_values: List of raw p-values from individual tests.
        method: ``"bonferroni"`` or ``"holm"`` (Holm step-down, more powerful).
        alpha: Significance level.

    Returns:
        MultipleTestingResult with corrected p-values and rejection decisions.
    """
    n = len(p_values)
    if n == 0:
        return MultipleTestingResult(
            method=method,
            original_p_values=[],
            corrected_p_values=[],
            rejected=[],
            alpha=alpha,
        )

    pv = np.asarray(p_values, dtype=np.float64)

    if method == "bonferroni":
        corrected = np.minimum(pv * n, 1.0)
        rejected = (corrected < alpha).tolist()
        return MultipleTestingResult(
            method="bonferroni",
            original_p_values=[round(float(p), 6) for p in pv],
            corrected_p_values=[round(float(p), 6) for p in corrected],
            rejected=rejected,
            alpha=alpha,
        )

    # Holm step-down procedure (uniformly more powerful than Bonferroni)
    sort_idx = np.argsort(pv)
    sorted_pv = pv[sort_idx]
    corrected = np.empty(n, dtype=np.float64)

    cumulative_max = 0.0
    for i in range(n):
        adjusted = sorted_pv[i] * (n - i)
        cumulative_max = max(cumulative_max, adjusted)
        corrected[sort_idx[i]] = min(cumulative_max, 1.0)

    rejected = (corrected < alpha).tolist()

    return MultipleTestingResult(
        method="holm",
        original_p_values=[round(float(p), 6) for p in pv],
        corrected_p_values=[round(float(p), 6) for p in corrected],
        rejected=rejected,
        alpha=alpha,
    )


# ---------------------------------------------------------------------------
# Convenience: full report
# ---------------------------------------------------------------------------

def run_significance_report(
    daily_returns: np.ndarray | list[float],
    n_wins: int = 0,
    n_total_trades: int = 0,
    n_trials: int = 1,
    ann_factor: int = 365,
) -> SignificanceReport:
    """Run all significance tests and return a unified report.

    Args:
        daily_returns: Array of fractional daily returns.
        n_wins: Number of winning trades (for binomial test).
        n_total_trades: Total number of trades.
        n_trials: Number of strategies tested (for deflated Sharpe).
        ann_factor: Annualisation factor.

    Returns:
        SignificanceReport combining all test results.
    """
    r = np.asarray(daily_returns, dtype=np.float64)

    # Sharpe significance
    sharpe_test = sharpe_significance(r, ann_factor=ann_factor)

    # Deflated Sharpe (only meaningful if multiple trials)
    deflated = None
    if n_trials > 1:
        deflated = deflated_sharpe_ratio(r, n_trials=n_trials, ann_factor=ann_factor)

    # Win rate
    win_test = None
    if n_total_trades > 0:
        win_test = win_rate_significance(n_wins, n_total_trades)

    # Ljung-Box
    lb = ljung_box_test(r)

    # Bootstrap CIs for key metrics
    def _sharpe_fn(returns: np.ndarray) -> float:
        if len(returns) < 2:
            return 0.0
        s = float(np.std(returns, ddof=1))
        return float(np.mean(returns)) / s * math.sqrt(ann_factor) if s > 0 else 0.0

    def _max_dd_fn(returns: np.ndarray) -> float:
        cum = np.cumprod(1.0 + returns)
        peak = np.maximum.accumulate(cum)
        dd = (peak - cum) / np.where(peak > 0, peak, 1.0)
        return float(np.max(dd)) if len(dd) > 0 else 0.0

    def _total_return_fn(returns: np.ndarray) -> float:
        return float(np.prod(1.0 + returns) - 1.0) * 100.0

    boot_sharpe = bootstrap_confidence_interval(r, _sharpe_fn, "sharpe_ratio")
    boot_dd = bootstrap_confidence_interval(r, _max_dd_fn, "max_drawdown")
    boot_ret = bootstrap_confidence_interval(r, _total_return_fn, "total_return_pct")

    return SignificanceReport(
        sharpe_test=sharpe_test,
        deflated_sharpe=deflated,
        win_rate_test=win_test,
        ljung_box=lb,
        bootstrap_sharpe=boot_sharpe,
        bootstrap_max_dd=boot_dd,
        bootstrap_returns=boot_ret,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sample_autocorrelations(r: np.ndarray, max_lag: int) -> np.ndarray:
    """Compute sample autocorrelation coefficients for lags 1..max_lag."""
    n = len(r)
    mean_r = np.mean(r)
    demeaned = r - mean_r
    var = float(np.sum(demeaned**2))
    if var == 0:
        return np.zeros(max_lag)

    rho = np.empty(max_lag, dtype=np.float64)
    for k in range(1, max_lag + 1):
        if k >= n:
            rho[k - 1] = 0.0
        else:
            rho[k - 1] = float(np.sum(demeaned[:n - k] * demeaned[k:])) / var
    return rho
