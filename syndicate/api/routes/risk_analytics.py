"""Risk analytics, attribution, diversification & market data endpoints.

Exposes the backend risk/portfolio/data modules that previously had no API routes.
All endpoints return realistic demo data where live data is unavailable.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["risk-analytics"])


# ═══════════════════════════════════════════
#  Response Models
# ═══════════════════════════════════════════


class VaRResponse(BaseModel):
    """VaR report response."""
    confidence_level: float
    horizon_days: int
    parametric_var: float
    historical_var: float
    monte_carlo_var: float
    parametric_cvar: float
    historical_cvar: float
    monte_carlo_cvar: float
    portfolio_mean_return: float
    portfolio_volatility: float
    skewness: float
    kurtosis: float
    undiversified_var: float
    diversification_ratio: float
    positions: list[dict[str, Any]]
    num_observations: int
    warnings: list[str]
    computed_at: str


class StressTestResponse(BaseModel):
    """Stress test suite response."""
    scenario_reports: list[dict[str, Any]]
    portfolio_value: float
    worst_scenario_name: str
    worst_scenario_pnl_pct: float
    timestamp: str


class CorrelationMatrixResponse(BaseModel):
    """Correlation matrix response."""
    symbols: list[str]
    matrix: list[list[float]]
    heatmap_data: list[dict[str, Any]]
    avg_correlation: float
    max_correlation: dict[str, Any]
    min_correlation: dict[str, Any]
    highly_correlated_pairs: list[dict[str, Any]]


class ExposurePosition(BaseModel):
    """Single position exposure."""
    symbol: str
    sector: str
    weight: float
    notional: float
    side: str


class SectorExposure(BaseModel):
    """Sector-level exposure."""
    sector: str
    weight: float
    notional: float
    num_positions: int
    limit: float
    within_limit: bool


class ExposureResponse(BaseModel):
    """Sector exposure breakdown."""
    total_portfolio_value: float
    positions: list[ExposurePosition]
    sector_exposures: list[SectorExposure]
    limit_breaches: list[str]


class AttributionResponse(BaseModel):
    """Attribution report response."""
    period_start: str
    period_end: str
    portfolio_return: float
    benchmark_return: float
    active_return: float
    position_attributions: list[dict[str, Any]]
    sector_attribution: dict[str, Any] | None = None
    team_performances: list[dict[str, Any]]
    holding_period_buckets: list[dict[str, Any]]
    top_contributors: list[str]
    top_detractors: list[str]


class DiversificationResponse(BaseModel):
    """Diversification report response."""
    num_positions: int
    concentration: dict[str, Any]
    diversification_ratio: float
    portfolio_volatility: float
    weighted_avg_volatility: float
    risk_contributions: list[dict[str, Any]]
    risk_parity_weights: dict[str, float]
    correlation_summary: dict[str, Any]


class LiquidityPosition(BaseModel):
    """Liquidity analysis for a single position."""
    symbol: str
    notional: float
    avg_daily_volume: float
    days_to_liquidate: float
    pct_of_daily_volume: float
    liquidity_tier: str
    spread_bps: float


class LiquidityResponse(BaseModel):
    """Liquidity analysis response."""
    total_portfolio_value: float
    positions: list[LiquidityPosition]
    portfolio_days_to_liquidate: float
    illiquid_pct: float


class MacroSnapshotResponse(BaseModel):
    """Macro regime summary."""
    timestamp: str
    fed_funds_rate: float
    yield_curve_10y_2y_spread: float
    yield_curve_status: str
    dxy_index: float
    dxy_trend: str
    vix: float
    vix_regime: str
    cpi_yoy: float
    pce_yoy: float
    inflation_regime: str
    gdp_growth_qoq: float
    unemployment_rate: float
    regime_label: str
    regime_description: str


class EconomicEvent(BaseModel):
    """Single economic calendar event."""
    date: str
    time_utc: str
    event: str
    country: str
    impact: str
    previous: str
    forecast: str


class EconomicCalendarResponse(BaseModel):
    """Economic calendar response."""
    events: list[EconomicEvent]
    period_start: str
    period_end: str


class EarningsEntry(BaseModel):
    """Single earnings calendar entry."""
    date: str
    symbol: str
    company: str
    market_cap_b: float
    eps_estimate: float | None = None
    revenue_estimate_b: float | None = None
    time: str  # "BMO" | "AMC" | "TBD"


class EarningsCalendarResponse(BaseModel):
    """Earnings calendar response."""
    entries: list[EarningsEntry]
    period_start: str
    period_end: str


class SectorHeatmapEntry(BaseModel):
    """Single sector in the heatmap."""
    sector: str
    etf: str
    return_1d: float
    return_5d: float
    return_1m: float
    market_cap_t: float


class SectorHeatmapResponse(BaseModel):
    """GICS sector heatmap response."""
    timestamp: str
    sectors: list[SectorHeatmapEntry]


# ═══════════════════════════════════════════
#  Demo Data Generators
# ═══════════════════════════════════════════

# Demo portfolio used across risk endpoints
DEMO_POSITIONS = [
    {"symbol": "BTCUSDT", "entry_price": 62000.0, "current_price": 64500.0, "quantity": 0.45, "side": "BUY", "sector": "Crypto - L1", "team": "alpha"},
    {"symbol": "ETHUSDT", "entry_price": 3100.0, "current_price": 3250.0, "quantity": 5.0, "side": "BUY", "sector": "Crypto - L1", "team": "alpha"},
    {"symbol": "SOLUSDT", "entry_price": 145.0, "current_price": 155.0, "quantity": 50.0, "side": "BUY", "sector": "Crypto - L1", "team": "momentum"},
    {"symbol": "LINKUSDT", "entry_price": 14.50, "current_price": 15.80, "quantity": 200.0, "side": "BUY", "sector": "Crypto - Oracle", "team": "quant"},
    {"symbol": "AVAXUSDT", "entry_price": 38.0, "current_price": 36.50, "quantity": 80.0, "side": "BUY", "sector": "Crypto - L1", "team": "momentum"},
    {"symbol": "DOGEUSDT", "entry_price": 0.12, "current_price": 0.135, "quantity": 25000.0, "side": "BUY", "sector": "Crypto - Meme", "team": "sentiment"},
    {"symbol": "ARBUSDT", "entry_price": 1.10, "current_price": 1.25, "quantity": 1500.0, "side": "BUY", "sector": "Crypto - L2", "team": "quant"},
    {"symbol": "NEARUSDT", "entry_price": 5.80, "current_price": 6.30, "quantity": 300.0, "side": "BUY", "sector": "Crypto - L1", "team": "alpha"},
]

DEMO_SYMBOLS = [p["symbol"] for p in DEMO_POSITIONS]

DEMO_WEIGHTS = {
    "BTCUSDT": 0.30, "ETHUSDT": 0.17, "SOLUSDT": 0.10, "LINKUSDT": 0.04,
    "AVAXUSDT": 0.04, "DOGEUSDT": 0.04, "ARBUSDT": 0.02, "NEARUSDT": 0.02,
}


def _generate_demo_returns(seed: int = 42) -> dict[str, list[float]]:
    """Generate 90 days of synthetic daily returns for the demo portfolio."""
    import numpy as np

    rng = np.random.default_rng(seed)
    n_days = 90
    # Approximate daily means and vols
    params = {
        "BTCUSDT": (0.001, 0.035),
        "ETHUSDT": (0.0012, 0.042),
        "SOLUSDT": (0.0015, 0.055),
        "LINKUSDT": (0.0008, 0.05),
        "AVAXUSDT": (0.0005, 0.06),
        "DOGEUSDT": (0.001, 0.07),
        "ARBUSDT": (0.0009, 0.065),
        "NEARUSDT": (0.001, 0.058),
    }
    returns: dict[str, list[float]] = {}
    for sym, (mu, sigma) in params.items():
        returns[sym] = rng.normal(mu, sigma, n_days).tolist()
    return returns


def _demo_portfolio_value() -> float:
    total = sum(p["current_price"] * p["quantity"] for p in DEMO_POSITIONS)
    cash = 100_000 - sum(p["entry_price"] * p["quantity"] for p in DEMO_POSITIONS)
    return total + max(cash, 0)


# ═══════════════════════════════════════════
#  Risk Endpoints
# ═══════════════════════════════════════════


@router.get("/portfolio/risk/var", response_model=VaRResponse)
async def get_var_report():
    """Return Value-at-Risk report (parametric, historical, Monte Carlo, CVaR) using demo portfolio data."""
    from syndicate.risk.var_metrics import compute_var_report

    returns = _generate_demo_returns()
    report = compute_var_report(
        returns_history=returns,
        weights=DEMO_WEIGHTS,
        confidence=0.95,
        horizon=1,
        mc_simulations=5_000,
    )

    return VaRResponse(
        confidence_level=report.confidence_level,
        horizon_days=report.horizon_days,
        parametric_var=round(report.parametric_var, 6),
        historical_var=round(report.historical_var, 6),
        monte_carlo_var=round(report.monte_carlo_var, 6),
        parametric_cvar=round(report.parametric_cvar, 6),
        historical_cvar=round(report.historical_cvar, 6),
        monte_carlo_cvar=round(report.monte_carlo_cvar, 6),
        portfolio_mean_return=round(report.portfolio_mean_return, 6),
        portfolio_volatility=round(report.portfolio_volatility, 6),
        skewness=round(report.skewness, 4),
        kurtosis=round(report.kurtosis, 4),
        undiversified_var=round(report.undiversified_var, 6),
        diversification_ratio=round(report.diversification_ratio, 4),
        positions=[p.model_dump() for p in report.positions],
        num_observations=report.num_observations,
        warnings=report.warnings,
        computed_at=report.computed_at.isoformat(),
    )


@router.get("/portfolio/risk/stress-test", response_model=StressTestResponse)
async def get_stress_test():
    """Return stress test results for all 11 scenarios applied to the demo portfolio."""
    from syndicate.risk.stress_testing import StressTestEngine, ALL_SCENARIOS
    from syndicate.data.models import PortfolioState, Position, OrderSide

    # Build a PortfolioState from demo data
    positions = []
    for p in DEMO_POSITIONS:
        positions.append(Position(
            symbol=p["symbol"],
            entry_price=p["entry_price"],
            current_price=p["current_price"],
            quantity=p["quantity"],
            side=OrderSide.BUY if p["side"] == "BUY" else OrderSide.SELL,
        ))

    cash = 100_000 - sum(p["entry_price"] * p["quantity"] for p in DEMO_POSITIONS)
    portfolio = PortfolioState(
        cash=max(cash, 0),
        positions=positions,
    )

    engine = StressTestEngine()
    suite = engine.run_full_suite(portfolio)

    return StressTestResponse(
        scenario_reports=[r.model_dump(mode="json") for r in suite.scenario_reports],
        portfolio_value=suite.portfolio_value,
        worst_scenario_name=suite.worst_scenario_name,
        worst_scenario_pnl_pct=round(suite.worst_scenario_pnl_pct, 6),
        timestamp=suite.timestamp.isoformat(),
    )


@router.get("/portfolio/risk/correlation-matrix", response_model=CorrelationMatrixResponse)
async def get_correlation_matrix():
    """Return NxN correlation matrix for portfolio positions."""
    from syndicate.portfolio.diversification import DiversificationAnalyzer

    analyzer = DiversificationAnalyzer(annualization_factor=365.0)
    returns = _generate_demo_returns()
    result = analyzer.correlation_matrix(returns, DEMO_SYMBOLS)

    return CorrelationMatrixResponse(
        symbols=result["symbols"],
        matrix=result["matrix"],
        heatmap_data=result["heatmap_data"],
        avg_correlation=result["avg_correlation"],
        max_correlation=result["max_correlation"],
        min_correlation=result["min_correlation"],
        highly_correlated_pairs=result["highly_correlated_pairs"],
    )


@router.get("/portfolio/risk/exposure", response_model=ExposureResponse)
async def get_exposure():
    """Return sector exposure breakdown with limit enforcement status."""
    port_val = _demo_portfolio_value()

    # Sector limits (typical institutional limits)
    sector_limits = {
        "Crypto - L1": 0.70,
        "Crypto - L2": 0.15,
        "Crypto - Oracle": 0.10,
        "Crypto - Meme": 0.10,
        "Crypto - DeFi": 0.15,
    }

    # Build position exposures
    position_exposures: list[ExposurePosition] = []
    sector_agg: dict[str, dict[str, Any]] = {}

    for p in DEMO_POSITIONS:
        notional = p["current_price"] * p["quantity"]
        weight = notional / port_val if port_val > 0 else 0.0
        sector = p.get("sector", "Unknown")

        position_exposures.append(ExposurePosition(
            symbol=p["symbol"],
            sector=sector,
            weight=round(weight, 4),
            notional=round(notional, 2),
            side=p["side"],
        ))

        if sector not in sector_agg:
            sector_agg[sector] = {"notional": 0.0, "count": 0}
        sector_agg[sector]["notional"] += notional
        sector_agg[sector]["count"] += 1

    # Build sector exposures
    sector_exposures: list[SectorExposure] = []
    limit_breaches: list[str] = []

    for sector, agg in sorted(sector_agg.items()):
        weight = agg["notional"] / port_val if port_val > 0 else 0.0
        limit = sector_limits.get(sector, 0.25)
        within = weight <= limit
        if not within:
            limit_breaches.append(
                f"{sector}: {weight:.1%} exceeds limit of {limit:.0%}"
            )
        sector_exposures.append(SectorExposure(
            sector=sector,
            weight=round(weight, 4),
            notional=round(agg["notional"], 2),
            num_positions=agg["count"],
            limit=limit,
            within_limit=within,
        ))

    return ExposureResponse(
        total_portfolio_value=round(port_val, 2),
        positions=position_exposures,
        sector_exposures=sector_exposures,
        limit_breaches=limit_breaches,
    )


# ═══════════════════════════════════════════
#  Attribution Endpoints
# ═══════════════════════════════════════════


@router.get("/portfolio/attribution", response_model=AttributionResponse)
async def get_attribution():
    """Return full attribution report (position, sector, team, timing, holding period)."""
    from syndicate.portfolio.attribution import PerformanceAttribution

    engine = PerformanceAttribution(annualization_factor=365.0)
    now = datetime.now(timezone.utc)

    # Enrich demo trades with fields required by the attribution engine
    trades = []
    port_val = _demo_portfolio_value()
    for p in DEMO_POSITIONS:
        notional = p["entry_price"] * p["quantity"]
        trades.append({
            "symbol": p["symbol"],
            "entry_price": p["entry_price"],
            "current_price": p["current_price"],
            "exit_price": None,
            "quantity": p["quantity"],
            "side": p["side"],
            "weight_at_entry": notional / port_val if port_val > 0 else 0.0,
            "sector": p.get("sector", ""),
            "team": p.get("team", "unknown"),
            "pnl": (p["current_price"] - p["entry_price"]) * p["quantity"],
            "pnl_pct": (p["current_price"] - p["entry_price"]) / p["entry_price"],
            "holding_days": 14,
        })

    # Sector attribution with benchmark
    portfolio_sectors = {
        "Crypto - L1": {"weight": 0.63, "return": 0.035},
        "Crypto - Oracle": {"weight": 0.04, "return": 0.089},
        "Crypto - Meme": {"weight": 0.04, "return": 0.125},
        "Crypto - L2": {"weight": 0.02, "return": 0.136},
    }
    benchmark_sectors = {
        "Crypto - L1": {"weight": 0.75, "return": 0.028},
        "Crypto - Oracle": {"weight": 0.08, "return": 0.060},
        "Crypto - Meme": {"weight": 0.05, "return": 0.100},
        "Crypto - L2": {"weight": 0.05, "return": 0.090},
    }

    report = engine.full_report(
        trades=trades,
        portfolio_value=port_val,
        period_start=now - timedelta(days=30),
        period_end=now,
        portfolio_return=0.042,
        benchmark_return=0.031,
        portfolio_sectors=portfolio_sectors,
        benchmark_sectors=benchmark_sectors,
    )

    return AttributionResponse(
        period_start=report.period_start.isoformat(),
        period_end=report.period_end.isoformat(),
        portfolio_return=report.portfolio_return,
        benchmark_return=report.benchmark_return,
        active_return=report.active_return,
        position_attributions=[pa.model_dump() for pa in report.position_attributions],
        sector_attribution=report.sector_attribution.model_dump(mode="json") if report.sector_attribution else None,
        team_performances=[tp.model_dump() for tp in report.team_performances],
        holding_period_buckets=[hb.model_dump() for hb in report.holding_period_buckets],
        top_contributors=report.top_contributors,
        top_detractors=report.top_detractors,
    )


# ═══════════════════════════════════════════
#  Diversification Endpoints
# ═══════════════════════════════════════════


@router.get("/portfolio/diversification", response_model=DiversificationResponse)
async def get_diversification():
    """Return HHI, effective positions, risk parity analysis."""
    from syndicate.portfolio.diversification import DiversificationAnalyzer

    analyzer = DiversificationAnalyzer(annualization_factor=365.0)
    returns = _generate_demo_returns()

    report = analyzer.full_report(
        weights=DEMO_WEIGHTS,
        returns=returns,
    )

    return DiversificationResponse(
        num_positions=report.num_positions,
        concentration=report.concentration.model_dump(),
        diversification_ratio=report.diversification_ratio,
        portfolio_volatility=report.portfolio_volatility,
        weighted_avg_volatility=report.weighted_avg_volatility,
        risk_contributions=[rc.model_dump() for rc in report.risk_contributions],
        risk_parity_weights=report.risk_parity_weights,
        correlation_summary=report.correlation_summary,
    )


# ═══════════════════════════════════════════
#  Liquidity Endpoint
# ═══════════════════════════════════════════


@router.get("/portfolio/risk/liquidity", response_model=LiquidityResponse)
async def get_liquidity():
    """Return liquidity analysis per position (demo estimates)."""
    # Realistic 24h volume estimates in USD
    volume_estimates = {
        "BTCUSDT": 25_000_000_000.0,
        "ETHUSDT": 12_000_000_000.0,
        "SOLUSDT": 2_500_000_000.0,
        "LINKUSDT": 500_000_000.0,
        "AVAXUSDT": 350_000_000.0,
        "DOGEUSDT": 1_200_000_000.0,
        "ARBUSDT": 300_000_000.0,
        "NEARUSDT": 250_000_000.0,
    }
    spread_estimates = {
        "BTCUSDT": 1.0, "ETHUSDT": 1.5, "SOLUSDT": 3.0, "LINKUSDT": 5.0,
        "AVAXUSDT": 6.0, "DOGEUSDT": 4.0, "ARBUSDT": 8.0, "NEARUSDT": 7.0,
    }

    port_val = _demo_portfolio_value()
    positions: list[LiquidityPosition] = []
    max_days = 0.0
    illiquid_notional = 0.0

    for p in DEMO_POSITIONS:
        notional = p["current_price"] * p["quantity"]
        vol = volume_estimates.get(p["symbol"], 100_000_000.0)
        # Assume we can trade up to 5% of daily volume without moving the market
        tradeable_per_day = vol * 0.05
        days_to_liq = notional / tradeable_per_day if tradeable_per_day > 0 else 999.0
        pct_vol = (notional / vol * 100) if vol > 0 else 0.0

        if days_to_liq > 1.0:
            tier = "Moderate"
            illiquid_notional += notional
        elif days_to_liq > 5.0:
            tier = "Illiquid"
            illiquid_notional += notional
        else:
            tier = "Highly Liquid"

        max_days = max(max_days, days_to_liq)

        positions.append(LiquidityPosition(
            symbol=p["symbol"],
            notional=round(notional, 2),
            avg_daily_volume=vol,
            days_to_liquidate=round(days_to_liq, 4),
            pct_of_daily_volume=round(pct_vol, 4),
            liquidity_tier=tier,
            spread_bps=spread_estimates.get(p["symbol"], 5.0),
        ))

    return LiquidityResponse(
        total_portfolio_value=round(port_val, 2),
        positions=positions,
        portfolio_days_to_liquidate=round(max_days, 4),
        illiquid_pct=round(illiquid_notional / port_val * 100, 2) if port_val > 0 else 0.0,
    )


# ═══════════════════════════════════════════
#  Market Data Endpoints
# ═══════════════════════════════════════════


@router.get("/data/macro/snapshot", response_model=MacroSnapshotResponse)
async def get_macro_snapshot():
    """Return current macro regime summary (demo data: Fed rate, yield curve, DXY, VIX, inflation)."""
    return MacroSnapshotResponse(
        timestamp=datetime.now(timezone.utc).isoformat(),
        fed_funds_rate=5.33,
        yield_curve_10y_2y_spread=-0.18,
        yield_curve_status="Inverted",
        dxy_index=104.25,
        dxy_trend="Strengthening",
        vix=16.8,
        vix_regime="Low Volatility",
        cpi_yoy=3.1,
        pce_yoy=2.8,
        inflation_regime="Disinflation",
        gdp_growth_qoq=2.1,
        unemployment_rate=3.9,
        regime_label="Late Cycle Tightening",
        regime_description=(
            "Fed funds at terminal rate with inverted yield curve. "
            "Inflation trending toward target but sticky in services. "
            "Labor market resilient but showing early softening. "
            "Risk assets supported by AI capex cycle but vulnerable to rate surprise."
        ),
    )


@router.get("/data/economic-calendar", response_model=EconomicCalendarResponse)
async def get_economic_calendar():
    """Return next 30 days of economic releases with impact ratings (demo data)."""
    now = datetime.now(timezone.utc)
    base = now.replace(hour=0, minute=0, second=0, microsecond=0)

    events = [
        EconomicEvent(date=(base + timedelta(days=1)).strftime("%Y-%m-%d"), time_utc="12:30", event="Non-Farm Payrolls", country="US", impact="High", previous="275K", forecast="200K"),
        EconomicEvent(date=(base + timedelta(days=1)).strftime("%Y-%m-%d"), time_utc="12:30", event="Unemployment Rate", country="US", impact="High", previous="3.9%", forecast="3.9%"),
        EconomicEvent(date=(base + timedelta(days=3)).strftime("%Y-%m-%d"), time_utc="14:00", event="ISM Services PMI", country="US", impact="High", previous="52.6", forecast="52.0"),
        EconomicEvent(date=(base + timedelta(days=5)).strftime("%Y-%m-%d"), time_utc="12:30", event="CPI (YoY)", country="US", impact="High", previous="3.1%", forecast="2.9%"),
        EconomicEvent(date=(base + timedelta(days=5)).strftime("%Y-%m-%d"), time_utc="12:30", event="Core CPI (MoM)", country="US", impact="High", previous="0.4%", forecast="0.3%"),
        EconomicEvent(date=(base + timedelta(days=7)).strftime("%Y-%m-%d"), time_utc="12:30", event="PPI (MoM)", country="US", impact="Medium", previous="0.3%", forecast="0.1%"),
        EconomicEvent(date=(base + timedelta(days=8)).strftime("%Y-%m-%d"), time_utc="12:30", event="Initial Jobless Claims", country="US", impact="Medium", previous="210K", forecast="215K"),
        EconomicEvent(date=(base + timedelta(days=8)).strftime("%Y-%m-%d"), time_utc="12:30", event="Retail Sales (MoM)", country="US", impact="High", previous="0.6%", forecast="0.3%"),
        EconomicEvent(date=(base + timedelta(days=10)).strftime("%Y-%m-%d"), time_utc="09:00", event="ECB Interest Rate Decision", country="EU", impact="High", previous="4.50%", forecast="4.50%"),
        EconomicEvent(date=(base + timedelta(days=12)).strftime("%Y-%m-%d"), time_utc="18:00", event="FOMC Minutes", country="US", impact="High", previous="N/A", forecast="N/A"),
        EconomicEvent(date=(base + timedelta(days=14)).strftime("%Y-%m-%d"), time_utc="12:30", event="PCE Price Index (YoY)", country="US", impact="High", previous="2.8%", forecast="2.7%"),
        EconomicEvent(date=(base + timedelta(days=15)).strftime("%Y-%m-%d"), time_utc="12:30", event="Initial Jobless Claims", country="US", impact="Medium", previous="215K", forecast="212K"),
        EconomicEvent(date=(base + timedelta(days=18)).strftime("%Y-%m-%d"), time_utc="14:00", event="Consumer Confidence", country="US", impact="Medium", previous="104.7", forecast="103.0"),
        EconomicEvent(date=(base + timedelta(days=20)).strftime("%Y-%m-%d"), time_utc="12:30", event="GDP (QoQ Annualized)", country="US", impact="High", previous="3.2%", forecast="2.1%"),
        EconomicEvent(date=(base + timedelta(days=22)).strftime("%Y-%m-%d"), time_utc="12:30", event="Initial Jobless Claims", country="US", impact="Medium", previous="212K", forecast="215K"),
        EconomicEvent(date=(base + timedelta(days=25)).strftime("%Y-%m-%d"), time_utc="02:30", event="BOJ Interest Rate Decision", country="JP", impact="High", previous="0.10%", forecast="0.10%"),
        EconomicEvent(date=(base + timedelta(days=27)).strftime("%Y-%m-%d"), time_utc="14:00", event="ISM Manufacturing PMI", country="US", impact="High", previous="47.8", forecast="48.5"),
        EconomicEvent(date=(base + timedelta(days=29)).strftime("%Y-%m-%d"), time_utc="12:30", event="Non-Farm Payrolls", country="US", impact="High", previous="200K", forecast="180K"),
    ]

    return EconomicCalendarResponse(
        events=events,
        period_start=base.strftime("%Y-%m-%d"),
        period_end=(base + timedelta(days=30)).strftime("%Y-%m-%d"),
    )


@router.get("/data/earnings-calendar", response_model=EarningsCalendarResponse)
async def get_earnings_calendar():
    """Return next 14 days of earnings dates for major S&P 500 companies (demo data)."""
    now = datetime.now(timezone.utc)
    base = now.replace(hour=0, minute=0, second=0, microsecond=0)

    entries = [
        EarningsEntry(date=(base + timedelta(days=1)).strftime("%Y-%m-%d"), symbol="AAPL", company="Apple Inc.", market_cap_b=2850.0, eps_estimate=2.10, revenue_estimate_b=94.5, time="AMC"),
        EarningsEntry(date=(base + timedelta(days=1)).strftime("%Y-%m-%d"), symbol="AMZN", company="Amazon.com Inc.", market_cap_b=1900.0, eps_estimate=0.85, revenue_estimate_b=155.0, time="AMC"),
        EarningsEntry(date=(base + timedelta(days=2)).strftime("%Y-%m-%d"), symbol="MSFT", company="Microsoft Corp.", market_cap_b=3100.0, eps_estimate=2.82, revenue_estimate_b=61.0, time="AMC"),
        EarningsEntry(date=(base + timedelta(days=2)).strftime("%Y-%m-%d"), symbol="META", company="Meta Platforms Inc.", market_cap_b=1250.0, eps_estimate=4.95, revenue_estimate_b=39.0, time="AMC"),
        EarningsEntry(date=(base + timedelta(days=3)).strftime("%Y-%m-%d"), symbol="GOOGL", company="Alphabet Inc.", market_cap_b=1750.0, eps_estimate=1.55, revenue_estimate_b=85.0, time="AMC"),
        EarningsEntry(date=(base + timedelta(days=4)).strftime("%Y-%m-%d"), symbol="NVDA", company="NVIDIA Corp.", market_cap_b=2200.0, eps_estimate=5.60, revenue_estimate_b=24.5, time="AMC"),
        EarningsEntry(date=(base + timedelta(days=5)).strftime("%Y-%m-%d"), symbol="JPM", company="JPMorgan Chase & Co.", market_cap_b=580.0, eps_estimate=4.10, revenue_estimate_b=41.0, time="BMO"),
        EarningsEntry(date=(base + timedelta(days=5)).strftime("%Y-%m-%d"), symbol="V", company="Visa Inc.", market_cap_b=540.0, eps_estimate=2.45, revenue_estimate_b=8.9, time="AMC"),
        EarningsEntry(date=(base + timedelta(days=7)).strftime("%Y-%m-%d"), symbol="UNH", company="UnitedHealth Group", market_cap_b=490.0, eps_estimate=6.60, revenue_estimate_b=94.0, time="BMO"),
        EarningsEntry(date=(base + timedelta(days=8)).strftime("%Y-%m-%d"), symbol="TSLA", company="Tesla Inc.", market_cap_b=680.0, eps_estimate=0.72, revenue_estimate_b=25.5, time="AMC"),
        EarningsEntry(date=(base + timedelta(days=9)).strftime("%Y-%m-%d"), symbol="XOM", company="Exxon Mobil Corp.", market_cap_b=470.0, eps_estimate=2.35, revenue_estimate_b=89.0, time="BMO"),
        EarningsEntry(date=(base + timedelta(days=10)).strftime("%Y-%m-%d"), symbol="WMT", company="Walmart Inc.", market_cap_b=430.0, eps_estimate=1.65, revenue_estimate_b=165.0, time="BMO"),
        EarningsEntry(date=(base + timedelta(days=11)).strftime("%Y-%m-%d"), symbol="DIS", company="Walt Disney Co.", market_cap_b=210.0, eps_estimate=1.10, revenue_estimate_b=22.5, time="AMC"),
        EarningsEntry(date=(base + timedelta(days=12)).strftime("%Y-%m-%d"), symbol="NFLX", company="Netflix Inc.", market_cap_b=250.0, eps_estimate=4.50, revenue_estimate_b=9.3, time="AMC"),
    ]

    return EarningsCalendarResponse(
        entries=entries,
        period_start=base.strftime("%Y-%m-%d"),
        period_end=(base + timedelta(days=14)).strftime("%Y-%m-%d"),
    )


@router.get("/data/sector-heatmap", response_model=SectorHeatmapResponse)
async def get_sector_heatmap():
    """Return 11 GICS sectors with 1d/5d/1m returns (demo data)."""
    sectors = [
        SectorHeatmapEntry(sector="Information Technology", etf="XLK", return_1d=0.82, return_5d=2.15, return_1m=5.40, market_cap_t=15.2),
        SectorHeatmapEntry(sector="Health Care", etf="XLV", return_1d=-0.35, return_5d=0.90, return_1m=2.10, market_cap_t=7.5),
        SectorHeatmapEntry(sector="Financials", etf="XLF", return_1d=0.55, return_5d=1.80, return_1m=4.30, market_cap_t=5.8),
        SectorHeatmapEntry(sector="Consumer Discretionary", etf="XLY", return_1d=0.12, return_5d=-0.60, return_1m=1.80, market_cap_t=5.2),
        SectorHeatmapEntry(sector="Communication Services", etf="XLC", return_1d=1.05, return_5d=3.20, return_1m=6.10, market_cap_t=4.9),
        SectorHeatmapEntry(sector="Industrials", etf="XLI", return_1d=0.28, return_5d=1.10, return_1m=3.50, market_cap_t=4.5),
        SectorHeatmapEntry(sector="Consumer Staples", etf="XLP", return_1d=-0.15, return_5d=0.40, return_1m=0.90, market_cap_t=3.8),
        SectorHeatmapEntry(sector="Energy", etf="XLE", return_1d=-0.95, return_5d=-2.30, return_1m=-1.50, market_cap_t=3.2),
        SectorHeatmapEntry(sector="Utilities", etf="XLU", return_1d=-0.20, return_5d=0.10, return_1m=1.20, market_cap_t=1.6),
        SectorHeatmapEntry(sector="Real Estate", etf="XLRE", return_1d=-0.45, return_5d=-0.80, return_1m=-0.30, market_cap_t=1.3),
        SectorHeatmapEntry(sector="Materials", etf="XLB", return_1d=0.40, return_5d=0.95, return_1m=2.60, market_cap_t=1.1),
    ]

    return SectorHeatmapResponse(
        timestamp=datetime.now(timezone.utc).isoformat(),
        sectors=sectors,
    )
