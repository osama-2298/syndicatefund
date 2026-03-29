"""
Liquidity Analyzer — Position-Level & Portfolio-Level Liquidity Assessment.

Evaluates how quickly and cheaply a portfolio can be liquidated.
Critical for institutional risk management: illiquid positions
amplify losses during market stress.

Key metrics:
- Days to liquidate: position_size / (participation_rate * ADV)
- Liquidity score: composite of volume, spread, depth
- Stress exit time: liquidation time under reduced market conditions
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════
#  Models
# ═══════════════════════════════════════════


class LiquidityProfile(BaseModel):
    """Liquidity assessment for a single position."""
    symbol: str
    position_value: float  # current notional value of the position
    avg_daily_volume: float  # ADV in dollar terms
    bid_ask_spread: float  # as a fraction (e.g., 0.001 = 10 bps)
    depth_at_1pct: float  # dollar depth within 1% of mid price
    days_to_liquidate: float  # at standard participation rate
    liquidity_score: float = Field(
        ge=0.0, le=100.0,
        description="Composite score: 100 = extremely liquid, 0 = illiquid",
    )
    pct_of_adv: float  # position as % of average daily volume
    participation_rate: float  # assumed % of daily volume we can capture
    estimated_impact_cost: float  # market impact cost to liquidate (in dollars)


class PortfolioLiquidityReport(BaseModel):
    """Aggregate liquidity metrics for the full portfolio."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_portfolio_value: float
    weighted_avg_liquidity_score: float
    min_liquidity_score: float
    least_liquid_position: str
    total_days_to_liquidate: float  # max across positions (parallel liquidation)
    sequential_days_to_liquidate: float  # sum (sequential liquidation)
    pct_liquidable_1_day: float  # % of portfolio that can be sold in 1 day
    pct_liquidable_5_days: float
    total_estimated_impact: float  # total dollar impact cost
    impact_as_pct_of_portfolio: float
    position_profiles: list[LiquidityProfile] = Field(default_factory=list)


class LiquidationStep(BaseModel):
    """A single step in an optimal liquidation schedule."""
    day: int
    symbol: str
    quantity_to_sell: float
    notional_to_sell: float
    pct_of_position: float
    estimated_impact: float
    cumulative_liquidated_pct: float


class LiquidationSchedule(BaseModel):
    """Optimal exit schedule for large positions."""
    symbol: str
    total_position_value: float
    total_days: int
    participation_rate: float
    total_estimated_impact: float
    steps: list[LiquidationStep] = Field(default_factory=list)


class StressExitReport(BaseModel):
    """Portfolio exit time under stressed market conditions."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    stress_scenario: str
    volume_haircut: float  # e.g., 0.5 = volumes drop 50%
    spread_multiplier: float  # e.g., 3.0 = spreads widen 3x
    normal_exit_days: float
    stressed_exit_days: float
    normal_impact_cost: float
    stressed_impact_cost: float
    impact_increase_pct: float
    position_details: list[dict[str, Any]] = Field(default_factory=list)


# ═══════════════════════════════════════════
#  Liquidity Analyzer
# ═══════════════════════════════════════════


class LiquidityAnalyzer:
    """
    Assesses liquidity risk at the position and portfolio level.

    Uses average daily volume, bid-ask spreads, and order book depth
    to estimate liquidation costs and timelines.
    """

    def __init__(
        self,
        default_participation_rate: float = 0.10,  # trade up to 10% of ADV
        impact_exponent: float = 0.5,  # square-root impact model
        impact_coefficient: float = 0.1,  # market impact scaling factor
    ) -> None:
        self.default_participation_rate = default_participation_rate
        self.impact_exponent = impact_exponent
        self.impact_coefficient = impact_coefficient

    # ── Position Assessment ─────────────────

    def assess_position(
        self,
        symbol: str,
        position_value: float,
        avg_daily_volume: float,
        bid_ask_spread: float = 0.001,
        depth_at_1pct: float | None = None,
        participation_rate: float | None = None,
    ) -> LiquidityProfile:
        """
        Compute liquidity score and liquidation estimate for a single position.

        The liquidity score is a weighted composite:
        - 40% volume score: based on position as % of ADV
        - 30% spread score: based on bid-ask spread
        - 30% depth score: based on depth relative to position size

        Market impact is estimated using the square-root model:
            impact = coefficient * (position / ADV) ^ exponent * spread

        Args:
            symbol: Ticker symbol.
            position_value: Current position notional value in dollars.
            avg_daily_volume: Average daily dollar volume.
            bid_ask_spread: Bid-ask spread as fraction of mid price.
            depth_at_1pct: Dollar depth within 1% of mid price.
                If None, estimated as 5% of ADV.
            participation_rate: Max fraction of daily volume to trade.

        Returns:
            LiquidityProfile with scores and estimates.
        """
        part_rate = participation_rate or self.default_participation_rate
        adv = max(avg_daily_volume, 1.0)

        if depth_at_1pct is None:
            depth_at_1pct = adv * 0.05  # rough estimate

        # Position as % of ADV
        pct_of_adv = position_value / adv

        # Days to liquidate at participation rate
        daily_capacity = adv * part_rate
        days_to_liq = position_value / max(daily_capacity, 1.0)

        # Market impact: square-root model
        # impact_pct = coeff * sqrt(position / ADV) * spread_factor
        spread_factor = max(bid_ask_spread / 0.001, 1.0)  # normalize to 10 bps
        impact_pct = self.impact_coefficient * (pct_of_adv ** self.impact_exponent) * spread_factor
        impact_cost = position_value * impact_pct

        # Volume score (40%): penalizes large positions relative to volume
        # pct_of_adv < 0.05 = excellent, > 1.0 = terrible
        volume_score = float(np.clip(100 * (1.0 - np.log1p(pct_of_adv * 10) / np.log1p(20)), 0, 100))

        # Spread score (30%): penalizes wide spreads
        # spread < 5 bps = excellent, > 50 bps = terrible
        spread_bps = bid_ask_spread * 10000
        spread_score = float(np.clip(100 * (1.0 - spread_bps / 100), 0, 100))

        # Depth score (30%): position relative to available depth
        depth_ratio = position_value / max(depth_at_1pct, 1.0)
        depth_score = float(np.clip(100 * (1.0 - np.log1p(depth_ratio) / np.log1p(50)), 0, 100))

        liquidity_score = 0.40 * volume_score + 0.30 * spread_score + 0.30 * depth_score
        liquidity_score = round(float(np.clip(liquidity_score, 0, 100)), 1)

        return LiquidityProfile(
            symbol=symbol,
            position_value=round(position_value, 2),
            avg_daily_volume=round(adv, 2),
            bid_ask_spread=bid_ask_spread,
            depth_at_1pct=round(depth_at_1pct, 2),
            days_to_liquidate=round(days_to_liq, 2),
            liquidity_score=liquidity_score,
            pct_of_adv=round(pct_of_adv, 4),
            participation_rate=part_rate,
            estimated_impact_cost=round(impact_cost, 2),
        )

    # ── Portfolio Liquidity ─────────────────

    def portfolio_liquidity(
        self,
        positions: list[dict[str, Any]],
    ) -> PortfolioLiquidityReport:
        """
        Aggregate liquidity metrics across the full portfolio.

        Args:
            positions: List of dicts, each with keys:
                - symbol (str)
                - position_value (float)
                - avg_daily_volume (float)
                - bid_ask_spread (float, optional)
                - depth_at_1pct (float, optional)

        Returns:
            PortfolioLiquidityReport with weighted-average and worst-case metrics.
        """
        if not positions:
            return PortfolioLiquidityReport(
                total_portfolio_value=0.0,
                weighted_avg_liquidity_score=0.0,
                min_liquidity_score=0.0,
                least_liquid_position="N/A",
                total_days_to_liquidate=0.0,
                sequential_days_to_liquidate=0.0,
                pct_liquidable_1_day=100.0,
                pct_liquidable_5_days=100.0,
                total_estimated_impact=0.0,
                impact_as_pct_of_portfolio=0.0,
            )

        profiles: list[LiquidityProfile] = []
        for pos in positions:
            profile = self.assess_position(
                symbol=pos["symbol"],
                position_value=pos["position_value"],
                avg_daily_volume=pos["avg_daily_volume"],
                bid_ask_spread=pos.get("bid_ask_spread", 0.001),
                depth_at_1pct=pos.get("depth_at_1pct"),
            )
            profiles.append(profile)

        total_value = sum(p.position_value for p in profiles)
        total_value = max(total_value, 1.0)

        # Weighted average liquidity score
        weights = np.array([p.position_value for p in profiles])
        scores = np.array([p.liquidity_score for p in profiles])
        weighted_avg = float(np.average(scores, weights=weights)) if len(profiles) > 0 else 0.0

        # Worst position
        min_score_profile = min(profiles, key=lambda p: p.liquidity_score)

        # Days to liquidate (parallel = max, sequential = sum)
        max_days = max(p.days_to_liquidate for p in profiles)
        sum_days = sum(p.days_to_liquidate for p in profiles)

        # Percentage liquidable in 1 day and 5 days
        one_day_value = sum(
            min(p.position_value, p.avg_daily_volume * p.participation_rate)
            for p in profiles
        )
        five_day_value = sum(
            min(p.position_value, p.avg_daily_volume * p.participation_rate * 5)
            for p in profiles
        )
        pct_1d = min(one_day_value / total_value * 100, 100.0)
        pct_5d = min(five_day_value / total_value * 100, 100.0)

        # Total impact
        total_impact = sum(p.estimated_impact_cost for p in profiles)

        return PortfolioLiquidityReport(
            total_portfolio_value=round(total_value, 2),
            weighted_avg_liquidity_score=round(weighted_avg, 1),
            min_liquidity_score=round(min_score_profile.liquidity_score, 1),
            least_liquid_position=min_score_profile.symbol,
            total_days_to_liquidate=round(max_days, 2),
            sequential_days_to_liquidate=round(sum_days, 2),
            pct_liquidable_1_day=round(pct_1d, 1),
            pct_liquidable_5_days=round(pct_5d, 1),
            total_estimated_impact=round(total_impact, 2),
            impact_as_pct_of_portfolio=round(total_impact / total_value * 100, 4),
            position_profiles=profiles,
        )

    # ── Stress Exit Time ────────────────────

    def stress_exit_time(
        self,
        positions: list[dict[str, Any]],
        volume_haircut: float = 0.50,
        spread_multiplier: float = 3.0,
        scenario_name: str = "Market Stress",
    ) -> StressExitReport:
        """
        Estimate portfolio liquidation time under stressed conditions.

        During market stress:
        - Volumes drop (e.g., 50% haircut)
        - Spreads widen (e.g., 3x normal)
        - Market impact increases non-linearly

        Args:
            positions: Same format as portfolio_liquidity().
            volume_haircut: Volume reduction factor (0.5 = 50% drop).
            spread_multiplier: How much spreads widen.
            scenario_name: Label for the stress scenario.

        Returns:
            StressExitReport comparing normal vs stressed liquidation.
        """
        # Normal conditions
        normal_report = self.portfolio_liquidity(positions)

        # Stressed conditions: reduce volumes, widen spreads
        stressed_positions = []
        for pos in positions:
            stressed_pos = dict(pos)
            stressed_pos["avg_daily_volume"] = pos["avg_daily_volume"] * (1 - volume_haircut)
            stressed_pos["bid_ask_spread"] = pos.get("bid_ask_spread", 0.001) * spread_multiplier
            if "depth_at_1pct" in pos and pos["depth_at_1pct"] is not None:
                stressed_pos["depth_at_1pct"] = pos["depth_at_1pct"] * (1 - volume_haircut)
            stressed_positions.append(stressed_pos)

        stressed_report = self.portfolio_liquidity(stressed_positions)

        # Per-position comparison
        details = []
        for normal_p, stressed_p in zip(
            normal_report.position_profiles, stressed_report.position_profiles
        ):
            details.append({
                "symbol": normal_p.symbol,
                "normal_days": normal_p.days_to_liquidate,
                "stressed_days": stressed_p.days_to_liquidate,
                "normal_impact": normal_p.estimated_impact_cost,
                "stressed_impact": stressed_p.estimated_impact_cost,
                "normal_score": normal_p.liquidity_score,
                "stressed_score": stressed_p.liquidity_score,
            })

        normal_impact = normal_report.total_estimated_impact
        stressed_impact = stressed_report.total_estimated_impact
        impact_increase = (
            (stressed_impact - normal_impact) / max(normal_impact, 1.0) * 100
        )

        return StressExitReport(
            stress_scenario=scenario_name,
            volume_haircut=volume_haircut,
            spread_multiplier=spread_multiplier,
            normal_exit_days=normal_report.total_days_to_liquidate,
            stressed_exit_days=stressed_report.total_days_to_liquidate,
            normal_impact_cost=round(normal_impact, 2),
            stressed_impact_cost=round(stressed_impact, 2),
            impact_increase_pct=round(impact_increase, 1),
            position_details=details,
        )

    # ── Concentration vs Volume ─────────────

    def concentration_vs_volume(
        self,
        positions: list[dict[str, Any]],
        warning_threshold: float = 0.25,
        critical_threshold: float = 1.0,
    ) -> list[dict[str, Any]]:
        """
        Analyze position size as percentage of average daily volume.

        Large positions relative to ADV create liquidation risk:
        - < 10% ADV: negligible impact
        - 10-25% ADV: moderate (may take 1-3 days)
        - 25-100% ADV: significant (multi-day exit, noticeable impact)
        - > 100% ADV: critical (market-moving, needs careful unwinding)

        Args:
            positions: List of dicts with symbol, position_value, avg_daily_volume.
            warning_threshold: % of ADV to flag as warning (default 25%).
            critical_threshold: % of ADV to flag as critical (default 100%).

        Returns:
            List of dicts with concentration analysis, sorted by severity.
        """
        results = []
        for pos in positions:
            adv = max(pos["avg_daily_volume"], 1.0)
            pct_of_adv = pos["position_value"] / adv

            if pct_of_adv >= critical_threshold:
                severity = "CRITICAL"
            elif pct_of_adv >= warning_threshold:
                severity = "WARNING"
            else:
                severity = "OK"

            results.append({
                "symbol": pos["symbol"],
                "position_value": round(pos["position_value"], 2),
                "avg_daily_volume": round(adv, 2),
                "pct_of_adv": round(pct_of_adv * 100, 2),
                "days_to_exit_10pct": round(pos["position_value"] / (adv * 0.10), 1),
                "days_to_exit_25pct": round(pos["position_value"] / (adv * 0.25), 1),
                "severity": severity,
            })

        # Sort: CRITICAL first, then WARNING, then OK; within each, by pct_of_adv desc
        severity_order = {"CRITICAL": 0, "WARNING": 1, "OK": 2}
        results.sort(key=lambda r: (severity_order[r["severity"]], -r["pct_of_adv"]))
        return results

    # ── Liquidation Schedule ────────────────

    def liquidation_schedule(
        self,
        symbol: str,
        position_value: float,
        current_price: float,
        avg_daily_volume: float,
        bid_ask_spread: float = 0.001,
        participation_rate: float | None = None,
        max_days: int = 30,
    ) -> LiquidationSchedule:
        """
        Generate an optimal exit schedule for a large position.

        Uses a VWAP-style approach: trade a fixed percentage of daily volume
        each day, with decreasing market impact as position shrinks.

        The schedule front-loads liquidation slightly to reduce risk of
        adverse price moves while the position is still large.

        Args:
            symbol: Ticker symbol.
            position_value: Total notional to liquidate.
            current_price: Current price per unit.
            avg_daily_volume: Average daily dollar volume.
            bid_ask_spread: Current bid-ask spread.
            participation_rate: Override for max daily participation.
            max_days: Maximum days for the schedule.

        Returns:
            LiquidationSchedule with day-by-day instructions.
        """
        part_rate = participation_rate or self.default_participation_rate
        adv = max(avg_daily_volume, 1.0)
        daily_capacity = adv * part_rate

        total_quantity = position_value / max(current_price, 0.01)
        remaining_value = position_value
        remaining_qty = total_quantity
        steps: list[LiquidationStep] = []
        total_impact = 0.0
        cumulative_pct = 0.0

        for day in range(1, max_days + 1):
            if remaining_value <= 0:
                break

            # Daily sell amount: min of daily capacity and remaining
            # Front-load slightly: first days sell up to 120% of normal rate
            front_load_factor = 1.0 + 0.2 * max(0, 1.0 - day / 5)
            day_capacity = min(daily_capacity * front_load_factor, remaining_value)
            day_qty = day_capacity / max(current_price, 0.01)

            # Market impact for this day's trade
            day_pct_of_adv = day_capacity / adv
            spread_factor = max(bid_ask_spread / 0.001, 1.0)
            day_impact_pct = (
                self.impact_coefficient
                * (day_pct_of_adv ** self.impact_exponent)
                * spread_factor
            )
            day_impact = day_capacity * day_impact_pct
            total_impact += day_impact

            pct_of_position = day_capacity / max(position_value, 1.0) * 100
            cumulative_pct += pct_of_position

            steps.append(LiquidationStep(
                day=day,
                symbol=symbol,
                quantity_to_sell=round(day_qty, 8),
                notional_to_sell=round(day_capacity, 2),
                pct_of_position=round(pct_of_position, 2),
                estimated_impact=round(day_impact, 2),
                cumulative_liquidated_pct=round(min(cumulative_pct, 100.0), 2),
            ))

            remaining_value -= day_capacity
            remaining_qty -= day_qty

        return LiquidationSchedule(
            symbol=symbol,
            total_position_value=round(position_value, 2),
            total_days=len(steps),
            participation_rate=part_rate,
            total_estimated_impact=round(total_impact, 2),
            steps=steps,
        )
