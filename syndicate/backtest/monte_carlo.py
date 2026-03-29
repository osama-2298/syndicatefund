"""Monte Carlo simulation for backtest robustness analysis.

Simulates thousands of alternative return paths to answer questions
that a single backtest cannot:

- "What is the probability of a 30% drawdown?"
- "What is the 5th-percentile equity curve?"
- "What is the ruin probability over 2 years?"

Methods:
- Path simulation from historical return distribution
- Bootstrap resampling (block bootstrap for autocorrelation)
- Fat-tail modeling via Student-t distribution
- Drawdown probability estimation
- Ruin probability calculation
- Confidence bands for equity curves
"""

from __future__ import annotations

import math

import numpy as np
from pydantic import BaseModel, Field
from scipy import stats as sp_stats


# ---------------------------------------------------------------------------
# Pydantic output models
# ---------------------------------------------------------------------------

class EquityCurveBand(BaseModel):
    """A single percentile band of the equity curve."""

    percentile: int
    values: list[float] = Field(description="Equity values at each time step")


class DrawdownDistribution(BaseModel):
    """Distribution of maximum drawdowns across simulations."""

    mean_max_dd: float
    median_max_dd: float
    p5_max_dd: float = Field(description="5th percentile (best case)")
    p25_max_dd: float
    p75_max_dd: float
    p95_max_dd: float = Field(description="95th percentile (worst case)")
    prob_dd_exceeds_10: float = Field(description="P(max_dd > 10%)")
    prob_dd_exceeds_20: float = Field(description="P(max_dd > 20%)")
    prob_dd_exceeds_30: float = Field(description="P(max_dd > 30%)")
    prob_dd_exceeds_50: float = Field(description="P(max_dd > 50%)")


class RuinProbabilityResult(BaseModel):
    """Probability of account ruin (hitting a drawdown threshold)."""

    ruin_threshold: float = Field(description="Drawdown threshold defining ruin (e.g., 0.5 = 50%)")
    ruin_probability: float = Field(description="Estimated P(ruin) over the simulation horizon")
    median_time_to_ruin_days: float | None = Field(
        description="Median days to ruin among paths that ruined (None if no ruin)",
    )
    n_paths_ruined: int
    n_paths_total: int
    confidence_interval_95: tuple[float, float] = Field(
        description="95% CI for ruin probability",
    )


class ReturnDistributionFit(BaseModel):
    """Fitted return distribution parameters."""

    distribution: str = Field(description="Distribution name: 'normal' or 'student_t'")
    mean: float
    std: float
    df: float | None = Field(description="Degrees of freedom (Student-t only)")
    skewness: float
    kurtosis: float = Field(description="Excess kurtosis")
    ks_statistic: float = Field(description="Kolmogorov-Smirnov test statistic")
    ks_p_value: float = Field(description="KS test p-value (>0.05 = good fit)")


class MonteCarloResult(BaseModel):
    """Complete Monte Carlo simulation results."""

    n_simulations: int
    n_steps: int
    initial_capital: float
    equity_bands: list[EquityCurveBand] = Field(
        description="Equity curve percentile bands (5th, 25th, 50th, 75th, 95th)",
    )
    terminal_wealth_mean: float
    terminal_wealth_median: float
    terminal_wealth_p5: float
    terminal_wealth_p95: float
    drawdown_distribution: DrawdownDistribution
    ruin_probability: RuinProbabilityResult
    return_distribution_fit: ReturnDistributionFit
    prob_profitable: float = Field(description="P(terminal > initial)")


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def fit_return_distribution(
    daily_returns: np.ndarray | list[float],
) -> ReturnDistributionFit:
    """Fit both normal and Student-t distributions, select the better fit.

    Crypto returns are heavy-tailed, so Student-t typically wins.
    This determines which distribution to use for path simulation.

    Args:
        daily_returns: Historical daily returns.

    Returns:
        ReturnDistributionFit with parameters and goodness-of-fit.
    """
    r = np.asarray(daily_returns, dtype=np.float64)
    n = len(r)

    if n < 10:
        return ReturnDistributionFit(
            distribution="normal", mean=0.0, std=0.01, df=None,
            skewness=0.0, kurtosis=0.0, ks_statistic=1.0, ks_p_value=0.0,
        )

    mu = float(np.mean(r))
    sigma = float(np.std(r, ddof=1))
    skew = float(sp_stats.skew(r))
    kurt = float(sp_stats.kurtosis(r, fisher=True))

    # Fit normal
    ks_norm_stat, ks_norm_p = sp_stats.kstest(r, "norm", args=(mu, sigma))

    # Fit Student-t (MLE)
    try:
        df_t, loc_t, scale_t = sp_stats.t.fit(r)
        ks_t_stat, ks_t_p = sp_stats.kstest(r, "t", args=(df_t, loc_t, scale_t))
    except Exception:
        df_t, loc_t, scale_t = 30.0, mu, sigma
        ks_t_stat, ks_t_p = ks_norm_stat, ks_norm_p

    # Select distribution with better KS p-value
    if ks_t_p > ks_norm_p:
        return ReturnDistributionFit(
            distribution="student_t",
            mean=round(loc_t, 8),
            std=round(scale_t, 8),
            df=round(df_t, 4),
            skewness=round(skew, 6),
            kurtosis=round(kurt, 6),
            ks_statistic=round(ks_t_stat, 6),
            ks_p_value=round(ks_t_p, 6),
        )

    return ReturnDistributionFit(
        distribution="normal",
        mean=round(mu, 8),
        std=round(sigma, 8),
        df=None,
        skewness=round(skew, 6),
        kurtosis=round(kurt, 6),
        ks_statistic=round(ks_norm_stat, 6),
        ks_p_value=round(ks_norm_p, 6),
    )


def simulate_paths(
    daily_returns: np.ndarray | list[float],
    n_simulations: int = 10_000,
    n_steps: int = 365,
    initial_capital: float = 100_000.0,
    method: str = "bootstrap",
    block_size: int = 5,
    seed: int | None = 42,
) -> np.ndarray:
    """Simulate equity curve paths.

    Args:
        daily_returns: Historical daily returns for calibration.
        n_simulations: Number of Monte Carlo paths.
        n_steps: Number of forward time steps (days).
        initial_capital: Starting capital.
        method: ``"bootstrap"`` (block resampling) or ``"parametric"`` (fitted distribution).
        block_size: Block size for bootstrap method.
        seed: Random seed for reproducibility.

    Returns:
        Array of shape (n_simulations, n_steps + 1) with equity values.
        Column 0 is initial_capital for all paths.
    """
    r = np.asarray(daily_returns, dtype=np.float64)
    rng = np.random.default_rng(seed)
    n_hist = len(r)

    if n_hist < 5:
        # Not enough data — return flat paths
        paths = np.full((n_simulations, n_steps + 1), initial_capital)
        return paths

    # Generate simulated returns: (n_simulations, n_steps)
    if method == "bootstrap":
        sim_returns = _block_bootstrap_returns(r, n_simulations, n_steps, block_size, rng)
    else:
        sim_returns = _parametric_returns(r, n_simulations, n_steps, rng)

    # Convert to equity paths
    cum_returns = np.cumprod(1.0 + sim_returns, axis=1)
    paths = np.column_stack([
        np.full(n_simulations, initial_capital),
        initial_capital * cum_returns,
    ])

    return paths


def compute_equity_bands(
    paths: np.ndarray,
    percentiles: list[int] | None = None,
) -> list[EquityCurveBand]:
    """Compute percentile bands from simulated equity paths.

    Args:
        paths: Array of shape (n_simulations, n_steps + 1).
        percentiles: Percentiles to compute (default: 5, 25, 50, 75, 95).

    Returns:
        List of EquityCurveBand, one per percentile.
    """
    if percentiles is None:
        percentiles = [5, 25, 50, 75, 95]

    bands: list[EquityCurveBand] = []
    for p in percentiles:
        values = np.percentile(paths, p, axis=0)
        bands.append(EquityCurveBand(
            percentile=p,
            values=[round(float(v), 2) for v in values],
        ))
    return bands


def compute_drawdown_distribution(
    paths: np.ndarray,
) -> DrawdownDistribution:
    """Compute the distribution of maximum drawdowns across all simulated paths.

    Args:
        paths: Array of shape (n_simulations, n_steps + 1).

    Returns:
        DrawdownDistribution with percentiles and exceedance probabilities.
    """
    n_sims = paths.shape[0]
    max_dds = np.empty(n_sims, dtype=np.float64)

    for i in range(n_sims):
        equity = paths[i]
        peak = np.maximum.accumulate(equity)
        dd = (peak - equity) / np.where(peak > 0, peak, 1.0)
        max_dds[i] = float(np.max(dd))

    return DrawdownDistribution(
        mean_max_dd=round(float(np.mean(max_dds)), 6),
        median_max_dd=round(float(np.median(max_dds)), 6),
        p5_max_dd=round(float(np.percentile(max_dds, 5)), 6),
        p25_max_dd=round(float(np.percentile(max_dds, 25)), 6),
        p75_max_dd=round(float(np.percentile(max_dds, 75)), 6),
        p95_max_dd=round(float(np.percentile(max_dds, 95)), 6),
        prob_dd_exceeds_10=round(float(np.mean(max_dds > 0.10)), 6),
        prob_dd_exceeds_20=round(float(np.mean(max_dds > 0.20)), 6),
        prob_dd_exceeds_30=round(float(np.mean(max_dds > 0.30)), 6),
        prob_dd_exceeds_50=round(float(np.mean(max_dds > 0.50)), 6),
    )


def compute_ruin_probability(
    paths: np.ndarray,
    ruin_threshold: float = 0.50,
) -> RuinProbabilityResult:
    """Estimate the probability of ruin (drawdown exceeding a threshold).

    Args:
        paths: Array of shape (n_simulations, n_steps + 1).
        ruin_threshold: Drawdown fraction that defines "ruin" (e.g., 0.50 = 50%).

    Returns:
        RuinProbabilityResult with probability and confidence interval.
    """
    n_sims = paths.shape[0]
    n_steps = paths.shape[1] - 1
    ruined = np.zeros(n_sims, dtype=bool)
    time_to_ruin: list[float] = []

    for i in range(n_sims):
        equity = paths[i]
        peak = np.maximum.accumulate(equity)
        dd = (peak - equity) / np.where(peak > 0, peak, 1.0)

        # Check if ruin threshold was ever breached
        breach_indices = np.where(dd >= ruin_threshold)[0]
        if len(breach_indices) > 0:
            ruined[i] = True
            time_to_ruin.append(float(breach_indices[0]))

    n_ruined = int(np.sum(ruined))
    ruin_prob = n_ruined / n_sims

    # Wilson score 95% CI for proportion
    z = 1.96
    denom = 1 + z**2 / n_sims
    centre = (ruin_prob + z**2 / (2 * n_sims)) / denom
    spread = z * math.sqrt(
        (ruin_prob * (1 - ruin_prob) + z**2 / (4 * n_sims)) / n_sims
    ) / denom
    ci_low = max(centre - spread, 0.0)
    ci_high = min(centre + spread, 1.0)

    median_ttr = float(np.median(time_to_ruin)) if time_to_ruin else None

    return RuinProbabilityResult(
        ruin_threshold=ruin_threshold,
        ruin_probability=round(ruin_prob, 6),
        median_time_to_ruin_days=round(median_ttr, 1) if median_ttr is not None else None,
        n_paths_ruined=n_ruined,
        n_paths_total=n_sims,
        confidence_interval_95=(round(ci_low, 6), round(ci_high, 6)),
    )


def run_monte_carlo(
    daily_returns: np.ndarray | list[float],
    n_simulations: int = 10_000,
    n_steps: int = 365,
    initial_capital: float = 100_000.0,
    ruin_threshold: float = 0.50,
    method: str = "bootstrap",
    block_size: int = 5,
    seed: int | None = 42,
) -> MonteCarloResult:
    """Run a complete Monte Carlo simulation analysis.

    This is the primary entry point that chains all sub-analyses:
    1. Fit return distribution
    2. Simulate paths
    3. Compute equity bands
    4. Compute drawdown distribution
    5. Compute ruin probability

    Args:
        daily_returns: Historical daily returns for calibration.
        n_simulations: Number of Monte Carlo paths.
        n_steps: Forward simulation horizon in days.
        initial_capital: Starting capital.
        ruin_threshold: Drawdown fraction defining ruin.
        method: ``"bootstrap"`` or ``"parametric"``.
        block_size: Block size for bootstrap method.
        seed: Random seed.

    Returns:
        MonteCarloResult with all simulation outputs.
    """
    r = np.asarray(daily_returns, dtype=np.float64)

    # 1. Fit distribution
    dist_fit = fit_return_distribution(r)

    # 2. Simulate paths
    paths = simulate_paths(
        r, n_simulations=n_simulations, n_steps=n_steps,
        initial_capital=initial_capital, method=method,
        block_size=block_size, seed=seed,
    )

    # 3. Equity bands
    bands = compute_equity_bands(paths)

    # 4. Terminal wealth stats
    terminal = paths[:, -1]
    prob_profitable = float(np.mean(terminal > initial_capital))

    # 5. Drawdown distribution
    dd_dist = compute_drawdown_distribution(paths)

    # 6. Ruin probability
    ruin = compute_ruin_probability(paths, ruin_threshold=ruin_threshold)

    return MonteCarloResult(
        n_simulations=n_simulations,
        n_steps=n_steps,
        initial_capital=initial_capital,
        equity_bands=bands,
        terminal_wealth_mean=round(float(np.mean(terminal)), 2),
        terminal_wealth_median=round(float(np.median(terminal)), 2),
        terminal_wealth_p5=round(float(np.percentile(terminal, 5)), 2),
        terminal_wealth_p95=round(float(np.percentile(terminal, 95)), 2),
        drawdown_distribution=dd_dist,
        ruin_probability=ruin,
        return_distribution_fit=dist_fit,
        prob_profitable=round(prob_profitable, 6),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _block_bootstrap_returns(
    historical_returns: np.ndarray,
    n_simulations: int,
    n_steps: int,
    block_size: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate simulated returns via circular block bootstrap.

    Block bootstrap preserves the autocorrelation structure of returns,
    which is critical for realistic drawdown estimation.

    Returns array of shape (n_simulations, n_steps).
    """
    n_hist = len(historical_returns)
    n_blocks = math.ceil(n_steps / block_size)

    sim_returns = np.empty((n_simulations, n_steps), dtype=np.float64)

    for i in range(n_simulations):
        starts = rng.integers(0, n_hist, size=n_blocks)
        indices = np.concatenate(
            [np.arange(s, s + block_size) % n_hist for s in starts]
        )[:n_steps]
        sim_returns[i] = historical_returns[indices]

    return sim_returns


def _parametric_returns(
    historical_returns: np.ndarray,
    n_simulations: int,
    n_steps: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate simulated returns from a fitted Student-t distribution.

    Falls back to normal if Student-t fitting fails.

    Returns array of shape (n_simulations, n_steps).
    """
    try:
        df, loc, scale = sp_stats.t.fit(historical_returns)
        if df < 2:
            df = 2.0  # Ensure finite variance
        sim_returns = sp_stats.t.rvs(
            df, loc=loc, scale=scale,
            size=(n_simulations, n_steps),
            random_state=rng,
        )
    except Exception:
        mu = float(np.mean(historical_returns))
        sigma = float(np.std(historical_returns, ddof=1))
        sim_returns = rng.normal(mu, sigma, size=(n_simulations, n_steps))

    return sim_returns.astype(np.float64)
