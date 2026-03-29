"""
Liquidity Risk Analyzer.

Assesses liquidity risk per position and across the portfolio:

  - Position-level liquidity scoring (0-100) based on ADV, spread, depth
  - Portfolio-level weighted aggregate score
  - Max position size enforcement (<=5% of ADV)
  - Stress exit analysis (time to liquidate under normal vs. stress)
  - Bid-ask spread monitoring with widening alerts
  - Dynamic slippage estimation replacing hardcoded constants
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from enum import Enum

import structlog
from pydantic import BaseModel, Field

from syndicate.data.models import PortfolioState

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

MAX_PARTICIPATION_RATE = 0.05   # never trade > 5% of ADV
STRESS_VOLUME_MULTIPLIER = 0.3  # in stress, effective volume drops to 30%
STRESS_SPREAD_MULTIPLIER = 3.0  # spreads widen 3x in stress

# Scoring weights (must sum to 1.0)
_W_ADV = 0.35
_W_SPREAD = 0.30
_W_DEPTH = 0.20
_W_PARTICIPATION = 0.15


# ---------------------------------------------------------------------------
#  Enums
# ---------------------------------------------------------------------------


class LiquidityTier(str, Enum):
    """Liquidity classification."""
    EXCELLENT = "excellent"   # score >= 80
    GOOD = "good"             # score >= 60
    MODERATE = "moderate"     # score >= 40
    POOR = "poor"             # score >= 20
    CRITICAL = "critical"     # score < 20


# ---------------------------------------------------------------------------
#  Pydantic models
# ---------------------------------------------------------------------------


class LiquidityMetrics(BaseModel):
    """Liquidity metrics for a single position or symbol."""

    symbol: str
    avg_daily_volume_usd: float = 0.0
    bid_ask_spread_bps: float = 0.0       # basis points
    market_depth_1pct: float = 0.0        # USD available within 1% of mid
    days_to_liquidate: float = 0.0        # at normal participation rate
    participation_rate: float = 0.0       # position_usd / adv
    liquidity_score: float = 0.0          # 0-100 composite
    tier: LiquidityTier = LiquidityTier.MODERATE
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StressExitResult(BaseModel):
    """Time and cost to exit a position under normal and stress conditions."""

    symbol: str
    position_usd: float
    normal_days_to_exit: float = 0.0
    normal_slippage_bps: float = 0.0
    normal_total_cost_usd: float = 0.0
    stress_days_to_exit: float = 0.0
    stress_slippage_bps: float = 0.0
    stress_total_cost_usd: float = 0.0


class SpreadAlert(BaseModel):
    """Alert when bid-ask spread widens significantly."""

    symbol: str
    current_spread_bps: float
    baseline_spread_bps: float
    widening_ratio: float
    severity: str  # "warning", "critical"
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PortfolioLiquidityReport(BaseModel):
    """Aggregate liquidity assessment for the whole portfolio."""

    portfolio_score: float = 0.0
    tier: LiquidityTier = LiquidityTier.MODERATE
    position_metrics: list[LiquidityMetrics] = Field(default_factory=list)
    illiquid_positions: list[str] = Field(default_factory=list)
    total_days_to_liquidate: float = 0.0
    spread_alerts: list[SpreadAlert] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SlippageEstimate(BaseModel):
    """Dynamic slippage estimate for a proposed trade."""

    symbol: str
    trade_size_usd: float
    estimated_slippage_bps: float = 0.0
    estimated_slippage_usd: float = 0.0
    participation_rate: float = 0.0
    confidence: str = "medium"  # low, medium, high


# ---------------------------------------------------------------------------
#  Scoring helpers
# ---------------------------------------------------------------------------

def _score_adv(adv_usd: float) -> float:
    """Score ADV on 0-100 scale.

    Thresholds (crypto-market calibrated):
      >= $500M  -> 100
      >= $100M  -> 85
      >= $20M   -> 65
      >= $5M    -> 45
      >= $1M    -> 25
      < $1M     -> 5
    """
    if adv_usd >= 500_000_000:
        return 100.0
    if adv_usd >= 100_000_000:
        return 85.0 + 15.0 * (adv_usd - 100_000_000) / 400_000_000
    if adv_usd >= 20_000_000:
        return 65.0 + 20.0 * (adv_usd - 20_000_000) / 80_000_000
    if adv_usd >= 5_000_000:
        return 45.0 + 20.0 * (adv_usd - 5_000_000) / 15_000_000
    if adv_usd >= 1_000_000:
        return 25.0 + 20.0 * (adv_usd - 1_000_000) / 4_000_000
    return max(5.0, 25.0 * adv_usd / 1_000_000)


def _score_spread(spread_bps: float) -> float:
    """Score bid-ask spread on 0-100 scale (lower spread = higher score).

      <= 2 bps  -> 100
      <= 5 bps  -> 85
      <= 15 bps -> 65
      <= 50 bps -> 40
      <= 150 bps -> 15
      > 150 bps -> 5
    """
    if spread_bps <= 2:
        return 100.0
    if spread_bps <= 5:
        return 85.0 + 15.0 * (5 - spread_bps) / 3
    if spread_bps <= 15:
        return 65.0 + 20.0 * (15 - spread_bps) / 10
    if spread_bps <= 50:
        return 40.0 + 25.0 * (50 - spread_bps) / 35
    if spread_bps <= 150:
        return 15.0 + 25.0 * (150 - spread_bps) / 100
    return 5.0


def _score_depth(depth_usd: float) -> float:
    """Score market depth (USD within 1% of mid) on 0-100 scale.

      >= $10M  -> 100
      >= $2M   -> 80
      >= $500K -> 55
      >= $100K -> 30
      < $100K  -> 10
    """
    if depth_usd >= 10_000_000:
        return 100.0
    if depth_usd >= 2_000_000:
        return 80.0 + 20.0 * (depth_usd - 2_000_000) / 8_000_000
    if depth_usd >= 500_000:
        return 55.0 + 25.0 * (depth_usd - 500_000) / 1_500_000
    if depth_usd >= 100_000:
        return 30.0 + 25.0 * (depth_usd - 100_000) / 400_000
    return max(10.0, 30.0 * depth_usd / 100_000)


def _score_participation(rate: float) -> float:
    """Score participation rate on 0-100 (lower = better).

      <= 0.5% -> 100
      <= 1%   -> 85
      <= 2%   -> 65
      <= 5%   -> 40
      > 5%    -> 10
    """
    if rate <= 0.005:
        return 100.0
    if rate <= 0.01:
        return 85.0 + 15.0 * (0.01 - rate) / 0.005
    if rate <= 0.02:
        return 65.0 + 20.0 * (0.02 - rate) / 0.01
    if rate <= 0.05:
        return 40.0 + 25.0 * (0.05 - rate) / 0.03
    return 10.0


def _tier_from_score(score: float) -> LiquidityTier:
    if score >= 80:
        return LiquidityTier.EXCELLENT
    if score >= 60:
        return LiquidityTier.GOOD
    if score >= 40:
        return LiquidityTier.MODERATE
    if score >= 20:
        return LiquidityTier.POOR
    return LiquidityTier.CRITICAL


# ---------------------------------------------------------------------------
#  Liquidity Risk Analyzer
# ---------------------------------------------------------------------------


class LiquidityRiskAnalyzer:
    """Assess and monitor liquidity risk across positions and the portfolio.

    Typical usage:
        analyzer = LiquidityRiskAnalyzer()
        metrics = analyzer.assess_position_liquidity("BTCUSDT", position_usd, market_data)
        report = analyzer.portfolio_liquidity_score(portfolio, market_data_map)
    """

    def __init__(
        self,
        max_participation_rate: float = MAX_PARTICIPATION_RATE,
        spread_warning_ratio: float = 2.0,
        spread_critical_ratio: float = 4.0,
    ) -> None:
        self.max_participation_rate = max_participation_rate
        self.spread_warning_ratio = spread_warning_ratio
        self.spread_critical_ratio = spread_critical_ratio
        # Track baseline spreads for widening detection
        self._baseline_spreads: dict[str, float] = {}

    # ------------------------------------------------------------------
    #  Position-level liquidity assessment
    # ------------------------------------------------------------------

    def assess_position_liquidity(
        self,
        symbol: str,
        position_usd: float,
        avg_daily_volume_usd: float,
        bid_ask_spread_bps: float = 10.0,
        market_depth_1pct_usd: float = 0.0,
    ) -> LiquidityMetrics:
        """Score a single position's liquidity on 0-100.

        Args:
            symbol: Trading pair, e.g. "BTCUSDT".
            position_usd: Current position notional in USD.
            avg_daily_volume_usd: 20-day average daily volume in USD.
            bid_ask_spread_bps: Current bid-ask spread in basis points.
            market_depth_1pct_usd: USD available within 1% of mid price on the book.

        Returns:
            LiquidityMetrics with composite score and component data.
        """
        adv = max(avg_daily_volume_usd, 1.0)
        participation = position_usd / adv if adv > 0 else 1.0
        days_to_liq = position_usd / (adv * self.max_participation_rate) if adv > 0 else 999.0

        # If depth not provided, estimate from ADV (rough heuristic)
        depth = market_depth_1pct_usd if market_depth_1pct_usd > 0 else adv * 0.02

        # Component scores
        s_adv = _score_adv(adv)
        s_spread = _score_spread(bid_ask_spread_bps)
        s_depth = _score_depth(depth)
        s_part = _score_participation(participation)

        composite = (
            _W_ADV * s_adv
            + _W_SPREAD * s_spread
            + _W_DEPTH * s_depth
            + _W_PARTICIPATION * s_part
        )
        composite = round(min(100.0, max(0.0, composite)), 1)

        # Update baseline spread
        if symbol not in self._baseline_spreads:
            self._baseline_spreads[symbol] = bid_ask_spread_bps
        else:
            # Exponential moving average for baseline
            self._baseline_spreads[symbol] = (
                0.95 * self._baseline_spreads[symbol] + 0.05 * bid_ask_spread_bps
            )

        metrics = LiquidityMetrics(
            symbol=symbol,
            avg_daily_volume_usd=adv,
            bid_ask_spread_bps=round(bid_ask_spread_bps, 2),
            market_depth_1pct=depth,
            days_to_liquidate=round(days_to_liq, 2),
            participation_rate=round(participation, 6),
            liquidity_score=composite,
            tier=_tier_from_score(composite),
        )

        logger.debug(
            "liquidity_assessed",
            symbol=symbol,
            score=composite,
            tier=metrics.tier.value,
            participation=round(participation, 4),
            days_to_liq=round(days_to_liq, 2),
        )
        return metrics

    # ------------------------------------------------------------------
    #  Portfolio-level aggregate
    # ------------------------------------------------------------------

    def portfolio_liquidity_score(
        self,
        portfolio: PortfolioState,
        market_data: dict[str, dict],
    ) -> PortfolioLiquidityReport:
        """Compute a weighted aggregate liquidity score for the portfolio.

        Args:
            portfolio: Current portfolio state.
            market_data: {symbol: {"adv_usd": float, "spread_bps": float, "depth_1pct": float}}

        Returns:
            PortfolioLiquidityReport.
        """
        total_value = portfolio.total_value
        if total_value <= 0 or not portfolio.positions:
            return PortfolioLiquidityReport(portfolio_score=100.0, tier=LiquidityTier.EXCELLENT)

        metrics_list: list[LiquidityMetrics] = []
        weighted_score = 0.0
        total_weight = 0.0
        illiquid: list[str] = []
        max_days = 0.0

        for pos in portfolio.positions:
            sym = pos.symbol
            pos_usd = abs(pos.notional_value)
            data = market_data.get(sym, {})

            m = self.assess_position_liquidity(
                symbol=sym,
                position_usd=pos_usd,
                avg_daily_volume_usd=data.get("adv_usd", 0.0),
                bid_ask_spread_bps=data.get("spread_bps", 20.0),
                market_depth_1pct_usd=data.get("depth_1pct", 0.0),
            )
            metrics_list.append(m)

            weight = pos_usd / total_value if total_value > 0 else 0.0
            weighted_score += m.liquidity_score * weight
            total_weight += weight

            if m.tier in (LiquidityTier.POOR, LiquidityTier.CRITICAL):
                illiquid.append(sym)

            max_days = max(max_days, m.days_to_liquidate)

        portfolio_score = round(weighted_score / total_weight, 1) if total_weight > 0 else 0.0

        # Check for spread alerts
        alerts = self._check_spread_alerts(metrics_list)

        report = PortfolioLiquidityReport(
            portfolio_score=portfolio_score,
            tier=_tier_from_score(portfolio_score),
            position_metrics=metrics_list,
            illiquid_positions=illiquid,
            total_days_to_liquidate=round(max_days, 2),
            spread_alerts=alerts,
        )

        logger.info(
            "portfolio_liquidity",
            score=portfolio_score,
            tier=report.tier.value,
            n_illiquid=len(illiquid),
            max_exit_days=round(max_days, 1),
            alerts=len(alerts),
        )
        return report

    # ------------------------------------------------------------------
    #  Max position by ADV
    # ------------------------------------------------------------------

    def max_position_by_adv(
        self,
        avg_daily_volume_usd: float,
        participation_rate: float | None = None,
    ) -> float:
        """Return the maximum position size (USD) based on ADV constraint.

        Position must be <= participation_rate * ADV so it can be exited
        in a single day without excessive market impact.
        """
        rate = participation_rate or self.max_participation_rate
        return avg_daily_volume_usd * rate

    def check_position_adv_limit(
        self,
        symbol: str,
        proposed_position_usd: float,
        avg_daily_volume_usd: float,
    ) -> tuple[bool, float, str]:
        """Check if a proposed position respects the ADV limit.

        Returns:
            (allowed, max_allowed_usd, reason)
        """
        max_usd = self.max_position_by_adv(avg_daily_volume_usd)
        if proposed_position_usd <= max_usd:
            return True, max_usd, "OK"

        return (
            False,
            max_usd,
            f"{symbol}: proposed ${proposed_position_usd:,.0f} exceeds "
            f"{self.max_participation_rate:.0%} of ADV (${avg_daily_volume_usd:,.0f}). "
            f"Max allowed: ${max_usd:,.0f}",
        )

    # ------------------------------------------------------------------
    #  Stress exit analysis
    # ------------------------------------------------------------------

    def stress_exit_analysis(
        self,
        symbol: str,
        position_usd: float,
        avg_daily_volume_usd: float,
        bid_ask_spread_bps: float = 10.0,
    ) -> StressExitResult:
        """Estimate time and cost to exit under normal vs. stress conditions.

        Normal: trade at max_participation_rate with current spread.
        Stress: volume drops to 30%, spreads widen 3x, slippage doubles.
        """
        adv = max(avg_daily_volume_usd, 1.0)

        # Normal
        normal_daily_capacity = adv * self.max_participation_rate
        normal_days = position_usd / normal_daily_capacity if normal_daily_capacity > 0 else 999.0
        normal_slip = self._estimate_slippage_bps(position_usd, adv, bid_ask_spread_bps)
        normal_cost = position_usd * (normal_slip + bid_ask_spread_bps / 2) / 10_000

        # Stress
        stress_adv = adv * STRESS_VOLUME_MULTIPLIER
        stress_daily_capacity = stress_adv * self.max_participation_rate
        stress_days = position_usd / stress_daily_capacity if stress_daily_capacity > 0 else 999.0
        stress_spread = bid_ask_spread_bps * STRESS_SPREAD_MULTIPLIER
        stress_slip = self._estimate_slippage_bps(position_usd, stress_adv, stress_spread)
        stress_cost = position_usd * (stress_slip + stress_spread / 2) / 10_000

        result = StressExitResult(
            symbol=symbol,
            position_usd=position_usd,
            normal_days_to_exit=round(normal_days, 2),
            normal_slippage_bps=round(normal_slip, 2),
            normal_total_cost_usd=round(normal_cost, 2),
            stress_days_to_exit=round(stress_days, 2),
            stress_slippage_bps=round(stress_slip, 2),
            stress_total_cost_usd=round(stress_cost, 2),
        )

        logger.debug(
            "stress_exit_analysis",
            symbol=symbol,
            normal_days=round(normal_days, 1),
            stress_days=round(stress_days, 1),
            stress_cost_usd=round(stress_cost, 0),
        )
        return result

    # ------------------------------------------------------------------
    #  Spread monitor
    # ------------------------------------------------------------------

    def spread_monitor(
        self,
        symbol: str,
        current_spread_bps: float,
    ) -> SpreadAlert | None:
        """Track bid-ask widening as an early warning signal.

        Compares current spread against the EMA baseline for this symbol.
        Returns an alert if the ratio exceeds warning/critical thresholds.
        """
        baseline = self._baseline_spreads.get(symbol)
        if baseline is None or baseline <= 0:
            # First observation: set baseline, no alert
            self._baseline_spreads[symbol] = current_spread_bps
            return None

        ratio = current_spread_bps / baseline if baseline > 0 else 1.0

        # Update baseline with EMA
        self._baseline_spreads[symbol] = 0.95 * baseline + 0.05 * current_spread_bps

        if ratio >= self.spread_critical_ratio:
            alert = SpreadAlert(
                symbol=symbol,
                current_spread_bps=round(current_spread_bps, 2),
                baseline_spread_bps=round(baseline, 2),
                widening_ratio=round(ratio, 2),
                severity="critical",
                message=(
                    f"{symbol} spread {current_spread_bps:.1f}bps is {ratio:.1f}x baseline "
                    f"({baseline:.1f}bps) — CRITICAL liquidity deterioration"
                ),
            )
            logger.warning("spread_critical", symbol=symbol, ratio=round(ratio, 1))
            return alert

        if ratio >= self.spread_warning_ratio:
            alert = SpreadAlert(
                symbol=symbol,
                current_spread_bps=round(current_spread_bps, 2),
                baseline_spread_bps=round(baseline, 2),
                widening_ratio=round(ratio, 2),
                severity="warning",
                message=(
                    f"{symbol} spread {current_spread_bps:.1f}bps is {ratio:.1f}x baseline "
                    f"({baseline:.1f}bps) — spread widening detected"
                ),
            )
            logger.info("spread_warning", symbol=symbol, ratio=round(ratio, 1))
            return alert

        return None

    def _check_spread_alerts(self, metrics: list[LiquidityMetrics]) -> list[SpreadAlert]:
        """Check for spread alerts across all assessed positions."""
        alerts: list[SpreadAlert] = []
        for m in metrics:
            alert = self.spread_monitor(m.symbol, m.bid_ask_spread_bps)
            if alert is not None:
                alerts.append(alert)
        return alerts

    # ------------------------------------------------------------------
    #  Dynamic slippage estimation
    # ------------------------------------------------------------------

    def dynamic_slippage_estimate(
        self,
        symbol: str,
        trade_size_usd: float,
        avg_daily_volume_usd: float,
        bid_ask_spread_bps: float = 10.0,
        market_depth_1pct_usd: float = 0.0,
    ) -> SlippageEstimate:
        """Volume-aware slippage model replacing hardcoded constants.

        The model combines three components:
          1. Half-spread cost (always paid)
          2. Market impact: Kyle's lambda model ~ sigma * sqrt(trade/ADV)
          3. Depth penalty when trade exceeds available book depth

        Returns a SlippageEstimate with the total expected slippage in bps.
        """
        adv = max(avg_daily_volume_usd, 1.0)
        participation = trade_size_usd / adv

        slip_bps = self._estimate_slippage_bps(
            trade_size_usd, adv, bid_ask_spread_bps, market_depth_1pct_usd,
        )
        slip_usd = trade_size_usd * slip_bps / 10_000

        # Confidence based on data quality
        if market_depth_1pct_usd > 0 and avg_daily_volume_usd > 1_000_000:
            confidence = "high"
        elif avg_daily_volume_usd > 100_000:
            confidence = "medium"
        else:
            confidence = "low"

        estimate = SlippageEstimate(
            symbol=symbol,
            trade_size_usd=trade_size_usd,
            estimated_slippage_bps=round(slip_bps, 2),
            estimated_slippage_usd=round(slip_usd, 2),
            participation_rate=round(participation, 6),
            confidence=confidence,
        )

        logger.debug(
            "slippage_estimate",
            symbol=symbol,
            size_usd=round(trade_size_usd, 0),
            slippage_bps=round(slip_bps, 2),
            participation=round(participation, 4),
            confidence=confidence,
        )
        return estimate

    @staticmethod
    def _estimate_slippage_bps(
        trade_size_usd: float,
        adv_usd: float,
        spread_bps: float = 10.0,
        depth_usd: float = 0.0,
    ) -> float:
        """Core slippage model in basis points.

        Components:
          1. Half-spread: spread_bps / 2
          2. Market impact (Kyle's lambda): k * sqrt(trade / adv)
             k calibrated to ~10bps at 1% participation for typical crypto
          3. Depth penalty: additional cost when trade > book depth
        """
        if adv_usd <= 0:
            return spread_bps  # no volume data, return full spread

        # 1. Half-spread
        half_spread = spread_bps / 2.0

        # 2. Market impact
        participation = trade_size_usd / adv_usd
        # Calibration: at participation=0.01 (1%), impact ~= 10bps
        kyle_k = 100.0  # sqrt(0.01) * 100 = 10 bps
        impact = kyle_k * math.sqrt(participation)

        # 3. Depth penalty
        depth_penalty = 0.0
        if depth_usd > 0 and trade_size_usd > depth_usd:
            overshoot = (trade_size_usd - depth_usd) / depth_usd
            depth_penalty = overshoot * 20.0  # 20bps per 100% overshoot

        total = half_spread + impact + depth_penalty
        return max(total, half_spread)  # never less than half-spread
