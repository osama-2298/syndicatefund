"""
Value-at-Risk Metrics Module.

Institutional-grade VaR calculation suite for Syndicate Fund.
Provides Parametric, Historical, and Monte Carlo VaR alongside
CVaR (Expected Shortfall), Component VaR, and Marginal VaR.

All outputs are strict Pydantic models for downstream consumption
by the portfolio risk manager and executive dashboards.

Methods implemented:
    1. Parametric VaR (variance-covariance, normal assumption)
    2. Historical VaR (empirical percentile)
    3. Monte Carlo VaR (Cholesky-correlated simulation with eigenvalue-clipping fallback)
    4. CVaR / Expected Shortfall (tail-average beyond VaR cutoff)
    5. Component VaR (additive per-position decomposition)
    6. Marginal VaR (per-unit sensitivity via finite difference)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()

# ═══════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════

Z_SCORES: dict[float, float] = {
    0.90: 1.2816,
    0.95: 1.6449,
    0.99: 2.3263,
}

DEFAULT_CONFIDENCE = 0.95
MC_NUM_SIMULATIONS = 5_000
MC_HORIZON_DAYS = 1
MIN_OBSERVATIONS = 10
EIGENVALUE_FLOOR = 1e-8  # for Cholesky fallback clipping


# ═══════════════════════════════════════════
#  Pydantic Output Models
# ═══════════════════════════════════════════


class PositionVaR(BaseModel):
    """Per-position VaR decomposition."""

    symbol: str
    weight: float = 0.0
    standalone_var: float = 0.0
    component_var: float = 0.0
    pct_contribution: float = 0.0
    marginal_var: float = 0.0
    beta_to_portfolio: float = 0.0


class VaRReport(BaseModel):
    """
    Complete VaR report produced by ``compute_var_report``.

    All VaR figures are expressed as positive loss amounts
    (percentage of portfolio value).
    """

    # Top-level metrics
    confidence_level: float = DEFAULT_CONFIDENCE
    horizon_days: int = MC_HORIZON_DAYS

    # Three VaR methods
    parametric_var: float = 0.0
    historical_var: float = 0.0
    monte_carlo_var: float = 0.0

    # Expected Shortfall (CVaR)
    parametric_cvar: float = 0.0
    historical_cvar: float = 0.0
    monte_carlo_cvar: float = 0.0

    # Portfolio-level stats
    portfolio_mean_return: float = 0.0
    portfolio_volatility: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0

    # Diversification
    undiversified_var: float = 0.0
    diversification_ratio: float = 0.0

    # Per-position breakdown
    positions: list[PositionVaR] = Field(default_factory=list)

    # Data quality
    num_observations: int = 0
    warnings: list[str] = Field(default_factory=list)

    # Metadata
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════
#  Internal Helpers
# ═══════════════════════════════════════════


def _align_returns(
    returns_history: dict[str, list[float]],
) -> tuple[list[str], np.ndarray]:
    """
    Align per-asset return series to the shortest common length.

    Returns:
        (symbols, returns_matrix)  where returns_matrix has shape (T, N).
    """
    symbols = sorted(returns_history.keys())
    min_len = min(len(returns_history[s]) for s in symbols)
    # Trim from the front so the most recent data is preserved
    matrix = np.column_stack(
        [np.array(returns_history[s][-min_len:], dtype=np.float64) for s in symbols]
    )
    return symbols, matrix


def _safe_cholesky(cov: np.ndarray) -> np.ndarray:
    """
    Attempt Cholesky decomposition.  If the covariance matrix is not
    positive-definite (common with noisy crypto returns), fall back to
    eigenvalue clipping: set any negative eigenvalue to ``EIGENVALUE_FLOOR``
    and reconstruct.

    Returns:
        Lower-triangular Cholesky factor L such that L @ L.T ≈ cov.
    """
    try:
        return np.linalg.cholesky(cov)
    except np.linalg.LinAlgError:
        logger.warning("cholesky_fallback", reason="eigenvalue_clipping")
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        eigenvalues = np.maximum(eigenvalues, EIGENVALUE_FLOOR)
        cov_fixed = (eigenvectors * eigenvalues) @ eigenvectors.T
        # Symmetrise to avoid floating-point drift
        cov_fixed = (cov_fixed + cov_fixed.T) / 2.0
        return np.linalg.cholesky(cov_fixed)


def _portfolio_returns(
    returns_matrix: np.ndarray,
    weights: np.ndarray,
) -> np.ndarray:
    """Compute portfolio return series from asset returns and weights."""
    return returns_matrix @ weights


# ═══════════════════════════════════════════
#  Core VaR Calculations
# ═══════════════════════════════════════════


def parametric_var(
    port_mean: float,
    port_std: float,
    confidence: float = DEFAULT_CONFIDENCE,
    horizon: int = MC_HORIZON_DAYS,
) -> float:
    """
    Variance-covariance (parametric) VaR.

    Assumes normally distributed returns.
    VaR = -(mu * h + z * sigma * sqrt(h))

    Returns a positive number representing the loss at the given confidence.
    """
    z = Z_SCORES.get(confidence, 1.6449)
    var = -(port_mean * horizon - z * port_std * np.sqrt(horizon))
    return max(float(var), 0.0)


def parametric_cvar(
    port_mean: float,
    port_std: float,
    confidence: float = DEFAULT_CONFIDENCE,
    horizon: int = MC_HORIZON_DAYS,
) -> float:
    """
    Parametric Expected Shortfall (CVaR) under normality.

    ES = -(mu * h) + sigma * sqrt(h) * phi(z) / (1 - c)
    where phi is the standard normal PDF.
    """
    z = Z_SCORES.get(confidence, 1.6449)
    from scipy.stats import norm  # deferred to keep import optional path light

    phi_z = norm.pdf(z)
    es = -(port_mean * horizon) + port_std * np.sqrt(horizon) * phi_z / (1.0 - confidence)
    return max(float(es), 0.0)


def historical_var(
    portfolio_returns: np.ndarray,
    confidence: float = DEFAULT_CONFIDENCE,
) -> float:
    """
    Empirical (historical) VaR.

    The loss at the (1 - confidence) percentile of the return distribution.
    """
    alpha = 1.0 - confidence
    cutoff = float(np.percentile(portfolio_returns, alpha * 100))
    return max(-cutoff, 0.0)


def historical_cvar(
    portfolio_returns: np.ndarray,
    confidence: float = DEFAULT_CONFIDENCE,
) -> float:
    """
    Historical Expected Shortfall — average of returns beyond VaR cutoff.
    """
    alpha = 1.0 - confidence
    cutoff = float(np.percentile(portfolio_returns, alpha * 100))
    tail = portfolio_returns[portfolio_returns <= cutoff]
    if len(tail) == 0:
        return historical_var(portfolio_returns, confidence)
    return max(float(-np.mean(tail)), 0.0)


def monte_carlo_var(
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    weights: np.ndarray,
    confidence: float = DEFAULT_CONFIDENCE,
    horizon: int = MC_HORIZON_DAYS,
    num_simulations: int = MC_NUM_SIMULATIONS,
    rng: np.random.Generator | None = None,
) -> tuple[float, float]:
    """
    Monte Carlo VaR via Cholesky-correlated multivariate normal paths.

    Args:
        mean_returns: (N,) annualised or per-period mean returns.
        cov_matrix: (N, N) covariance matrix of returns.
        weights: (N,) portfolio weights.
        confidence: VaR confidence level.
        horizon: holding period in days.
        num_simulations: number of scenarios (default 5 000).
        rng: optional numpy Generator for reproducibility.

    Returns:
        (mc_var, mc_cvar) both as positive loss percentages.
    """
    if rng is None:
        rng = np.random.default_rng()

    n_assets = len(weights)
    L = _safe_cholesky(cov_matrix)

    # Generate correlated random shocks
    Z = rng.standard_normal((num_simulations, n_assets))
    correlated = Z @ L.T  # (sims, N)

    # Simulate portfolio returns for the horizon
    sim_returns = correlated * np.sqrt(horizon) + mean_returns * horizon  # (sims, N)
    port_sim = sim_returns @ weights  # (sims,)

    alpha = 1.0 - confidence
    cutoff = float(np.percentile(port_sim, alpha * 100))
    mc_var = max(-cutoff, 0.0)

    tail = port_sim[port_sim <= cutoff]
    mc_cvar = max(float(-np.mean(tail)), 0.0) if len(tail) > 0 else mc_var

    return mc_var, mc_cvar


# ═══════════════════════════════════════════
#  Component & Marginal VaR
# ═══════════════════════════════════════════


def component_var(
    weights: np.ndarray,
    cov_matrix: np.ndarray,
    portfolio_var: float,
    confidence: float = DEFAULT_CONFIDENCE,
) -> np.ndarray:
    """
    Additive Component VaR decomposition.

    Component VaR_i = w_i * (Sigma @ w)_i / sigma_p * VaR_p

    The components sum exactly to portfolio VaR.
    """
    sigma_w = cov_matrix @ weights  # (N,)
    port_variance = float(weights @ sigma_w)
    port_std = np.sqrt(port_variance) if port_variance > 0 else 1e-12

    # Marginal contribution to risk (per unit weight)
    mcr = sigma_w / port_std  # (N,)

    # Component VaR = weight * MCR * (VaR / z)  ... but simpler:
    # Component VaR_i = (w_i * sigma_w_i / port_variance) * portfolio_var
    comp = (weights * sigma_w / port_variance) * portfolio_var if port_variance > 0 else np.zeros_like(weights)
    return comp


def marginal_var(
    weights: np.ndarray,
    cov_matrix: np.ndarray,
    confidence: float = DEFAULT_CONFIDENCE,
) -> np.ndarray:
    """
    Marginal VaR: sensitivity of portfolio VaR to a one-unit increase in each weight.

    Marginal VaR_i = z * (Sigma @ w)_i / sigma_p
    """
    z = Z_SCORES.get(confidence, 1.6449)
    sigma_w = cov_matrix @ weights
    port_variance = float(weights @ sigma_w)
    port_std = np.sqrt(port_variance) if port_variance > 0 else 1e-12
    return z * sigma_w / port_std


# ═══════════════════════════════════════════
#  Distributional Statistics
# ═══════════════════════════════════════════


def _skewness(x: np.ndarray) -> float:
    """Sample skewness (Fisher definition)."""
    n = len(x)
    if n < 3:
        return 0.0
    m = np.mean(x)
    s = np.std(x, ddof=1)
    if s < 1e-14:
        return 0.0
    return float((n / ((n - 1) * (n - 2))) * np.sum(((x - m) / s) ** 3))


def _kurtosis_excess(x: np.ndarray) -> float:
    """Sample excess kurtosis (Fisher, normal = 0)."""
    n = len(x)
    if n < 4:
        return 0.0
    m = np.mean(x)
    s = np.std(x, ddof=1)
    if s < 1e-14:
        return 0.0
    k4 = float(np.mean(((x - m) / s) ** 4))
    # Bias-corrected excess kurtosis
    excess = ((n + 1) * k4 - 3 * (n - 1)) * (n - 1) / ((n - 2) * (n - 3))
    return excess


# ═══════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════


def compute_var_report(
    returns_history: dict[str, list[float]],
    weights: dict[str, float] | None = None,
    confidence: float = DEFAULT_CONFIDENCE,
    horizon: int = MC_HORIZON_DAYS,
    mc_simulations: int = MC_NUM_SIMULATIONS,
    rng: np.random.Generator | None = None,
) -> VaRReport:
    """
    Compute a full VaR report for a portfolio.

    Args:
        returns_history: ``{symbol: [r_1, r_2, ...]}`` — per-period simple returns.
            All series are trimmed to the shortest common length.
        weights: ``{symbol: weight}`` portfolio weights (must sum to ~1.0).
            If *None*, equal-weight is assumed.
        confidence: VaR confidence level (0.90, 0.95, or 0.99).
        horizon: holding period in days (default 1).
        mc_simulations: number of Monte Carlo paths (default 5 000).
        rng: optional ``numpy.random.Generator`` for reproducible MC.

    Returns:
        ``VaRReport`` with all metrics populated.
    """
    report = VaRReport(confidence_level=confidence, horizon_days=horizon)

    # ── Validate inputs ────────────────────────────────────────────
    if not returns_history:
        report.warnings.append("Empty returns_history — cannot compute VaR.")
        return report

    # Drop symbols with no data
    returns_history = {s: r for s, r in returns_history.items() if len(r) > 0}
    if not returns_history:
        report.warnings.append("All return series are empty.")
        return report

    symbols, returns_matrix = _align_returns(returns_history)
    T, N = returns_matrix.shape
    report.num_observations = T

    if T < MIN_OBSERVATIONS:
        report.warnings.append(
            f"Only {T} observations available (minimum {MIN_OBSERVATIONS}). "
            f"VaR estimates will be unreliable."
        )

    # ── Weights ────────────────────────────────────────────────────
    if weights is None:
        w = np.ones(N) / N
        report.warnings.append("No weights provided — using equal-weight portfolio.")
    else:
        w = np.array([weights.get(s, 0.0) for s in symbols], dtype=np.float64)
        weight_sum = float(np.sum(w))
        if abs(weight_sum) < 1e-10:
            report.warnings.append("Weights sum to zero — using equal-weight fallback.")
            w = np.ones(N) / N
        elif abs(weight_sum - 1.0) > 0.05:
            report.warnings.append(
                f"Weights sum to {weight_sum:.4f} (expected ~1.0). "
                f"Results are based on provided weights without re-normalisation."
            )

    # ── Portfolio return series ────────────────────────────────────
    port_ret = _portfolio_returns(returns_matrix, w)
    port_mean = float(np.mean(port_ret))
    port_std = float(np.std(port_ret, ddof=1)) if T > 1 else 0.0

    report.portfolio_mean_return = port_mean
    report.portfolio_volatility = port_std
    report.skewness = _skewness(port_ret)
    report.kurtosis = _kurtosis_excess(port_ret)

    # Warn on non-normal tails
    if abs(report.skewness) > 1.0:
        report.warnings.append(
            f"Return distribution is significantly skewed ({report.skewness:.2f}). "
            f"Parametric VaR may understate risk."
        )
    if report.kurtosis > 3.0:
        report.warnings.append(
            f"Excess kurtosis is {report.kurtosis:.2f} (fat tails). "
            f"Parametric VaR may understate tail risk."
        )

    # ── Covariance matrix ──────────────────────────────────────────
    if T > 1:
        cov = np.cov(returns_matrix, rowvar=False, ddof=1)
        # Ensure 2-D even for single asset
        cov = np.atleast_2d(cov)
    else:
        cov = np.zeros((N, N))

    mean_vec = np.mean(returns_matrix, axis=0)

    # ── 1. Parametric VaR ──────────────────────────────────────────
    report.parametric_var = parametric_var(port_mean, port_std, confidence, horizon)
    report.parametric_cvar = parametric_cvar(port_mean, port_std, confidence, horizon)

    # ── 2. Historical VaR ──────────────────────────────────────────
    report.historical_var = historical_var(port_ret, confidence)
    report.historical_cvar = historical_cvar(port_ret, confidence)

    # ── 3. Monte Carlo VaR ─────────────────────────────────────────
    try:
        mc_v, mc_cv = monte_carlo_var(
            mean_returns=mean_vec,
            cov_matrix=cov,
            weights=w,
            confidence=confidence,
            horizon=horizon,
            num_simulations=mc_simulations,
            rng=rng,
        )
        report.monte_carlo_var = mc_v
        report.monte_carlo_cvar = mc_cv
    except Exception as exc:
        logger.error("monte_carlo_var_failed", error=str(exc))
        report.warnings.append(f"Monte Carlo VaR failed: {exc}")

    # ── 4. Diversification ratio ───────────────────────────────────
    asset_stds = np.sqrt(np.diag(cov)) if T > 1 else np.zeros(N)
    undiversified = float(np.sum(np.abs(w) * asset_stds))
    z = Z_SCORES.get(confidence, 1.6449)
    report.undiversified_var = undiversified * z * np.sqrt(horizon)
    if report.parametric_var > 1e-12:
        report.diversification_ratio = report.undiversified_var / report.parametric_var
    else:
        report.diversification_ratio = 1.0

    # ── 5. Per-position decomposition ──────────────────────────────
    comp = component_var(w, cov, report.parametric_var, confidence)
    marg = marginal_var(w, cov, confidence)

    for i, sym in enumerate(symbols):
        standalone_std = float(asset_stds[i]) if T > 1 else 0.0
        standalone_v = standalone_std * z * np.sqrt(horizon) * abs(float(w[i]))

        # Beta to portfolio
        port_var_scalar = float(w @ cov @ w)
        if port_var_scalar > 1e-14:
            cov_with_port = float(cov[i, :] @ w)
            beta = cov_with_port / port_var_scalar
        else:
            beta = 0.0

        pct_contrib = float(comp[i]) / report.parametric_var if report.parametric_var > 1e-12 else 0.0

        report.positions.append(
            PositionVaR(
                symbol=sym,
                weight=float(w[i]),
                standalone_var=float(standalone_v),
                component_var=float(comp[i]),
                pct_contribution=pct_contrib,
                marginal_var=float(marg[i]),
                beta_to_portfolio=beta,
            )
        )

    # ── Data quality checks ────────────────────────────────────────
    for sym in symbols:
        series = returns_history[sym]
        n_zeros = sum(1 for r in series[-T:] if abs(r) < 1e-14)
        if n_zeros > T * 0.3:
            report.warnings.append(
                f"{sym}: {n_zeros}/{T} zero returns — possible stale or illiquid data."
            )

    if T < 30:
        report.warnings.append(
            f"Short history ({T} periods). Consider at least 60+ observations "
            f"for reliable VaR estimates."
        )

    logger.info(
        "var_report_computed",
        confidence=confidence,
        horizon=horizon,
        num_assets=N,
        observations=T,
        parametric_var=round(report.parametric_var, 6),
        historical_var=round(report.historical_var, 6),
        monte_carlo_var=round(report.monte_carlo_var, 6),
        diversification_ratio=round(report.diversification_ratio, 4),
        num_warnings=len(report.warnings),
    )

    return report
