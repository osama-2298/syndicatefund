"""
Performance Attribution — Position, Sector, Factor & Timing Decomposition.

Institutional-grade performance attribution that answers:
- WHERE did returns come from? (position attribution)
- WHY? Allocation vs selection vs interaction (Brinson-Fachler)
- WHEN? Entry timing vs holding vs exit timing
- WHAT FACTORS drove returns? (factor attribution)
- WHO generated the alpha? (team attribution)
- HOW LONG? Returns by holding duration bucket
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════
#  Models
# ═══════════════════════════════════════════


class PositionAttribution(BaseModel):
    """P&L contribution of a single position."""
    symbol: str
    entry_price: float
    exit_price: float | None = None  # None if still open
    current_price: float
    quantity: float
    side: str  # "BUY" or "SELL"
    pnl: float  # dollar P&L
    pnl_pct: float  # return percentage
    weight_at_entry: float  # portfolio weight when entered
    contribution_to_return: float  # pnl / portfolio_value
    sector: str = ""
    team: str = ""  # which team's signal originated this position


class SectorAttributionDetail(BaseModel):
    """Brinson-Fachler attribution for a single sector."""
    sector: str
    portfolio_weight: float
    benchmark_weight: float
    portfolio_return: float
    benchmark_return: float
    allocation_effect: float  # over/underweighting the sector
    selection_effect: float  # stock picking within the sector
    interaction_effect: float  # combined effect
    total_effect: float


class SectorAttributionReport(BaseModel):
    """Full Brinson-Fachler sector attribution."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    portfolio_return: float
    benchmark_return: float
    active_return: float  # portfolio - benchmark
    total_allocation_effect: float
    total_selection_effect: float
    total_interaction_effect: float
    sectors: list[SectorAttributionDetail] = Field(default_factory=list)


class TimingBreakdown(BaseModel):
    """Timing attribution for a single trade."""
    symbol: str
    total_return_pct: float
    entry_timing_pct: float  # return from entry timing vs VWAP
    holding_return_pct: float  # return during hold period
    exit_timing_pct: float  # return from exit timing vs VWAP
    holding_period_days: int
    entry_date: datetime
    exit_date: datetime | None = None


class FactorExposure(BaseModel):
    """Exposure and return attribution for a single factor."""
    factor_name: str
    factor_return: float  # the factor's return in the period
    portfolio_exposure: float  # beta or loading to this factor
    attributed_return: float  # exposure * factor_return
    pct_of_total_return: float


class FactorAttributionReport(BaseModel):
    """Return decomposition by risk factors."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_return: float
    factor_explained_return: float
    alpha: float  # residual / idiosyncratic return
    r_squared: float  # % of return variance explained by factors
    factors: list[FactorExposure] = Field(default_factory=list)


class TeamPerformance(BaseModel):
    """Performance metrics for a single team's signals."""
    team: str
    num_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_pnl_per_trade: float
    best_trade_pnl: float
    worst_trade_pnl: float
    sharpe_ratio: float
    contribution_to_portfolio_return: float


class HoldingPeriodBucket(BaseModel):
    """Returns aggregated by holding duration."""
    bucket_label: str  # e.g., "0-1d", "1-7d", "1-4w", "1-3m", "3m+"
    min_days: int
    max_days: int
    num_trades: int
    avg_return_pct: float
    median_return_pct: float
    total_pnl: float
    win_rate: float
    avg_holding_days: float


class AttributionReport(BaseModel):
    """Complete attribution report combining all dimensions."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    period_start: datetime
    period_end: datetime
    portfolio_return: float
    benchmark_return: float = 0.0
    active_return: float = 0.0
    position_attributions: list[PositionAttribution] = Field(default_factory=list)
    sector_attribution: SectorAttributionReport | None = None
    factor_attribution: FactorAttributionReport | None = None
    team_performances: list[TeamPerformance] = Field(default_factory=list)
    holding_period_buckets: list[HoldingPeriodBucket] = Field(default_factory=list)
    top_contributors: list[str] = Field(default_factory=list)
    top_detractors: list[str] = Field(default_factory=list)


# ═══════════════════════════════════════════
#  Performance Attribution
# ═══════════════════════════════════════════


class PerformanceAttribution:
    """
    Multi-dimensional performance attribution engine.

    Decomposes portfolio returns across positions, sectors, factors,
    teams, timing, and holding periods.
    """

    def __init__(self, annualization_factor: float = 252.0) -> None:
        self.annualization_factor = annualization_factor

    # ── Position Attribution ────────────────

    def position_attribution(
        self,
        trades: list[dict[str, Any]],
        portfolio_value: float,
    ) -> list[PositionAttribution]:
        """
        Compute P&L contribution by position.

        Each trade dict should have:
        - symbol (str)
        - entry_price (float)
        - current_price (float)
        - exit_price (float, optional)
        - quantity (float)
        - side (str): "BUY" or "SELL"
        - weight_at_entry (float): portfolio weight at entry
        - sector (str, optional)
        - team (str, optional)

        Returns:
            List of PositionAttribution sorted by contribution descending.
        """
        port_val = max(portfolio_value, 1.0)
        results: list[PositionAttribution] = []

        for trade in trades:
            entry = trade["entry_price"]
            current = trade["current_price"]
            exit_p = trade.get("exit_price")
            qty = trade["quantity"]
            side = trade["side"]
            ref_price = exit_p if exit_p is not None else current

            if side == "BUY":
                pnl = (ref_price - entry) * qty
                pnl_pct = (ref_price - entry) / entry if entry > 0 else 0.0
            else:  # SHORT/SELL
                pnl = (entry - ref_price) * qty
                pnl_pct = (entry - ref_price) / entry if entry > 0 else 0.0

            contribution = pnl / port_val

            results.append(PositionAttribution(
                symbol=trade["symbol"],
                entry_price=entry,
                exit_price=exit_p,
                current_price=current,
                quantity=qty,
                side=side,
                pnl=round(pnl, 2),
                pnl_pct=round(pnl_pct, 4),
                weight_at_entry=trade.get("weight_at_entry", 0.0),
                contribution_to_return=round(contribution, 6),
                sector=trade.get("sector", ""),
                team=trade.get("team", ""),
            ))

        results.sort(key=lambda r: r.contribution_to_return, reverse=True)
        return results

    # ── Sector Attribution (Brinson-Fachler) ─

    def sector_attribution(
        self,
        portfolio_sectors: dict[str, dict[str, float]],
        benchmark_sectors: dict[str, dict[str, float]],
    ) -> SectorAttributionReport:
        """
        Brinson-Fachler sector attribution model.

        Decomposes active return into:
        - Allocation effect: value from over/underweighting sectors
        - Selection effect: value from stock selection within sectors
        - Interaction effect: combined allocation + selection

        Args:
            portfolio_sectors: sector -> {"weight": w, "return": r}
            benchmark_sectors: sector -> {"weight": w, "return": r}

        Returns:
            SectorAttributionReport with full Brinson-Fachler decomposition.
        """
        all_sectors = set(portfolio_sectors.keys()) | set(benchmark_sectors.keys())

        # Portfolio and benchmark total returns
        port_return = sum(
            s["weight"] * s["return"]
            for s in portfolio_sectors.values()
        )
        bench_return = sum(
            s["weight"] * s["return"]
            for s in benchmark_sectors.values()
        )

        details: list[SectorAttributionDetail] = []
        total_alloc = 0.0
        total_select = 0.0
        total_interact = 0.0

        for sector in sorted(all_sectors):
            p = portfolio_sectors.get(sector, {"weight": 0.0, "return": 0.0})
            b = benchmark_sectors.get(sector, {"weight": 0.0, "return": 0.0})

            pw, pr = p["weight"], p["return"]
            bw, br = b["weight"], b["return"]

            # Brinson-Fachler decomposition
            allocation = (pw - bw) * (br - bench_return)
            selection = bw * (pr - br)
            interaction = (pw - bw) * (pr - br)
            total = allocation + selection + interaction

            total_alloc += allocation
            total_select += selection
            total_interact += interaction

            details.append(SectorAttributionDetail(
                sector=sector,
                portfolio_weight=round(pw, 4),
                benchmark_weight=round(bw, 4),
                portfolio_return=round(pr, 4),
                benchmark_return=round(br, 4),
                allocation_effect=round(allocation, 6),
                selection_effect=round(selection, 6),
                interaction_effect=round(interaction, 6),
                total_effect=round(total, 6),
            ))

        details.sort(key=lambda d: abs(d.total_effect), reverse=True)

        return SectorAttributionReport(
            portfolio_return=round(port_return, 6),
            benchmark_return=round(bench_return, 6),
            active_return=round(port_return - bench_return, 6),
            total_allocation_effect=round(total_alloc, 6),
            total_selection_effect=round(total_select, 6),
            total_interaction_effect=round(total_interact, 6),
            sectors=details,
        )

    # ── Timing Attribution ──────────────────

    def timing_attribution(
        self,
        trades: list[dict[str, Any]],
    ) -> list[TimingBreakdown]:
        """
        Decompose returns into entry timing, holding, and exit timing.

        Each trade dict should have:
        - symbol (str)
        - entry_price (float)
        - entry_date (datetime)
        - current_price (float)
        - exit_price (float, optional)
        - exit_date (datetime, optional)
        - side (str)
        - vwap_at_entry (float): VWAP around entry time (benchmark)
        - vwap_at_exit (float, optional): VWAP around exit time

        Entry timing: how much was gained/lost by entering at the
            actual price vs the period VWAP (positive = bought cheaper than VWAP).
        Holding return: the return from VWAP-to-VWAP (the unavoidable part).
        Exit timing: how much was gained/lost by exiting at the
            actual price vs the period VWAP.

        Returns:
            List of TimingBreakdown sorted by total_return_pct descending.
        """
        results: list[TimingBreakdown] = []

        for trade in trades:
            entry = trade["entry_price"]
            current = trade["current_price"]
            exit_p = trade.get("exit_price")
            side = trade.get("side", "BUY")
            vwap_entry = trade.get("vwap_at_entry", entry)
            vwap_exit = trade.get("vwap_at_exit", exit_p or current)
            ref_price = exit_p if exit_p is not None else current

            if entry <= 0 or vwap_entry <= 0:
                continue

            if side == "BUY":
                # Entry timing: bought cheaper than VWAP = positive
                entry_timing = (vwap_entry - entry) / entry
                # Holding: VWAP-to-VWAP return
                holding = (vwap_exit - vwap_entry) / vwap_entry if vwap_entry > 0 else 0.0
                # Exit timing: sold higher than VWAP = positive
                exit_timing = (ref_price - vwap_exit) / vwap_exit if vwap_exit > 0 else 0.0
                total = (ref_price - entry) / entry
            else:
                entry_timing = (entry - vwap_entry) / entry
                holding = (vwap_entry - vwap_exit) / vwap_entry if vwap_entry > 0 else 0.0
                exit_timing = (vwap_exit - ref_price) / vwap_exit if vwap_exit > 0 else 0.0
                total = (entry - ref_price) / entry

            entry_date = trade["entry_date"]
            exit_date = trade.get("exit_date")
            holding_days = (
                (exit_date - entry_date).days
                if exit_date
                else (datetime.now(timezone.utc) - entry_date).days
            )

            results.append(TimingBreakdown(
                symbol=trade["symbol"],
                total_return_pct=round(total, 4),
                entry_timing_pct=round(entry_timing, 4),
                holding_return_pct=round(holding, 4),
                exit_timing_pct=round(exit_timing, 4),
                holding_period_days=holding_days,
                entry_date=entry_date,
                exit_date=exit_date,
            ))

        results.sort(key=lambda r: r.total_return_pct, reverse=True)
        return results

    # ── Factor Attribution ──────────────────

    def factor_attribution(
        self,
        portfolio_returns: list[float],
        factor_returns: dict[str, list[float]],
    ) -> FactorAttributionReport:
        """
        Decompose portfolio returns by risk factors using linear regression.

        R_p = alpha + beta_1 * F_1 + beta_2 * F_2 + ... + epsilon

        Common factors for crypto:
        - Market (BTC return)
        - Size (small vs large cap)
        - Momentum (winners vs losers)
        - Volatility (high vs low vol)
        - DeFi yield

        Args:
            portfolio_returns: List of periodic portfolio returns.
            factor_returns: factor_name -> list of periodic returns (same length).

        Returns:
            FactorAttributionReport with exposures and attributed returns.
        """
        factor_names = list(factor_returns.keys())
        if not factor_names or len(portfolio_returns) < 3:
            return FactorAttributionReport(
                total_return=0.0,
                factor_explained_return=0.0,
                alpha=0.0,
                r_squared=0.0,
            )

        y = np.array(portfolio_returns)
        n = len(y)

        # Build factor matrix (with intercept)
        min_len = min(n, *(len(factor_returns[f]) for f in factor_names))
        y = y[:min_len]

        X = np.column_stack([
            np.array(factor_returns[f][:min_len]) for f in factor_names
        ])
        X_with_intercept = np.column_stack([np.ones(min_len), X])

        # OLS regression: beta = (X'X)^-1 X'y
        try:
            XtX = X_with_intercept.T @ X_with_intercept
            Xty = X_with_intercept.T @ y
            betas = np.linalg.solve(XtX, Xty)
        except np.linalg.LinAlgError:
            # Singular matrix — fall back to pseudo-inverse
            betas = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]

        alpha = float(betas[0])
        factor_betas = betas[1:]

        # Fitted values and R-squared
        y_hat = X_with_intercept @ betas
        ss_res = float(np.sum((y - y_hat) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = 1.0 - ss_res / max(ss_tot, 1e-20)
        r_squared = max(r_squared, 0.0)

        # Total return (cumulative)
        total_return = float(np.sum(y))

        # Factor-attributed returns
        factors: list[FactorExposure] = []
        factor_explained = 0.0

        for i, fname in enumerate(factor_names):
            f_ret = float(np.sum(factor_returns[fname][:min_len]))
            exposure = float(factor_betas[i])
            attributed = exposure * f_ret
            factor_explained += attributed

            pct_of_total = attributed / total_return if abs(total_return) > 1e-10 else 0.0

            factors.append(FactorExposure(
                factor_name=fname,
                factor_return=round(f_ret, 6),
                portfolio_exposure=round(exposure, 4),
                attributed_return=round(attributed, 6),
                pct_of_total_return=round(pct_of_total, 4),
            ))

        factors.sort(key=lambda f: abs(f.attributed_return), reverse=True)

        # Alpha is total return minus factor-explained
        residual_alpha = total_return - factor_explained

        return FactorAttributionReport(
            total_return=round(total_return, 6),
            factor_explained_return=round(factor_explained, 6),
            alpha=round(residual_alpha, 6),
            r_squared=round(r_squared, 4),
            factors=factors,
        )

    # ── Team Attribution ────────────────────

    def team_attribution(
        self,
        trades: list[dict[str, Any]],
        portfolio_value: float,
    ) -> list[TeamPerformance]:
        """
        Attribute P&L to the team whose signals originated each trade.

        Each trade dict should have:
        - team (str)
        - pnl (float)
        - pnl_pct (float)

        Returns:
            List of TeamPerformance sorted by total_pnl descending.
        """
        port_val = max(portfolio_value, 1.0)

        # Group trades by team
        by_team: dict[str, list[dict[str, Any]]] = {}
        for trade in trades:
            team = trade.get("team", "unknown")
            by_team.setdefault(team, []).append(trade)

        results: list[TeamPerformance] = []

        for team, team_trades in by_team.items():
            pnls = [t["pnl"] for t in team_trades]
            pnl_pcts = [t["pnl_pct"] for t in team_trades]
            n = len(pnls)

            winners = sum(1 for p in pnls if p > 0)
            losers = sum(1 for p in pnls if p < 0)
            total_pnl = sum(pnls)
            avg_pnl = total_pnl / n if n > 0 else 0.0

            # Sharpe-like ratio: mean return / std of returns
            pnl_arr = np.array(pnl_pcts)
            std = float(np.std(pnl_arr)) if n > 1 else 0.0
            mean_ret = float(np.mean(pnl_arr)) if n > 0 else 0.0
            sharpe = mean_ret / std * np.sqrt(self.annualization_factor) if std > 1e-10 else 0.0

            results.append(TeamPerformance(
                team=team,
                num_trades=n,
                winning_trades=winners,
                losing_trades=losers,
                win_rate=round(winners / n, 4) if n > 0 else 0.0,
                total_pnl=round(total_pnl, 2),
                avg_pnl_per_trade=round(avg_pnl, 2),
                best_trade_pnl=round(max(pnls), 2) if pnls else 0.0,
                worst_trade_pnl=round(min(pnls), 2) if pnls else 0.0,
                sharpe_ratio=round(float(sharpe), 4),
                contribution_to_portfolio_return=round(total_pnl / port_val, 6),
            ))

        results.sort(key=lambda r: r.total_pnl, reverse=True)
        return results

    # ── Holding Period Analysis ──────────────

    def holding_period_analysis(
        self,
        trades: list[dict[str, Any]],
    ) -> list[HoldingPeriodBucket]:
        """
        Bucket trades by holding duration and compute stats per bucket.

        Each trade dict should have:
        - holding_days (int)
        - pnl (float)
        - pnl_pct (float)

        Default buckets:
        - Intraday: 0-1 day
        - Short: 1-7 days
        - Medium: 7-30 days
        - Long: 30-90 days
        - Extended: 90+ days

        Returns:
            List of HoldingPeriodBucket.
        """
        bucket_defs = [
            ("0-1d (Intraday)", 0, 1),
            ("1-7d (Short)", 1, 7),
            ("7-30d (Medium)", 7, 30),
            ("30-90d (Long)", 30, 90),
            ("90d+ (Extended)", 90, 100_000),
        ]

        results: list[HoldingPeriodBucket] = []

        for label, min_d, max_d in bucket_defs:
            bucket_trades = [
                t for t in trades
                if min_d <= t.get("holding_days", 0) < max_d
            ]

            if not bucket_trades:
                results.append(HoldingPeriodBucket(
                    bucket_label=label,
                    min_days=min_d,
                    max_days=max_d,
                    num_trades=0,
                    avg_return_pct=0.0,
                    median_return_pct=0.0,
                    total_pnl=0.0,
                    win_rate=0.0,
                    avg_holding_days=0.0,
                ))
                continue

            pnls = [t["pnl"] for t in bucket_trades]
            pnl_pcts = np.array([t["pnl_pct"] for t in bucket_trades])
            hold_days = np.array([t["holding_days"] for t in bucket_trades])
            n = len(bucket_trades)
            winners = sum(1 for p in pnls if p > 0)

            results.append(HoldingPeriodBucket(
                bucket_label=label,
                min_days=min_d,
                max_days=max_d,
                num_trades=n,
                avg_return_pct=round(float(np.mean(pnl_pcts)), 4),
                median_return_pct=round(float(np.median(pnl_pcts)), 4),
                total_pnl=round(sum(pnls), 2),
                win_rate=round(winners / n, 4),
                avg_holding_days=round(float(np.mean(hold_days)), 1),
            ))

        return results

    # ── Full Report ─────────────────────────

    def full_report(
        self,
        trades: list[dict[str, Any]],
        portfolio_value: float,
        period_start: datetime,
        period_end: datetime,
        portfolio_return: float,
        benchmark_return: float = 0.0,
        portfolio_sectors: dict[str, dict[str, float]] | None = None,
        benchmark_sectors: dict[str, dict[str, float]] | None = None,
        portfolio_returns_series: list[float] | None = None,
        factor_returns: dict[str, list[float]] | None = None,
    ) -> AttributionReport:
        """
        Generate a comprehensive attribution report across all dimensions.

        Args:
            trades: List of trade dicts (see individual methods for required keys).
            portfolio_value: Current portfolio value.
            period_start: Analysis period start.
            period_end: Analysis period end.
            portfolio_return: Total portfolio return for the period.
            benchmark_return: Benchmark return for comparison.
            portfolio_sectors: For Brinson-Fachler. sector -> {weight, return}.
            benchmark_sectors: Benchmark sector weights/returns.
            portfolio_returns_series: Periodic returns for factor attribution.
            factor_returns: Factor return series for factor attribution.

        Returns:
            AttributionReport with all available attribution dimensions.
        """
        # Position attribution
        pos_attr = self.position_attribution(trades, portfolio_value)

        # Top contributors and detractors
        top_contributors = [
            p.symbol for p in pos_attr[:5] if p.contribution_to_return > 0
        ]
        top_detractors = [
            p.symbol for p in reversed(pos_attr) if p.contribution_to_return < 0
        ][:5]

        # Sector attribution (if data available)
        sector_attr = None
        if portfolio_sectors and benchmark_sectors:
            sector_attr = self.sector_attribution(portfolio_sectors, benchmark_sectors)

        # Factor attribution (if data available)
        factor_attr = None
        if portfolio_returns_series and factor_returns:
            factor_attr = self.factor_attribution(portfolio_returns_series, factor_returns)

        # Team attribution
        team_perfs = self.team_attribution(trades, portfolio_value)

        # Holding period analysis
        hold_buckets = self.holding_period_analysis(trades)

        return AttributionReport(
            period_start=period_start,
            period_end=period_end,
            portfolio_return=round(portfolio_return, 6),
            benchmark_return=round(benchmark_return, 6),
            active_return=round(portfolio_return - benchmark_return, 6),
            position_attributions=pos_attr,
            sector_attribution=sector_attr,
            factor_attribution=factor_attr,
            team_performances=team_perfs,
            holding_period_buckets=hold_buckets,
            top_contributors=top_contributors,
            top_detractors=top_detractors,
        )
