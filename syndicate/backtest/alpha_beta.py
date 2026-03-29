"""Alpha/Beta decomposition and multi-factor attribution.

Decomposes strategy returns into systematic factor exposures and
residual alpha to answer: "Is this strategy genuinely skilled, or is it
just levered beta to BTC/ETH?"

- Jensen's Alpha (CAPM)
- Rolling beta estimation (configurable window)
- Fama-French 3-factor model (market, size, value)
- Crypto-specific factor model (BTC, ETH, DeFi, momentum)
- Information Coefficient (IC) analysis
- Factor contribution breakdown
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

class JensensAlphaResult(BaseModel):
    """CAPM alpha: the return unexplained by market exposure."""

    alpha_daily: float = Field(description="Daily alpha (intercept)")
    alpha_annualised: float = Field(description="Annualised alpha")
    beta: float = Field(description="Market beta (slope)")
    r_squared: float = Field(description="R-squared of regression")
    alpha_t_stat: float = Field(description="t-statistic for alpha")
    alpha_p_value: float = Field(description="p-value for H0: alpha=0")
    beta_t_stat: float = Field(description="t-statistic for beta")
    beta_p_value: float = Field(description="p-value for H0: beta=0")
    n_observations: int = 0


class RollingBetaResult(BaseModel):
    """Rolling beta over time."""

    dates: list[str] = Field(description="Date labels for each beta estimate")
    betas: list[float] = Field(description="Rolling beta values")
    window_size: int
    mean_beta: float
    std_beta: float = Field(description="Std dev of beta (stability measure)")
    min_beta: float
    max_beta: float


class FactorExposure(BaseModel):
    """Single factor exposure from a multi-factor regression."""

    factor_name: str
    beta: float = Field(description="Factor loading (coefficient)")
    t_stat: float
    p_value: float
    contribution_pct: float = Field(
        description="Percentage of return attributable to this factor",
    )


class MultiFactorResult(BaseModel):
    """Multi-factor model decomposition."""

    model_name: str = Field(description="E.g. 'fama_french_3f' or 'crypto_4f'")
    alpha_daily: float
    alpha_annualised: float
    alpha_t_stat: float
    alpha_p_value: float
    r_squared: float
    adjusted_r_squared: float
    factors: list[FactorExposure]
    residual_vol_annualised: float = Field(
        description="Annualised volatility of unexplained returns",
    )
    n_observations: int = 0


class ICAnalysisResult(BaseModel):
    """Information Coefficient analysis for signal quality."""

    mean_ic: float = Field(description="Mean rank IC across periods")
    std_ic: float = Field(description="Std dev of IC")
    ic_ir: float = Field(description="IC Information Ratio = mean_ic / std_ic")
    t_stat: float = Field(description="t-stat for H0: mean_ic=0")
    p_value: float
    hit_rate: float = Field(description="Fraction of periods with positive IC")
    ic_series: list[float] = Field(description="IC for each period")
    n_periods: int


class FactorContribution(BaseModel):
    """Breakdown of total return into factor contributions."""

    total_return_pct: float
    alpha_contribution_pct: float
    factor_contributions: dict[str, float] = Field(
        description="Return contribution from each factor in percent",
    )
    residual_pct: float = Field(description="Unexplained return")


class AlphaBetaReport(BaseModel):
    """Complete alpha/beta analysis report."""

    jensens_alpha: JensensAlphaResult
    rolling_beta: RollingBetaResult
    crypto_factors: MultiFactorResult | None = None
    fama_french: MultiFactorResult | None = None
    factor_contribution: FactorContribution | None = None


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def jensens_alpha(
    strategy_returns: np.ndarray | list[float],
    market_returns: np.ndarray | list[float],
    risk_free_rate: float = 0.0,
    ann_factor: int = 365,
) -> JensensAlphaResult:
    """Compute Jensen's Alpha via OLS regression of excess returns on market excess returns.

    Jensen's Alpha = R_s - [R_f + beta * (R_m - R_f)]
    Estimated as the intercept of: (R_s - R_f) = alpha + beta * (R_m - R_f) + epsilon

    Args:
        strategy_returns: Daily fractional returns of the strategy.
        market_returns: Daily fractional returns of the market benchmark.
        risk_free_rate: Daily risk-free rate (default 0).
        ann_factor: Annualisation factor.

    Returns:
        JensensAlphaResult with alpha, beta, and statistical tests.
    """
    rs = np.asarray(strategy_returns, dtype=np.float64)
    rm = np.asarray(market_returns, dtype=np.float64)
    n = min(len(rs), len(rm))

    if n < 10:
        return JensensAlphaResult(
            alpha_daily=0.0, alpha_annualised=0.0, beta=0.0,
            r_squared=0.0, alpha_t_stat=0.0, alpha_p_value=1.0,
            beta_t_stat=0.0, beta_p_value=1.0, n_observations=n,
        )

    rs = rs[:n]
    rm = rm[:n]

    # Excess returns
    xs = rs - risk_free_rate
    xm = rm - risk_free_rate

    # OLS: xs = alpha + beta * xm + eps
    X = np.column_stack([np.ones(n), xm])
    coeffs, residuals, rank, sv = np.linalg.lstsq(X, xs, rcond=None)
    alpha = float(coeffs[0])
    beta = float(coeffs[1])

    # Predictions and residuals
    fitted = X @ coeffs
    eps = xs - fitted

    # R-squared
    ss_res = float(np.sum(eps**2))
    ss_tot = float(np.sum((xs - np.mean(xs))**2))
    r_sq = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Standard errors (OLS)
    mse = ss_res / (n - 2) if n > 2 else 0.0
    XtX_inv = np.linalg.inv(X.T @ X) if rank == 2 else np.zeros((2, 2))
    se = np.sqrt(np.diag(XtX_inv) * mse)

    se_alpha = float(se[0]) if se[0] > 0 else 1e-12
    se_beta = float(se[1]) if se[1] > 0 else 1e-12

    t_alpha = alpha / se_alpha
    t_beta = beta / se_beta
    p_alpha = float(2.0 * sp_stats.t.sf(abs(t_alpha), df=n - 2))
    p_beta = float(2.0 * sp_stats.t.sf(abs(t_beta), df=n - 2))

    alpha_ann = alpha * ann_factor

    return JensensAlphaResult(
        alpha_daily=round(alpha, 8),
        alpha_annualised=round(alpha_ann, 6),
        beta=round(beta, 6),
        r_squared=round(r_sq, 6),
        alpha_t_stat=round(t_alpha, 4),
        alpha_p_value=round(p_alpha, 6),
        beta_t_stat=round(t_beta, 4),
        beta_p_value=round(p_beta, 6),
        n_observations=n,
    )


def rolling_beta(
    strategy_returns: np.ndarray | list[float],
    market_returns: np.ndarray | list[float],
    window: int = 60,
    dates: list[str] | None = None,
) -> RollingBetaResult:
    """Compute rolling beta over a sliding window.

    Useful for monitoring how market exposure evolves over time —
    a market-neutral strategy should maintain beta near zero.

    Args:
        strategy_returns: Daily fractional returns of the strategy.
        market_returns: Daily fractional returns of the market benchmark.
        window: Rolling window size in days.
        dates: Optional date labels aligned to returns.

    Returns:
        RollingBetaResult with time series of betas and summary stats.
    """
    rs = np.asarray(strategy_returns, dtype=np.float64)
    rm = np.asarray(market_returns, dtype=np.float64)
    n = min(len(rs), len(rm))
    rs = rs[:n]
    rm = rm[:n]

    if n < window:
        return RollingBetaResult(
            dates=[], betas=[], window_size=window,
            mean_beta=0.0, std_beta=0.0, min_beta=0.0, max_beta=0.0,
        )

    betas: list[float] = []
    date_labels: list[str] = []

    for i in range(window, n + 1):
        rs_win = rs[i - window:i]
        rm_win = rm[i - window:i]

        var_m = float(np.var(rm_win, ddof=1))
        if var_m > 0:
            cov = float(np.cov(rs_win, rm_win, ddof=1)[0, 1])
            b = cov / var_m
        else:
            b = 0.0

        betas.append(round(b, 6))
        if dates and i - 1 < len(dates):
            date_labels.append(dates[i - 1])
        else:
            date_labels.append(f"t+{i}")

    beta_arr = np.array(betas)
    return RollingBetaResult(
        dates=date_labels,
        betas=betas,
        window_size=window,
        mean_beta=round(float(np.mean(beta_arr)), 6),
        std_beta=round(float(np.std(beta_arr, ddof=1)), 6) if len(betas) > 1 else 0.0,
        min_beta=round(float(np.min(beta_arr)), 6),
        max_beta=round(float(np.max(beta_arr)), 6),
    )


def multi_factor_regression(
    strategy_returns: np.ndarray | list[float],
    factor_returns: dict[str, np.ndarray | list[float]],
    model_name: str = "custom",
    ann_factor: int = 365,
) -> MultiFactorResult:
    """Run a multi-factor regression to decompose strategy returns.

    R_s = alpha + beta_1*F_1 + beta_2*F_2 + ... + beta_k*F_k + epsilon

    This is the workhorse for both Fama-French and crypto factor models.

    Args:
        strategy_returns: Daily fractional strategy returns.
        factor_returns: Dict mapping factor name to its return series.
        model_name: Label for the model.
        ann_factor: Annualisation factor.

    Returns:
        MultiFactorResult with alpha, factor exposures, and diagnostics.
    """
    rs = np.asarray(strategy_returns, dtype=np.float64)

    if not factor_returns:
        return _empty_multi_factor(model_name)

    # Align all series to minimum common length
    factor_names = list(factor_returns.keys())
    factor_arrays = [np.asarray(factor_returns[f], dtype=np.float64) for f in factor_names]
    n = min(len(rs), *(len(f) for f in factor_arrays))
    k = len(factor_names)

    if n < k + 10:
        return _empty_multi_factor(model_name)

    rs = rs[:n]
    F = np.column_stack([f[:n] for f in factor_arrays])

    # OLS with intercept
    X = np.column_stack([np.ones(n), F])
    coeffs, _, rank, _ = np.linalg.lstsq(X, rs, rcond=None)

    alpha = float(coeffs[0])
    betas = coeffs[1:]

    # Residuals
    fitted = X @ coeffs
    eps = rs - fitted
    ss_res = float(np.sum(eps**2))
    ss_tot = float(np.sum((rs - np.mean(rs))**2))
    r_sq = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    adj_r_sq = 1.0 - (1.0 - r_sq) * (n - 1) / (n - k - 1) if n > k + 1 else r_sq

    # Residual volatility
    resid_vol = float(np.std(eps, ddof=k + 1)) * math.sqrt(ann_factor)

    # Standard errors
    mse = ss_res / (n - k - 1) if n > k + 1 else 0.0
    try:
        XtX_inv = np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        XtX_inv = np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.maximum(np.diag(XtX_inv) * mse, 0.0))

    # Factor contribution: beta_j * mean(F_j) * ann_factor
    mean_strategy = float(np.mean(rs)) * ann_factor
    factor_exposures: list[FactorExposure] = []

    for j, fname in enumerate(factor_names):
        b = float(betas[j])
        se_j = float(se[j + 1]) if j + 1 < len(se) and se[j + 1] > 0 else 1e-12
        t_j = b / se_j
        p_j = float(2.0 * sp_stats.t.sf(abs(t_j), df=n - k - 1))

        # Contribution of this factor to total return
        factor_mean = float(np.mean(F[:, j]))
        contrib_ann = b * factor_mean * ann_factor
        contrib_pct = (contrib_ann / mean_strategy * 100.0) if mean_strategy != 0 else 0.0

        factor_exposures.append(FactorExposure(
            factor_name=fname,
            beta=round(b, 6),
            t_stat=round(t_j, 4),
            p_value=round(p_j, 6),
            contribution_pct=round(contrib_pct, 2),
        ))

    # Alpha stats
    se_alpha = float(se[0]) if se[0] > 0 else 1e-12
    t_alpha = alpha / se_alpha
    p_alpha = float(2.0 * sp_stats.t.sf(abs(t_alpha), df=n - k - 1))

    return MultiFactorResult(
        model_name=model_name,
        alpha_daily=round(alpha, 8),
        alpha_annualised=round(alpha * ann_factor, 6),
        alpha_t_stat=round(t_alpha, 4),
        alpha_p_value=round(p_alpha, 6),
        r_squared=round(r_sq, 6),
        adjusted_r_squared=round(adj_r_sq, 6),
        factors=factor_exposures,
        residual_vol_annualised=round(resid_vol, 6),
        n_observations=n,
    )


def fama_french_3factor(
    strategy_returns: np.ndarray | list[float],
    market_returns: np.ndarray | list[float],
    smb_returns: np.ndarray | list[float],
    hml_returns: np.ndarray | list[float],
    ann_factor: int = 365,
) -> MultiFactorResult:
    """Fama-French 3-factor model: Market, Size (SMB), Value (HML).

    For crypto, SMB can be proxied by small-cap vs large-cap token returns,
    and HML by fundamental value metrics.

    Args:
        strategy_returns: Daily strategy returns.
        market_returns: Market excess return (e.g., total crypto market).
        smb_returns: Small-Minus-Big factor returns.
        hml_returns: High-Minus-Low factor returns.
        ann_factor: Annualisation factor.

    Returns:
        MultiFactorResult with alpha and factor loadings.
    """
    factors = {
        "MKT": market_returns,
        "SMB": smb_returns,
        "HML": hml_returns,
    }
    return multi_factor_regression(
        strategy_returns, factors, model_name="fama_french_3f", ann_factor=ann_factor,
    )


def crypto_factor_model(
    strategy_returns: np.ndarray | list[float],
    btc_returns: np.ndarray | list[float],
    eth_returns: np.ndarray | list[float],
    defi_returns: np.ndarray | list[float] | None = None,
    momentum_returns: np.ndarray | list[float] | None = None,
    ann_factor: int = 365,
) -> MultiFactorResult:
    """Crypto-specific multi-factor model.

    Factors:
    - BTC beta: Exposure to Bitcoin (the dominant systematic factor)
    - ETH beta: Incremental exposure to Ethereum beyond BTC
    - DeFi factor: Exposure to DeFi vs CeFi divergence
    - Momentum factor: Cross-sectional momentum (top-minus-bottom quintile)

    Args:
        strategy_returns: Daily strategy returns.
        btc_returns: BTC daily returns.
        eth_returns: ETH daily returns (residualised against BTC internally).
        defi_returns: DeFi factor returns (optional).
        momentum_returns: Momentum factor returns (optional).
        ann_factor: Annualisation factor.

    Returns:
        MultiFactorResult with crypto factor loadings.
    """
    btc = np.asarray(btc_returns, dtype=np.float64)
    eth = np.asarray(eth_returns, dtype=np.float64)

    # Orthogonalise ETH against BTC to avoid multicollinearity
    n = min(len(btc), len(eth))
    btc_t = btc[:n]
    eth_t = eth[:n]
    var_btc = float(np.var(btc_t, ddof=1))
    if var_btc > 0:
        eth_beta_on_btc = float(np.cov(eth_t, btc_t, ddof=1)[0, 1]) / var_btc
        eth_resid = eth_t - eth_beta_on_btc * btc_t
    else:
        eth_resid = eth_t

    factors: dict[str, np.ndarray | list[float]] = {
        "BTC": btc_t,
        "ETH_resid": eth_resid,
    }

    if defi_returns is not None:
        factors["DeFi"] = defi_returns
    if momentum_returns is not None:
        factors["Momentum"] = momentum_returns

    return multi_factor_regression(
        strategy_returns, factors, model_name="crypto_4f", ann_factor=ann_factor,
    )


def information_coefficient_analysis(
    signal_values: np.ndarray | list[float],
    forward_returns: np.ndarray | list[float],
) -> ICAnalysisResult:
    """Compute the Information Coefficient (IC) — the rank correlation between
    signal predictions and subsequent realised returns.

    IC is the gold standard for evaluating signal quality:
    - IC > 0.05 is considered useful
    - IC > 0.10 is very strong
    - IC IR > 0.5 is publishable

    Args:
        signal_values: Predicted signal values (e.g., alpha scores).
        forward_returns: Realised forward returns corresponding to each signal.

    Returns:
        ICAnalysisResult with IC statistics.
    """
    signals = np.asarray(signal_values, dtype=np.float64)
    returns = np.asarray(forward_returns, dtype=np.float64)
    n = min(len(signals), len(returns))

    if n < 10:
        return ICAnalysisResult(
            mean_ic=0.0, std_ic=0.0, ic_ir=0.0,
            t_stat=0.0, p_value=1.0, hit_rate=0.0,
            ic_series=[], n_periods=0,
        )

    signals = signals[:n]
    returns = returns[:n]

    # Compute rolling IC in non-overlapping windows for time-series IC
    window = max(20, n // 20)
    ic_series: list[float] = []

    for start in range(0, n - window + 1, window):
        end = start + window
        s_win = signals[start:end]
        r_win = returns[start:end]
        # Spearman rank correlation
        if np.std(s_win) > 0 and np.std(r_win) > 0:
            rho, _ = sp_stats.spearmanr(s_win, r_win)
            ic_series.append(float(rho))

    if not ic_series:
        # Fall back to single IC
        rho, p = sp_stats.spearmanr(signals, returns)
        return ICAnalysisResult(
            mean_ic=round(float(rho), 6),
            std_ic=0.0,
            ic_ir=0.0,
            t_stat=0.0,
            p_value=round(float(p), 6),
            hit_rate=1.0 if rho > 0 else 0.0,
            ic_series=[round(float(rho), 6)],
            n_periods=1,
        )

    ic_arr = np.array(ic_series)
    mean_ic = float(np.mean(ic_arr))
    std_ic = float(np.std(ic_arr, ddof=1)) if len(ic_arr) > 1 else 0.0
    ic_ir = mean_ic / std_ic if std_ic > 0 else 0.0

    # t-test for mean IC != 0
    n_periods = len(ic_arr)
    t_stat = mean_ic / (std_ic / math.sqrt(n_periods)) if std_ic > 0 else 0.0
    p_value = float(2.0 * sp_stats.t.sf(abs(t_stat), df=n_periods - 1)) if n_periods > 1 else 1.0

    hit_rate = float(np.mean(ic_arr > 0))

    return ICAnalysisResult(
        mean_ic=round(mean_ic, 6),
        std_ic=round(std_ic, 6),
        ic_ir=round(ic_ir, 6),
        t_stat=round(t_stat, 4),
        p_value=round(p_value, 6),
        hit_rate=round(hit_rate, 4),
        ic_series=[round(float(x), 6) for x in ic_arr],
        n_periods=n_periods,
    )


def compute_factor_contribution(
    strategy_returns: np.ndarray | list[float],
    factor_result: MultiFactorResult,
    factor_returns: dict[str, np.ndarray | list[float]],
    ann_factor: int = 365,
) -> FactorContribution:
    """Decompose total return into factor contributions.

    Computes how much of the total return came from each factor exposure
    vs genuine alpha. Critical for understanding whether "alpha" is really
    just disguised beta.

    Args:
        strategy_returns: Daily strategy returns.
        factor_result: Output from a multi_factor_regression call.
        factor_returns: Dict of factor return arrays (same as used in regression).
        ann_factor: Annualisation factor.

    Returns:
        FactorContribution with percentage attribution.
    """
    rs = np.asarray(strategy_returns, dtype=np.float64)
    n = len(rs)
    total_return = float(np.prod(1.0 + rs) - 1.0) * 100.0

    # Alpha contribution
    alpha_contrib = factor_result.alpha_daily * n * 100.0

    # Factor contributions
    factor_contribs: dict[str, float] = {}
    for fe in factor_result.factors:
        fname = fe.factor_name
        if fname in factor_returns:
            f_arr = np.asarray(factor_returns[fname], dtype=np.float64)[:n]
            contrib = fe.beta * float(np.sum(f_arr)) * 100.0
            factor_contribs[fname] = round(contrib, 4)
        else:
            factor_contribs[fname] = 0.0

    # Residual
    explained = alpha_contrib + sum(factor_contribs.values())
    residual = total_return - explained

    return FactorContribution(
        total_return_pct=round(total_return, 4),
        alpha_contribution_pct=round(alpha_contrib, 4),
        factor_contributions=factor_contribs,
        residual_pct=round(residual, 4),
    )


def run_alpha_beta_report(
    strategy_returns: np.ndarray | list[float],
    btc_returns: np.ndarray | list[float],
    eth_returns: np.ndarray | list[float] | None = None,
    defi_returns: np.ndarray | list[float] | None = None,
    momentum_returns: np.ndarray | list[float] | None = None,
    dates: list[str] | None = None,
    rolling_window: int = 60,
    ann_factor: int = 365,
) -> AlphaBetaReport:
    """Run a comprehensive alpha/beta analysis.

    Args:
        strategy_returns: Daily strategy returns.
        btc_returns: BTC daily returns (primary market benchmark).
        eth_returns: ETH daily returns (optional, for crypto factor model).
        defi_returns: DeFi factor returns (optional).
        momentum_returns: Momentum factor returns (optional).
        dates: Date labels for rolling beta.
        rolling_window: Window size for rolling beta.
        ann_factor: Annualisation factor.

    Returns:
        AlphaBetaReport with all analyses.
    """
    rs = np.asarray(strategy_returns, dtype=np.float64)
    btc = np.asarray(btc_returns, dtype=np.float64)

    # Jensen's Alpha (using BTC as the market)
    ja = jensens_alpha(rs, btc, ann_factor=ann_factor)

    # Rolling beta
    rb = rolling_beta(rs, btc, window=rolling_window, dates=dates)

    # Crypto factor model (if ETH provided)
    cf = None
    if eth_returns is not None:
        cf = crypto_factor_model(
            rs, btc, eth_returns,
            defi_returns=defi_returns,
            momentum_returns=momentum_returns,
            ann_factor=ann_factor,
        )

    return AlphaBetaReport(
        jensens_alpha=ja,
        rolling_beta=rb,
        crypto_factors=cf,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _empty_multi_factor(model_name: str) -> MultiFactorResult:
    return MultiFactorResult(
        model_name=model_name,
        alpha_daily=0.0,
        alpha_annualised=0.0,
        alpha_t_stat=0.0,
        alpha_p_value=1.0,
        r_squared=0.0,
        adjusted_r_squared=0.0,
        factors=[],
        residual_vol_annualised=0.0,
        n_observations=0,
    )
