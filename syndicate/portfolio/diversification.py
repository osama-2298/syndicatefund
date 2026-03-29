"""
Diversification Analyzer — Concentration, Risk Parity & Correlation Analysis.

Institutional-grade diversification metrics:
- Herfindahl-Hirschman Index (HHI) for concentration
- Effective number of positions (1/HHI)
- Diversification ratio (portfolio vol vs weighted component vols)
- Marginal risk contribution per position
- Risk parity optimization
- Full correlation matrix with heatmap-ready output
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════
#  Models
# ═══════════════════════════════════════════


class ConcentrationMetrics(BaseModel):
    """Portfolio concentration measurements."""
    herfindahl_index: float = Field(
        ge=0.0, le=1.0,
        description="HHI: sum of squared weights. 0 = perfectly diversified, 1 = single position",
    )
    effective_positions: float = Field(
        ge=0.0,
        description="1/HHI: effective number of independent bets",
    )
    top_1_weight: float
    top_5_weight: float
    top_10_weight: float
    gini_coefficient: float = Field(
        ge=0.0, le=1.0,
        description="Gini: 0 = equal weights, 1 = one position holds everything",
    )


class RiskContribution(BaseModel):
    """Risk contribution breakdown for a single position."""
    symbol: str
    weight: float
    volatility: float  # annualized
    marginal_contribution: float  # dSigma/dWeight
    component_risk: float  # weight * marginal_contribution
    pct_of_total_risk: float  # component_risk / portfolio_vol


class DiversificationReport(BaseModel):
    """Full diversification analysis report."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    num_positions: int
    concentration: ConcentrationMetrics
    diversification_ratio: float = Field(
        ge=0.0,
        description="Sum of weighted vols / portfolio vol. >1 means diversification benefit",
    )
    portfolio_volatility: float  # annualized
    weighted_avg_volatility: float  # weighted sum of component vols
    risk_contributions: list[RiskContribution] = Field(default_factory=list)
    risk_parity_weights: dict[str, float] = Field(
        default_factory=dict,
        description="Weights that equalize risk contribution across positions",
    )
    correlation_summary: dict[str, Any] = Field(default_factory=dict)


# ═══════════════════════════════════════════
#  Diversification Analyzer
# ═══════════════════════════════════════════


class DiversificationAnalyzer:
    """
    Analyzes portfolio diversification using modern portfolio theory concepts.

    Takes position weights and a return history (or covariance matrix)
    to compute concentration, risk contribution, and diversification metrics.
    """

    def __init__(self, annualization_factor: float = 252.0) -> None:
        """
        Args:
            annualization_factor: Trading days per year for annualizing volatility.
                Use 252 for equities/crypto daily data, 365 for 24/7 crypto.
        """
        self.annualization_factor = annualization_factor

    # ── Herfindahl Index ────────────────────

    def herfindahl_index(self, weights: dict[str, float]) -> ConcentrationMetrics:
        """
        Compute the Herfindahl-Hirschman Index and related concentration metrics.

        HHI = sum(w_i^2) where w_i are portfolio weights.
        - 1/N (equal weight) is the minimum for N positions
        - 1.0 means 100% in a single position
        - Effective positions = 1/HHI

        Also computes Gini coefficient for weight inequality.

        Args:
            weights: symbol -> portfolio weight (should sum to ~1.0).

        Returns:
            ConcentrationMetrics with HHI, effective positions, top-N, and Gini.
        """
        if not weights:
            return ConcentrationMetrics(
                herfindahl_index=0.0,
                effective_positions=0.0,
                top_1_weight=0.0,
                top_5_weight=0.0,
                top_10_weight=0.0,
                gini_coefficient=0.0,
            )

        w = np.array(list(weights.values()))
        w = np.abs(w)  # handle short positions

        # Normalize to sum to 1
        total = w.sum()
        if total > 0:
            w = w / total

        hhi = float(np.sum(w ** 2))
        eff_pos = 1.0 / max(hhi, 1e-10)

        # Top N weights
        sorted_w = np.sort(w)[::-1]
        top_1 = float(sorted_w[0]) if len(sorted_w) >= 1 else 0.0
        top_5 = float(sorted_w[:5].sum()) if len(sorted_w) >= 1 else 0.0
        top_10 = float(sorted_w[:10].sum()) if len(sorted_w) >= 1 else 0.0

        # Gini coefficient
        n = len(w)
        if n <= 1:
            gini = 0.0
        else:
            sorted_w_gini = np.sort(w)
            index = np.arange(1, n + 1)
            gini = float((2 * np.sum(index * sorted_w_gini) - (n + 1) * np.sum(sorted_w_gini))
                         / (n * np.sum(sorted_w_gini))) if np.sum(sorted_w_gini) > 0 else 0.0

        return ConcentrationMetrics(
            herfindahl_index=round(hhi, 6),
            effective_positions=round(eff_pos, 2),
            top_1_weight=round(top_1, 4),
            top_5_weight=round(top_5, 4),
            top_10_weight=round(top_10, 4),
            gini_coefficient=round(max(gini, 0.0), 4),
        )

    # ── Effective Positions ─────────────────

    def effective_positions(self, weights: dict[str, float]) -> float:
        """
        Shortcut: returns 1/HHI — the effective number of independent bets.

        An equally-weighted portfolio of N stocks has effective_positions = N.
        A portfolio with 90% in one stock has effective_positions ~ 1.2.
        """
        metrics = self.herfindahl_index(weights)
        return metrics.effective_positions

    # ── Diversification Ratio ───────────────

    def diversification_ratio(
        self,
        weights: dict[str, float],
        covariance_matrix: np.ndarray,
        symbols: list[str],
    ) -> float:
        """
        Compute the diversification ratio: DR = (w' * sigma) / sqrt(w' * Cov * w)

        Where:
        - w' * sigma = weighted sum of individual volatilities
        - sqrt(w' * Cov * w) = portfolio volatility

        DR > 1 indicates diversification benefit (correlations < 1).
        DR = 1 means all assets are perfectly correlated (no benefit).

        Args:
            weights: symbol -> weight.
            covariance_matrix: NxN annualized covariance matrix.
            symbols: Ordered list of symbols matching matrix rows/cols.

        Returns:
            Diversification ratio (>= 1.0 is normal).
        """
        w = self._weights_to_array(weights, symbols)
        cov = np.array(covariance_matrix)

        # Individual volatilities (sqrt of diagonal)
        vols = np.sqrt(np.diag(cov))

        # Weighted sum of vols
        weighted_vol_sum = float(np.dot(np.abs(w), vols))

        # Portfolio volatility
        port_var = float(w @ cov @ w)
        port_vol = np.sqrt(max(port_var, 0.0))

        if port_vol < 1e-10:
            return 1.0

        return round(weighted_vol_sum / port_vol, 4)

    # ── Risk Contribution ───────────────────

    def risk_contribution(
        self,
        weights: dict[str, float],
        covariance_matrix: np.ndarray,
        symbols: list[str],
    ) -> list[RiskContribution]:
        """
        Compute marginal and component risk contribution per position.

        Marginal risk contribution (MRC): dSigma_p / dw_i = (Cov * w)_i / sigma_p
        Component risk contribution (CRC): w_i * MRC_i
        Sum of CRC = portfolio volatility (Euler decomposition)

        Args:
            weights: symbol -> weight.
            covariance_matrix: NxN annualized covariance matrix.
            symbols: Ordered list of symbols matching matrix rows/cols.

        Returns:
            List of RiskContribution, sorted by pct_of_total_risk descending.
        """
        w = self._weights_to_array(weights, symbols)
        cov = np.array(covariance_matrix)
        vols = np.sqrt(np.diag(cov))

        # Portfolio variance and volatility
        port_var = float(w @ cov @ w)
        port_vol = np.sqrt(max(port_var, 1e-20))

        # Marginal risk contribution: (Cov * w) / sigma_p
        cov_w = cov @ w
        mrc = cov_w / port_vol

        # Component risk contribution: w_i * MRC_i
        crc = w * mrc

        results: list[RiskContribution] = []
        for i, sym in enumerate(symbols):
            pct_risk = float(crc[i]) / port_vol if port_vol > 1e-10 else 0.0
            results.append(RiskContribution(
                symbol=sym,
                weight=round(float(w[i]), 6),
                volatility=round(float(vols[i]), 6),
                marginal_contribution=round(float(mrc[i]), 6),
                component_risk=round(float(crc[i]), 6),
                pct_of_total_risk=round(pct_risk, 4),
            ))

        results.sort(key=lambda r: abs(r.pct_of_total_risk), reverse=True)
        return results

    # ── Risk Parity Weights ─────────────────

    def risk_parity_weights(
        self,
        covariance_matrix: np.ndarray,
        symbols: list[str],
        max_iterations: int = 1000,
        tolerance: float = 1e-8,
    ) -> dict[str, float]:
        """
        Compute risk parity (equal risk contribution) weights.

        Uses iterative reweighting: w_i proportional to 1/MRC_i,
        normalized to sum to 1. Converges to the point where
        each position contributes equally to portfolio risk.

        This is the "inverse volatility" approach extended to
        account for correlations.

        Args:
            covariance_matrix: NxN annualized covariance matrix.
            symbols: Ordered list of symbols.
            max_iterations: Max iterations for convergence.
            tolerance: Convergence threshold.

        Returns:
            Dict of symbol -> risk parity weight.
        """
        n = len(symbols)
        cov = np.array(covariance_matrix)

        # Initialize with inverse-volatility weights
        vols = np.sqrt(np.diag(cov))
        inv_vol = 1.0 / np.maximum(vols, 1e-10)
        w = inv_vol / inv_vol.sum()

        for iteration in range(max_iterations):
            # Portfolio risk
            port_var = w @ cov @ w
            port_vol = np.sqrt(max(port_var, 1e-20))

            # Marginal risk contributions
            cov_w = cov @ w
            mrc = cov_w / port_vol

            # Component risk contributions
            crc = w * mrc

            # Target: equal risk contribution = port_vol / n
            target_rc = port_vol / n

            # Update weights: increase weight where risk contribution is below target
            # w_new proportional to w * target_rc / crc
            crc_safe = np.maximum(np.abs(crc), 1e-20)
            w_new = w * target_rc / crc_safe
            w_new = np.maximum(w_new, 0.0)  # no short positions
            w_new = w_new / w_new.sum()

            # Check convergence
            if np.max(np.abs(w_new - w)) < tolerance:
                w = w_new
                break
            w = w_new

        return {sym: round(float(w[i]), 6) for i, sym in enumerate(symbols)}

    # ── Correlation Matrix ──────────────────

    def correlation_matrix(
        self,
        returns: dict[str, list[float]],
        symbols: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Compute the full NxN correlation matrix with heatmap-ready output.

        Args:
            returns: symbol -> list of periodic returns (same length for all).
            symbols: Order of symbols. If None, uses sorted keys.

        Returns:
            Dict with:
            - 'symbols': ordered list of symbols
            - 'matrix': NxN correlation matrix as list-of-lists
            - 'covariance_matrix': NxN covariance matrix (annualized)
            - 'heatmap_data': list of {row, col, symbol_row, symbol_col, correlation}
            - 'avg_correlation': average off-diagonal correlation
            - 'max_correlation': max off-diagonal correlation (with pair)
            - 'min_correlation': min off-diagonal correlation (with pair)
            - 'highly_correlated_pairs': pairs with |corr| > 0.7
        """
        if symbols is None:
            symbols = sorted(returns.keys())

        n = len(symbols)
        if n == 0:
            return {
                "symbols": [],
                "matrix": [],
                "covariance_matrix": [],
                "heatmap_data": [],
                "avg_correlation": 0.0,
                "max_correlation": {"value": 0.0, "pair": []},
                "min_correlation": {"value": 0.0, "pair": []},
                "highly_correlated_pairs": [],
            }

        # Build return matrix: each row is a symbol's return series
        min_len = min(len(returns[s]) for s in symbols)
        return_matrix = np.array([returns[s][:min_len] for s in symbols])

        # Covariance and correlation
        cov_matrix = np.cov(return_matrix) * self.annualization_factor
        # Handle single-asset edge case
        if n == 1:
            cov_matrix = cov_matrix.reshape(1, 1)

        std_devs = np.sqrt(np.diag(cov_matrix))
        std_outer = np.outer(std_devs, std_devs)
        std_outer = np.maximum(std_outer, 1e-20)
        corr_matrix = cov_matrix / std_outer
        np.fill_diagonal(corr_matrix, 1.0)  # ensure diagonal is exactly 1
        corr_matrix = np.clip(corr_matrix, -1.0, 1.0)

        # Heatmap data
        heatmap_data = []
        for i in range(n):
            for j in range(n):
                heatmap_data.append({
                    "row": i,
                    "col": j,
                    "symbol_row": symbols[i],
                    "symbol_col": symbols[j],
                    "correlation": round(float(corr_matrix[i, j]), 4),
                })

        # Off-diagonal statistics
        mask = ~np.eye(n, dtype=bool)
        off_diag = corr_matrix[mask] if n > 1 else np.array([])
        avg_corr = float(np.mean(off_diag)) if len(off_diag) > 0 else 0.0

        # Max and min off-diagonal
        max_corr_val = 0.0
        max_pair: list[str] = []
        min_corr_val = 0.0
        min_pair: list[str] = []
        highly_correlated: list[dict[str, Any]] = []

        if n > 1:
            # Find max/min off-diagonal
            for i in range(n):
                for j in range(i + 1, n):
                    val = float(corr_matrix[i, j])
                    if max_pair == [] or val > max_corr_val:
                        max_corr_val = val
                        max_pair = [symbols[i], symbols[j]]
                    if min_pair == [] or val < min_corr_val:
                        min_corr_val = val
                        min_pair = [symbols[i], symbols[j]]
                    if abs(val) > 0.7:
                        highly_correlated.append({
                            "pair": [symbols[i], symbols[j]],
                            "correlation": round(val, 4),
                        })

        highly_correlated.sort(key=lambda x: abs(x["correlation"]), reverse=True)

        return {
            "symbols": symbols,
            "matrix": [[round(float(corr_matrix[i, j]), 4) for j in range(n)] for i in range(n)],
            "covariance_matrix": [[round(float(cov_matrix[i, j]), 8) for j in range(n)] for i in range(n)],
            "heatmap_data": heatmap_data,
            "avg_correlation": round(avg_corr, 4),
            "max_correlation": {"value": round(max_corr_val, 4), "pair": max_pair},
            "min_correlation": {"value": round(min_corr_val, 4), "pair": min_pair},
            "highly_correlated_pairs": highly_correlated,
        }

    # ── Full Report ─────────────────────────

    def full_report(
        self,
        weights: dict[str, float],
        returns: dict[str, list[float]],
        symbols: list[str] | None = None,
    ) -> DiversificationReport:
        """
        Generate a complete diversification analysis.

        Args:
            weights: symbol -> portfolio weight.
            returns: symbol -> list of periodic returns.
            symbols: Order of symbols. If None, uses intersection of weights and returns.

        Returns:
            DiversificationReport with all metrics.
        """
        if symbols is None:
            symbols = sorted(set(weights.keys()) & set(returns.keys()))

        if not symbols:
            return DiversificationReport(
                num_positions=0,
                concentration=self.herfindahl_index({}),
                diversification_ratio=1.0,
                portfolio_volatility=0.0,
                weighted_avg_volatility=0.0,
            )

        # Compute correlation and covariance
        corr_data = self.correlation_matrix(returns, symbols)
        cov_matrix = np.array(corr_data["covariance_matrix"])

        # Concentration
        concentration = self.herfindahl_index(weights)

        # Diversification ratio
        div_ratio = self.diversification_ratio(weights, cov_matrix, symbols)

        # Risk contributions
        risk_contribs = self.risk_contribution(weights, cov_matrix, symbols)

        # Portfolio volatility
        w = self._weights_to_array(weights, symbols)
        port_var = float(w @ cov_matrix @ w)
        port_vol = float(np.sqrt(max(port_var, 0.0)))

        # Weighted average volatility
        vols = np.sqrt(np.diag(cov_matrix))
        weighted_avg_vol = float(np.dot(np.abs(w), vols))

        # Risk parity weights
        rp_weights = self.risk_parity_weights(cov_matrix, symbols)

        return DiversificationReport(
            num_positions=len(symbols),
            concentration=concentration,
            diversification_ratio=div_ratio,
            portfolio_volatility=round(port_vol, 6),
            weighted_avg_volatility=round(weighted_avg_vol, 6),
            risk_contributions=risk_contribs,
            risk_parity_weights=rp_weights,
            correlation_summary={
                "avg_correlation": corr_data["avg_correlation"],
                "max_correlation": corr_data["max_correlation"],
                "min_correlation": corr_data["min_correlation"],
                "highly_correlated_pairs": corr_data["highly_correlated_pairs"],
            },
        )

    # ── Internal Helpers ────────────────────

    @staticmethod
    def _weights_to_array(weights: dict[str, float], symbols: list[str]) -> np.ndarray:
        """Convert weight dict to numpy array in symbol order."""
        return np.array([weights.get(s, 0.0) for s in symbols])
