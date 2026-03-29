"""
Institutional-Grade Stress Testing Framework.

Implements the stress testing discipline used by real hedge funds and
mandated by prime brokers / institutional LPs:

1. Historical Crisis Replay:
   Apply shocks from actual market crises to current portfolio holdings.
   Each scenario encodes asset-class-specific drawdowns, correlation
   shifts, and liquidity effects observed during the real event.

2. Hypothetical Stress Scenarios:
   Configurable what-if shocks that may not have historical precedent
   but represent plausible tail risks (regulatory ban, flash crash,
   liquidity crunch, correlation breakdown).

3. Sensitivity Analysis:
   Systematic grid of P&L impacts across move sizes, volatility
   multipliers, and correlation regimes.

4. Structured Output:
   Every scenario produces a StressTestReport (Pydantic model) with
   dollar and percentage impact, worst-case loss, and estimated
   recovery time -- suitable for LP reporting and compliance dashboards.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

import numpy as np
import structlog
from pydantic import BaseModel, Field

from syndicate.data.models import OrderSide, PortfolioState, Position

logger = structlog.get_logger()


# ═══════════════════════════════════════════
#  Asset Classification Helpers
# ═══════════════════════════════════════════

class AssetClass(str, Enum):
    """Broad asset class buckets for stress scenario mapping."""

    BTC = "btc"
    ETH = "eth"
    ALT_LARGE = "alt_large"    # Top-20 ex BTC/ETH
    ALT_MID = "alt_mid"        # Rank 20-100
    MEME = "meme"
    STABLECOIN = "stablecoin"
    EQUITY = "equity"


# Simple heuristic classifier -- production would use a proper taxonomy
_STABLES = {"USDT", "USDC", "DAI", "BUSD", "TUSD", "FDUSD", "USDCUSDT"}
_BTC_SYMBOLS = {"BTC", "BTCUSDT", "BTCUSD", "XBTUSD"}
_ETH_SYMBOLS = {"ETH", "ETHUSDT", "ETHUSD"}
_LARGE_ALTS = {
    "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "MATIC", "LINK",
    "ATOM", "UNI", "LTC", "TRX", "NEAR", "APT", "OP", "ARB",
    "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "AVAXUSDT",
    "DOTUSDT", "MATICUSDT", "LINKUSDT", "ATOMUSDT", "UNIUSDT",
    "LTCUSDT", "TRXUSDT", "NEARUSDT", "APTUSDT", "OPUSDT", "ARBUSDT",
}
_MEME_SYMBOLS = {
    "DOGE", "SHIB", "PEPE", "FLOKI", "BONK", "WIF", "MEME",
    "DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "FLOKIUSDT", "BONKUSDT",
    "WIFUSDT", "MEMEUSDT",
}


def classify_asset(symbol: str) -> AssetClass:
    """Map a trading symbol to its broad asset class."""
    sym = symbol.upper().replace("/", "")
    if sym in _STABLES:
        return AssetClass.STABLECOIN
    if sym in _BTC_SYMBOLS:
        return AssetClass.BTC
    if sym in _ETH_SYMBOLS:
        return AssetClass.ETH
    if sym in _MEME_SYMBOLS:
        return AssetClass.MEME
    if sym in _LARGE_ALTS:
        return AssetClass.ALT_LARGE
    # Default: if it ends in USDT/USD and isn't classified, treat as mid alt
    if sym.endswith("USDT") or sym.endswith("USD"):
        return AssetClass.ALT_MID
    return AssetClass.EQUITY


# ═══════════════════════════════════════════
#  Stress Scenario Definitions
# ═══════════════════════════════════════════

class ScenarioType(str, Enum):
    HISTORICAL = "historical"
    HYPOTHETICAL = "hypothetical"
    SENSITIVITY = "sensitivity"


class StressScenario(BaseModel):
    """
    Definition of a single stress scenario.

    `shocks` maps AssetClass values to fractional price changes
    (e.g., -0.50 means a 50% drop). Missing keys imply 0% shock.

    `correlation_override` forces all pairwise correlations to this
    value during the scenario (models correlation spikes in crises).

    `spread_multiplier` simulates liquidity crunch -- e.g., 10.0
    means spreads widen to 10x normal.

    `recovery_days_est` is the median observed (or estimated) number
    of calendar days to recover 50% of the drawdown.
    """

    name: str
    description: str
    scenario_type: ScenarioType
    shocks: dict[str, float]  # AssetClass value -> fractional move
    correlation_override: float | None = None
    spread_multiplier: float = 1.0
    recovery_days_est: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# -----------------------------------------------
#  Historical Crisis Scenarios
# -----------------------------------------------

HISTORICAL_SCENARIOS: list[StressScenario] = [
    StressScenario(
        name="2008 Financial Crisis",
        description=(
            "Global equity meltdown. S&P 500 peak-to-trough -56.8%. "
            "Crypto did not exist. Correlations converged to ~0.95 across "
            "all risk assets. Liquidity evaporated in credit markets."
        ),
        scenario_type=ScenarioType.HISTORICAL,
        shocks={
            AssetClass.EQUITY: -0.50,
            AssetClass.BTC: 0.0,          # N/A -- did not exist
            AssetClass.ETH: 0.0,          # N/A
            AssetClass.ALT_LARGE: 0.0,    # N/A
            AssetClass.ALT_MID: 0.0,      # N/A
            AssetClass.MEME: 0.0,         # N/A
            AssetClass.STABLECOIN: 0.0,
        },
        correlation_override=0.95,
        spread_multiplier=5.0,
        recovery_days_est=680,
        metadata={"date_range": "Oct 2007 - Mar 2009", "sp500_trough": "666.79"},
    ),
    StressScenario(
        name="COVID Crash Mar 2020",
        description=(
            "Pandemic liquidity shock. S&P 500 -34% in 23 trading days. "
            "BTC crashed -50% on Mar 12-13 ('Black Thursday'). Altcoins "
            "saw -60% to -80%. DeFi TVL collapsed. Massive liquidation cascades."
        ),
        scenario_type=ScenarioType.HISTORICAL,
        shocks={
            AssetClass.EQUITY: -0.34,
            AssetClass.BTC: -0.50,
            AssetClass.ETH: -0.55,
            AssetClass.ALT_LARGE: -0.60,
            AssetClass.ALT_MID: -0.70,
            AssetClass.MEME: -0.70,
            AssetClass.STABLECOIN: -0.005,  # Minor depeg pressure
        },
        correlation_override=0.90,
        spread_multiplier=8.0,
        recovery_days_est=55,
        metadata={"date_range": "Feb 20 - Mar 23, 2020", "btc_low": "$3,850"},
    ),
    StressScenario(
        name="Luna/Terra Collapse May 2022",
        description=(
            "UST algorithmic stablecoin death spiral triggered $40B wipeout. "
            "LUNA went to zero. Contagion hit BTC (-40%), alts (-80%). "
            "Stablecoin depegs across USDT, USDD. 3AC, Celsius, Voyager "
            "went bankrupt in aftermath."
        ),
        scenario_type=ScenarioType.HISTORICAL,
        shocks={
            AssetClass.EQUITY: -0.05,
            AssetClass.BTC: -0.40,
            AssetClass.ETH: -0.45,
            AssetClass.ALT_LARGE: -0.55,
            AssetClass.ALT_MID: -0.80,
            AssetClass.MEME: -0.80,
            AssetClass.STABLECOIN: -0.05,  # USDT briefly hit $0.95
        },
        correlation_override=0.85,
        spread_multiplier=6.0,
        recovery_days_est=240,
        metadata={"date_range": "May 7 - Jun 18, 2022", "luna_fate": "Zero"},
    ),
    StressScenario(
        name="FTX Contagion Nov 2022",
        description=(
            "FTX/Alameda collapse. $8B customer funds missing. BTC -25% "
            "in days, alts -50%. Exchange counterparty risk repriced. "
            "SOL, SRM, FTT near zero. Contagion to BlockFi, Genesis."
        ),
        scenario_type=ScenarioType.HISTORICAL,
        shocks={
            AssetClass.EQUITY: -0.03,
            AssetClass.BTC: -0.25,
            AssetClass.ETH: -0.30,
            AssetClass.ALT_LARGE: -0.40,
            AssetClass.ALT_MID: -0.50,
            AssetClass.MEME: -0.50,
            AssetClass.STABLECOIN: -0.01,
        },
        correlation_override=0.80,
        spread_multiplier=4.0,
        recovery_days_est=120,
        metadata={
            "date_range": "Nov 6 - Nov 21, 2022",
            "ftx_gap": "$8B",
            "sol_special_shock": -0.60,
        },
    ),
    StressScenario(
        name="SVB Banking Crisis Mar 2023",
        description=(
            "Silicon Valley Bank collapse triggered banking contagion fears. "
            "USDC depegged to $0.87 (Circle had $3.3B at SVB). Paradoxically, "
            "BTC rallied +20% as a 'flight from TradFi' trade. Alts mixed."
        ),
        scenario_type=ScenarioType.HISTORICAL,
        shocks={
            AssetClass.EQUITY: -0.08,
            AssetClass.BTC: +0.20,          # Flight to BTC
            AssetClass.ETH: +0.12,
            AssetClass.ALT_LARGE: +0.05,
            AssetClass.ALT_MID: -0.10,
            AssetClass.MEME: -0.15,
            AssetClass.STABLECOIN: -0.10,   # USDC depeg to ~$0.87
        },
        correlation_override=None,  # Correlations actually broke down
        spread_multiplier=3.0,
        recovery_days_est=14,
        metadata={"date_range": "Mar 10 - Mar 15, 2023", "usdc_low": "$0.87"},
    ),
    StressScenario(
        name="Rate Shock",
        description=(
            "Sudden hawkish repricing -- 100bp surprise hike or similar. "
            "Models the 2022-style rate shock environment. Risk assets "
            "reprice lower, crypto drops 30%, equities -20%."
        ),
        scenario_type=ScenarioType.HISTORICAL,
        shocks={
            AssetClass.EQUITY: -0.20,
            AssetClass.BTC: -0.30,
            AssetClass.ETH: -0.35,
            AssetClass.ALT_LARGE: -0.40,
            AssetClass.ALT_MID: -0.45,
            AssetClass.MEME: -0.55,
            AssetClass.STABLECOIN: 0.0,
        },
        correlation_override=0.80,
        spread_multiplier=2.0,
        recovery_days_est=90,
        metadata={"trigger": "Surprise 100bp rate hike"},
    ),
]

# -----------------------------------------------
#  Hypothetical Stress Scenarios
# -----------------------------------------------

HYPOTHETICAL_SCENARIOS: list[StressScenario] = [
    StressScenario(
        name="Crypto Winter: BTC -30%, Alts -60%",
        description=(
            "Sustained bear market deepening. BTC breaks major support, "
            "altcoins enter capitulation phase. Similar to late 2018 or "
            "mid-2022 drawdown dynamics."
        ),
        scenario_type=ScenarioType.HYPOTHETICAL,
        shocks={
            AssetClass.BTC: -0.30,
            AssetClass.ETH: -0.40,
            AssetClass.ALT_LARGE: -0.50,
            AssetClass.ALT_MID: -0.60,
            AssetClass.MEME: -0.75,
            AssetClass.STABLECOIN: -0.01,
            AssetClass.EQUITY: -0.10,
        },
        correlation_override=0.85,
        spread_multiplier=3.0,
        recovery_days_est=180,
    ),
    StressScenario(
        name="Correlation Convergence (All -> 0.95)",
        description=(
            "All risk assets become maximally correlated. Diversification "
            "benefit collapses. A moderate -15% move in BTC drags everything "
            "down proportionally. This is the scenario portfolio diversification "
            "is supposed to protect against -- and often fails."
        ),
        scenario_type=ScenarioType.HYPOTHETICAL,
        shocks={
            AssetClass.BTC: -0.15,
            AssetClass.ETH: -0.18,
            AssetClass.ALT_LARGE: -0.20,
            AssetClass.ALT_MID: -0.25,
            AssetClass.MEME: -0.30,
            AssetClass.STABLECOIN: 0.0,
            AssetClass.EQUITY: -0.12,
        },
        correlation_override=0.95,
        spread_multiplier=2.0,
        recovery_days_est=45,
    ),
    StressScenario(
        name="Liquidity Crunch (Spreads 10x)",
        description=(
            "Market maker withdrawal event. Bid-ask spreads widen to 10x "
            "normal across all venues. Slippage on exit becomes extreme. "
            "Modeled as both direct price impact (-10% for illiquid assets) "
            "and inability to exit at mark prices."
        ),
        scenario_type=ScenarioType.HYPOTHETICAL,
        shocks={
            AssetClass.BTC: -0.05,
            AssetClass.ETH: -0.08,
            AssetClass.ALT_LARGE: -0.12,
            AssetClass.ALT_MID: -0.25,
            AssetClass.MEME: -0.40,
            AssetClass.STABLECOIN: -0.02,
            AssetClass.EQUITY: -0.03,
        },
        correlation_override=0.70,
        spread_multiplier=10.0,
        recovery_days_est=7,
        metadata={
            "slippage_note": (
                "Actual exit cost is shock + spread impact. "
                "Mid-cap and meme positions may be un-exitable at any price."
            ),
        },
    ),
    StressScenario(
        name="Flash Crash (-20% in 1 Hour, Recovery)",
        description=(
            "Sudden cascade of liquidations causes a -20% wick across "
            "all crypto assets within one hour, followed by a 60-70% "
            "recovery within 4 hours. Net impact: ~-7% for BTC, worse "
            "for leveraged or illiquid holdings. Stop losses get blown "
            "through with heavy slippage."
        ),
        scenario_type=ScenarioType.HYPOTHETICAL,
        shocks={
            # Net impact after partial recovery
            AssetClass.BTC: -0.07,
            AssetClass.ETH: -0.10,
            AssetClass.ALT_LARGE: -0.12,
            AssetClass.ALT_MID: -0.18,
            AssetClass.MEME: -0.25,
            AssetClass.STABLECOIN: 0.0,
            AssetClass.EQUITY: 0.0,
        },
        correlation_override=0.95,
        spread_multiplier=15.0,  # Extreme during the wick
        recovery_days_est=1,
        metadata={
            "intra_scenario_trough": -0.20,
            "recovery_pct": 0.65,
            "stop_loss_slippage_est": 0.05,  # 5% beyond stop price
        },
    ),
    StressScenario(
        name="Regulatory Ban Scenario",
        description=(
            "Major jurisdiction (US, EU, or China) announces outright ban "
            "on crypto trading/holding. Exchanges delist assets, fiat "
            "off-ramps freeze. Extreme panic selling."
        ),
        scenario_type=ScenarioType.HYPOTHETICAL,
        shocks={
            AssetClass.BTC: -0.50,
            AssetClass.ETH: -0.55,
            AssetClass.ALT_LARGE: -0.65,
            AssetClass.ALT_MID: -0.80,
            AssetClass.MEME: -0.90,
            AssetClass.STABLECOIN: -0.15,
            AssetClass.EQUITY: -0.05,
        },
        correlation_override=0.95,
        spread_multiplier=20.0,
        recovery_days_est=365,
        metadata={"note": "Worst case. Partial ban would be less severe."},
    ),
]

ALL_SCENARIOS: list[StressScenario] = HISTORICAL_SCENARIOS + HYPOTHETICAL_SCENARIOS


# ═══════════════════════════════════════════
#  Output Models
# ═══════════════════════════════════════════

class PositionImpact(BaseModel):
    """Stress impact on a single position."""

    symbol: str
    asset_class: str
    side: str
    notional_before: float
    shock_pct: float
    pnl_dollar: float
    pnl_pct: float
    notional_after: float
    spread_cost_est: float = 0.0  # Estimated additional cost to exit under stress


class StressTestReport(BaseModel):
    """
    Full output of a single stress scenario applied to the portfolio.

    This is the unit of output that goes to LP reports, compliance
    dashboards, and the CRO agent for decision-making.
    """

    scenario_name: str
    scenario_type: str
    scenario_description: str

    # Portfolio-level impact
    portfolio_value_before: float
    portfolio_value_after: float
    total_pnl_dollar: float
    total_pnl_pct: float

    # Worst case (accounts for spread/slippage during stress)
    worst_case_pnl_dollar: float
    worst_case_pnl_pct: float

    # Per-position breakdown
    position_impacts: list[PositionImpact] = Field(default_factory=list)

    # Stress metadata
    correlation_override: float | None = None
    spread_multiplier: float = 1.0
    recovery_days_est: int | None = None

    # Cash impact (cash is not shocked but spread costs come from it)
    cash_before: float = 0.0
    cash_after: float = 0.0

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_summary(self) -> str:
        """Human-readable summary for dashboards and LLM consumption."""
        lines = [
            f"Stress Test: {self.scenario_name}",
            f"  Type: {self.scenario_type}",
            f"  Portfolio Before: ${self.portfolio_value_before:,.2f}",
            f"  Portfolio After:  ${self.portfolio_value_after:,.2f}",
            f"  P&L:             ${self.total_pnl_dollar:,.2f} ({self.total_pnl_pct:+.2%})",
            f"  Worst Case:      ${self.worst_case_pnl_dollar:,.2f} ({self.worst_case_pnl_pct:+.2%})",
        ]
        if self.recovery_days_est is not None:
            lines.append(f"  Est. Recovery:   ~{self.recovery_days_est} days")
        if self.position_impacts:
            lines.append("  Position Impacts:")
            for pi in sorted(self.position_impacts, key=lambda x: x.pnl_dollar):
                lines.append(
                    f"    {pi.symbol:12s} {pi.shock_pct:+7.1%} -> "
                    f"${pi.pnl_dollar:+,.2f} ({pi.pnl_pct:+.2%})"
                )
        return "\n".join(lines)


class SensitivityRow(BaseModel):
    """One row in a sensitivity grid (one holding x one shock level)."""

    symbol: str
    asset_class: str
    shock_pct: float
    pnl_dollar: float
    pnl_pct_of_portfolio: float
    notional_before: float
    notional_after: float


class SensitivityReport(BaseModel):
    """Grid output from sensitivity analysis."""

    analysis_type: str  # "price_sensitivity" | "volatility_surface" | "correlation_breakdown"
    shock_levels: list[float]
    rows: list[SensitivityRow] = Field(default_factory=list)
    portfolio_value: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_summary(self) -> str:
        lines = [f"Sensitivity Analysis: {self.analysis_type}"]
        if not self.rows:
            lines.append("  No positions to analyze.")
            return "\n".join(lines)
        # Group by symbol
        symbols = sorted(set(r.symbol for r in self.rows))
        header = "  {:12s}".format("Symbol") + "".join(f"{s:+8.0%}" for s in self.shock_levels)
        lines.append(header)
        for sym in symbols:
            sym_rows = {r.shock_pct: r for r in self.rows if r.symbol == sym}
            vals = "".join(
                f"${sym_rows[s].pnl_dollar:+8,.0f}" if s in sym_rows else " " * 9
                for s in self.shock_levels
            )
            lines.append(f"  {sym:12s}{vals}")
        return "\n".join(lines)


class FullStressTestSuite(BaseModel):
    """Complete stress test output -- all scenarios + sensitivity grids."""

    scenario_reports: list[StressTestReport] = Field(default_factory=list)
    sensitivity_reports: list[SensitivityReport] = Field(default_factory=list)
    portfolio_value: float = 0.0
    worst_scenario_name: str = ""
    worst_scenario_pnl_pct: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════
#  Stress Testing Engine
# ═══════════════════════════════════════════

class StressTestEngine:
    """
    Runs stress tests against a PortfolioState.

    Usage:
        engine = StressTestEngine()
        suite = engine.run_full_suite(portfolio)
        print(suite.worst_scenario_name, suite.worst_scenario_pnl_pct)

        # Or run a single scenario:
        report = engine.run_scenario(portfolio, HISTORICAL_SCENARIOS[1])
    """

    # Default sensitivity shock levels
    PRICE_SHOCK_LEVELS: list[float] = [-0.30, -0.20, -0.10, +0.10, +0.20, +0.30]
    VOL_MULTIPLIERS: list[float] = [2.0, 3.0]
    CORRELATION_LEVELS: list[float] = [0.50, 0.70, 0.85, 0.95]

    # Estimated base spread by asset class (in bps)
    BASE_SPREAD_BPS: dict[str, float] = {
        AssetClass.BTC: 1.0,
        AssetClass.ETH: 2.0,
        AssetClass.ALT_LARGE: 5.0,
        AssetClass.ALT_MID: 15.0,
        AssetClass.MEME: 30.0,
        AssetClass.STABLECOIN: 0.5,
        AssetClass.EQUITY: 2.0,
    }

    def run_scenario(
        self,
        portfolio: PortfolioState,
        scenario: StressScenario,
    ) -> StressTestReport:
        """
        Apply a single stress scenario to the portfolio.

        For each position:
        1. Classify asset class
        2. Look up the shock for that class
        3. Compute dollar and % P&L
        4. Estimate spread/slippage cost under stressed liquidity
        5. Aggregate to portfolio level
        """
        total_value = portfolio.total_value
        if total_value <= 0:
            return StressTestReport(
                scenario_name=scenario.name,
                scenario_type=scenario.scenario_type.value,
                scenario_description=scenario.description,
                portfolio_value_before=0.0,
                portfolio_value_after=0.0,
                total_pnl_dollar=0.0,
                total_pnl_pct=0.0,
                worst_case_pnl_dollar=0.0,
                worst_case_pnl_pct=0.0,
                cash_before=portfolio.cash,
                cash_after=portfolio.cash,
                correlation_override=scenario.correlation_override,
                spread_multiplier=scenario.spread_multiplier,
                recovery_days_est=scenario.recovery_days_est,
            )

        position_impacts: list[PositionImpact] = []
        total_pnl = 0.0
        total_spread_cost = 0.0

        for pos in portfolio.positions:
            asset_class = classify_asset(pos.symbol)
            shock = scenario.shocks.get(asset_class, 0.0)

            # Handle special per-symbol overrides in metadata
            symbol_key = f"{pos.symbol.upper().replace('USDT', '')}_special_shock"
            if symbol_key.lower() in {
                k.lower() for k in scenario.metadata
            }:
                for k, v in scenario.metadata.items():
                    if k.lower() == symbol_key.lower():
                        shock = v
                        break

            notional = pos.notional_value
            # For long positions, shock applies directly
            # For short positions, a market drop is a gain
            if pos.side == OrderSide.BUY:
                pnl = notional * shock
            else:
                pnl = notional * (-shock)

            pnl_pct = shock if pos.side == OrderSide.BUY else -shock

            # Spread / slippage cost estimate for emergency exit
            base_spread = self.BASE_SPREAD_BPS.get(asset_class, 10.0)
            stressed_spread_bps = base_spread * scenario.spread_multiplier
            spread_cost = abs(notional) * (stressed_spread_bps / 10_000)

            position_impacts.append(
                PositionImpact(
                    symbol=pos.symbol,
                    asset_class=asset_class.value,
                    side=pos.side.value,
                    notional_before=notional,
                    shock_pct=shock,
                    pnl_dollar=pnl,
                    pnl_pct=pnl_pct,
                    notional_after=notional + pnl,
                    spread_cost_est=spread_cost,
                )
            )

            total_pnl += pnl
            total_spread_cost += spread_cost

        portfolio_after = total_value + total_pnl
        worst_case_pnl = total_pnl - total_spread_cost

        return StressTestReport(
            scenario_name=scenario.name,
            scenario_type=scenario.scenario_type.value,
            scenario_description=scenario.description,
            portfolio_value_before=total_value,
            portfolio_value_after=portfolio_after,
            total_pnl_dollar=total_pnl,
            total_pnl_pct=total_pnl / total_value if total_value else 0.0,
            worst_case_pnl_dollar=worst_case_pnl,
            worst_case_pnl_pct=worst_case_pnl / total_value if total_value else 0.0,
            position_impacts=position_impacts,
            correlation_override=scenario.correlation_override,
            spread_multiplier=scenario.spread_multiplier,
            recovery_days_est=scenario.recovery_days_est,
            cash_before=portfolio.cash,
            cash_after=portfolio.cash - total_spread_cost,
        )

    def run_all_scenarios(
        self,
        portfolio: PortfolioState,
        scenarios: list[StressScenario] | None = None,
    ) -> list[StressTestReport]:
        """Run all predefined scenarios (or a custom list) against the portfolio."""
        if scenarios is None:
            scenarios = ALL_SCENARIOS
        reports = []
        for scenario in scenarios:
            report = self.run_scenario(portfolio, scenario)
            reports.append(report)
            logger.info(
                "stress_scenario_complete",
                scenario=scenario.name,
                pnl_pct=f"{report.total_pnl_pct:+.2%}",
                worst_case_pct=f"{report.worst_case_pnl_pct:+.2%}",
            )
        return reports

    # -----------------------------------------------
    #  Sensitivity Analysis
    # -----------------------------------------------

    def price_sensitivity(
        self,
        portfolio: PortfolioState,
        shock_levels: list[float] | None = None,
    ) -> SensitivityReport:
        """
        P&L impact grid: every holding x every shock level.

        Default shock levels: +/-10%, +/-20%, +/-30%.
        """
        if shock_levels is None:
            shock_levels = self.PRICE_SHOCK_LEVELS
        total_value = portfolio.total_value

        rows: list[SensitivityRow] = []
        for pos in portfolio.positions:
            asset_class = classify_asset(pos.symbol)
            notional = pos.notional_value
            for shock in shock_levels:
                if pos.side == OrderSide.BUY:
                    pnl = notional * shock
                else:
                    pnl = notional * (-shock)
                rows.append(
                    SensitivityRow(
                        symbol=pos.symbol,
                        asset_class=asset_class.value,
                        shock_pct=shock,
                        pnl_dollar=pnl,
                        pnl_pct_of_portfolio=pnl / total_value if total_value else 0.0,
                        notional_before=notional,
                        notional_after=notional + pnl,
                    )
                )

        return SensitivityReport(
            analysis_type="price_sensitivity",
            shock_levels=sorted(shock_levels),
            rows=rows,
            portfolio_value=total_value,
        )

    def volatility_surface_shock(
        self,
        portfolio: PortfolioState,
        vol_multipliers: list[float] | None = None,
        base_daily_vol: dict[str, float] | None = None,
    ) -> SensitivityReport:
        """
        Estimate P&L impact if realized volatility doubles or triples.

        Uses a simplified model: if vol multiplies by N, the expected
        max adverse move over a holding period scales by sqrt(N) for
        a random walk, but in practice crisis vol produces directional
        moves. We model the 95th-percentile adverse daily move under
        each vol regime.

        `base_daily_vol` maps symbols to their current annualized vol
        (e.g., 0.60 for 60% annualized). If not provided, uses asset-
        class defaults.
        """
        if vol_multipliers is None:
            vol_multipliers = self.VOL_MULTIPLIERS

        # Default annualized volatilities by asset class
        default_vol: dict[str, float] = {
            AssetClass.BTC: 0.55,
            AssetClass.ETH: 0.70,
            AssetClass.ALT_LARGE: 0.85,
            AssetClass.ALT_MID: 1.10,
            AssetClass.MEME: 1.50,
            AssetClass.STABLECOIN: 0.02,
            AssetClass.EQUITY: 0.20,
        }

        total_value = portfolio.total_value
        # We model 1-day 95th percentile move = daily_vol * 1.645
        # daily_vol = annualized_vol / sqrt(252)
        sqrt_252 = np.sqrt(252)
        z_95 = 1.645

        shock_levels_out: list[float] = []
        rows: list[SensitivityRow] = []

        for mult in vol_multipliers:
            shock_levels_out.append(mult)
            for pos in portfolio.positions:
                asset_class = classify_asset(pos.symbol)
                if base_daily_vol and pos.symbol in base_daily_vol:
                    ann_vol = base_daily_vol[pos.symbol]
                else:
                    ann_vol = default_vol.get(asset_class, 0.80)

                daily_vol = ann_vol / sqrt_252
                stressed_daily_vol = daily_vol * mult
                adverse_move = stressed_daily_vol * z_95  # 95th pctile 1-day loss

                notional = pos.notional_value
                if pos.side == OrderSide.BUY:
                    pnl = -notional * adverse_move
                else:
                    pnl = -notional * adverse_move  # Vol hurts short too (gap risk)

                rows.append(
                    SensitivityRow(
                        symbol=pos.symbol,
                        asset_class=asset_class.value,
                        shock_pct=-adverse_move,
                        pnl_dollar=pnl,
                        pnl_pct_of_portfolio=pnl / total_value if total_value else 0.0,
                        notional_before=notional,
                        notional_after=notional + pnl,
                    )
                )

        return SensitivityReport(
            analysis_type="volatility_surface",
            shock_levels=shock_levels_out,
            rows=rows,
            portfolio_value=total_value,
        )

    def correlation_breakdown_matrix(
        self,
        portfolio: PortfolioState,
        returns_history: dict[str, list[float]] | None = None,
        correlation_levels: list[float] | None = None,
    ) -> SensitivityReport:
        """
        Model portfolio risk under different correlation regimes.

        For each correlation level, computes the portfolio VaR (95%)
        assuming all pairwise correlations equal that level. This shows
        how diversification benefit erodes as correlations rise.

        If `returns_history` is provided, uses actual position volatilities.
        Otherwise uses asset-class defaults.
        """
        if correlation_levels is None:
            correlation_levels = self.CORRELATION_LEVELS

        default_ann_vol: dict[str, float] = {
            AssetClass.BTC: 0.55,
            AssetClass.ETH: 0.70,
            AssetClass.ALT_LARGE: 0.85,
            AssetClass.ALT_MID: 1.10,
            AssetClass.MEME: 1.50,
            AssetClass.STABLECOIN: 0.02,
            AssetClass.EQUITY: 0.20,
        }
        sqrt_252 = np.sqrt(252)
        z_95 = 1.645

        total_value = portfolio.total_value
        if total_value <= 0 or not portfolio.positions:
            return SensitivityReport(
                analysis_type="correlation_breakdown",
                shock_levels=correlation_levels,
                portfolio_value=total_value,
            )

        # Build weight and vol vectors
        n = len(portfolio.positions)
        weights = np.zeros(n)
        daily_vols = np.zeros(n)

        for i, pos in enumerate(portfolio.positions):
            asset_class = classify_asset(pos.symbol)
            weights[i] = pos.notional_value / total_value

            if returns_history and pos.symbol in returns_history:
                rets = returns_history[pos.symbol]
                if len(rets) >= 5:
                    daily_vols[i] = float(np.std(rets))
                else:
                    daily_vols[i] = default_ann_vol.get(asset_class, 0.80) / sqrt_252
            else:
                daily_vols[i] = default_ann_vol.get(asset_class, 0.80) / sqrt_252

        rows: list[SensitivityRow] = []
        for rho in correlation_levels:
            # Build uniform correlation matrix
            corr = np.full((n, n), rho)
            np.fill_diagonal(corr, 1.0)

            # Covariance matrix: Sigma = diag(vol) @ Corr @ diag(vol)
            vol_diag = np.diag(daily_vols)
            cov = vol_diag @ corr @ vol_diag

            # Portfolio variance = w^T Sigma w
            port_var = float(weights @ cov @ weights)
            port_vol = np.sqrt(port_var)
            port_var_95 = port_vol * z_95  # 1-day 95% VaR as fraction

            pnl = -total_value * port_var_95

            # Report as a single portfolio-level row per correlation level
            rows.append(
                SensitivityRow(
                    symbol="PORTFOLIO",
                    asset_class="portfolio",
                    shock_pct=-port_var_95,
                    pnl_dollar=pnl,
                    pnl_pct_of_portfolio=-port_var_95,
                    notional_before=total_value,
                    notional_after=total_value + pnl,
                )
            )

        return SensitivityReport(
            analysis_type="correlation_breakdown",
            shock_levels=correlation_levels,
            rows=rows,
            portfolio_value=total_value,
        )

    # -----------------------------------------------
    #  Full Suite
    # -----------------------------------------------

    def run_full_suite(
        self,
        portfolio: PortfolioState,
        scenarios: list[StressScenario] | None = None,
        returns_history: dict[str, list[float]] | None = None,
        include_sensitivity: bool = True,
    ) -> FullStressTestSuite:
        """
        Run the complete stress test suite:
        1. All historical + hypothetical scenarios
        2. Price sensitivity grid
        3. Volatility surface shock
        4. Correlation breakdown matrix

        Returns a FullStressTestSuite with everything an LP or CRO needs.
        """
        # Scenario stress tests
        scenario_reports = self.run_all_scenarios(portfolio, scenarios)

        # Sensitivity analyses
        sensitivity_reports: list[SensitivityReport] = []
        if include_sensitivity:
            sensitivity_reports.append(self.price_sensitivity(portfolio))
            sensitivity_reports.append(self.volatility_surface_shock(portfolio))
            sensitivity_reports.append(
                self.correlation_breakdown_matrix(portfolio, returns_history)
            )

        # Find worst scenario
        worst_name = ""
        worst_pnl_pct = 0.0
        for report in scenario_reports:
            if report.worst_case_pnl_pct < worst_pnl_pct:
                worst_pnl_pct = report.worst_case_pnl_pct
                worst_name = report.scenario_name

        suite = FullStressTestSuite(
            scenario_reports=scenario_reports,
            sensitivity_reports=sensitivity_reports,
            portfolio_value=portfolio.total_value,
            worst_scenario_name=worst_name,
            worst_scenario_pnl_pct=worst_pnl_pct,
        )

        logger.info(
            "stress_test_suite_complete",
            num_scenarios=len(scenario_reports),
            num_sensitivity=len(sensitivity_reports),
            worst_scenario=worst_name,
            worst_pnl_pct=f"{worst_pnl_pct:+.2%}",
            portfolio_value=f"${portfolio.total_value:,.2f}",
        )

        return suite


# ═══════════════════════════════════════════
#  Convenience Constructor
# ═══════════════════════════════════════════

def build_custom_scenario(
    name: str,
    description: str,
    shocks: dict[str, float],
    correlation_override: float | None = None,
    spread_multiplier: float = 1.0,
    recovery_days_est: int | None = None,
) -> StressScenario:
    """
    Helper to build a custom stress scenario on-the-fly.

    `shocks` should map AssetClass value strings to fractional moves:
        {"btc": -0.20, "eth": -0.30, "alt_mid": -0.50}
    """
    return StressScenario(
        name=name,
        description=description,
        scenario_type=ScenarioType.HYPOTHETICAL,
        shocks=shocks,
        correlation_override=correlation_override,
        spread_multiplier=spread_multiplier,
        recovery_days_est=recovery_days_est,
    )
