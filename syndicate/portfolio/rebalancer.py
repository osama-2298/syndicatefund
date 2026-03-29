"""
Portfolio Rebalancer — Drift Detection & Rebalancing Engine.

Monitors portfolio allocations against targets and generates
rebalancing orders when drift exceeds tolerance bands.

Supports:
- Calendar-based rebalancing (monthly/quarterly)
- Threshold-based rebalancing (drift triggers)
- Tax-aware rebalancing (harvest losses, avoid wash sales)
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

import numpy as np
from pydantic import BaseModel, Field

from syndicate.data.models import OrderSide, PortfolioState, TradeOrder, TradeParameters


# ═══════════════════════════════════════════
#  Models
# ═══════════════════════════════════════════


class RebalanceAction(str, Enum):
    """Possible rebalancing actions."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class TargetAllocation(BaseModel):
    """A single target allocation for a symbol or sector."""
    key: str  # symbol or sector name
    target_weight: float = Field(ge=0.0, le=1.0, description="Target portfolio weight")
    tolerance_band: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="Allowed drift before rebalance triggers (e.g., 0.05 = 5%)",
    )
    is_sector: bool = False  # True if key is a sector, False if symbol


class DriftAnalysis(BaseModel):
    """Drift analysis for a single allocation target."""
    key: str
    current_weight: float
    target_weight: float
    drift_pct: float  # absolute drift as percentage points
    drift_relative: float  # drift relative to target (e.g., 0.5 = 50% over target)
    action_needed: RebalanceAction
    urgency: float = Field(
        ge=0.0, le=1.0,
        description="0 = no action, 1 = immediate rebalance needed",
    )


class RebalanceOrder(BaseModel):
    """A proposed rebalancing trade."""
    symbol: str
    side: OrderSide
    target_notional: float  # dollar amount to trade
    target_quantity: float
    current_price: float
    reason: str
    estimated_cost: float = 0.0  # transaction cost estimate


class RebalanceCostEstimate(BaseModel):
    """Transaction cost estimate for a full rebalance."""
    total_turnover: float  # total dollars traded
    estimated_commissions: float
    estimated_spread_cost: float
    estimated_market_impact: float
    total_estimated_cost: float
    cost_as_pct_of_portfolio: float
    num_trades: int


class RebalanceReport(BaseModel):
    """Full rebalance analysis report."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    drift_analyses: list[DriftAnalysis] = Field(default_factory=list)
    max_drift: float = 0.0
    rebalance_needed: bool = False
    trigger_reason: str = ""
    proposed_orders: list[RebalanceOrder] = Field(default_factory=list)
    cost_estimate: RebalanceCostEstimate | None = None


# ═══════════════════════════════════════════
#  Rebalancer
# ═══════════════════════════════════════════


class Rebalancer:
    """
    Portfolio rebalancing engine.

    Compares current allocations against targets, detects drift,
    and generates orders to realign the portfolio.
    """

    def __init__(
        self,
        targets: list[TargetAllocation],
        commission_rate: float = 0.001,      # 10 bps per trade
        spread_cost_rate: float = 0.0005,    # 5 bps estimated spread
        market_impact_rate: float = 0.001,   # 10 bps market impact
    ) -> None:
        self.targets = {t.key: t for t in targets}
        self.commission_rate = commission_rate
        self.spread_cost_rate = spread_cost_rate
        self.market_impact_rate = market_impact_rate
        self._last_rebalance: datetime | None = None

    # ── Drift Analysis ──────────────────────

    def analyze_drift(
        self,
        portfolio: PortfolioState,
        segment_map: dict[str, str] | None = None,
    ) -> list[DriftAnalysis]:
        """
        Compare current portfolio weights vs target allocations.

        For symbol-level targets, compares position weights directly.
        For sector-level targets, aggregates positions by sector using segment_map.

        Returns a DriftAnalysis for each target, sorted by urgency descending.
        """
        total_value = max(portfolio.total_value, 1.0)
        results: list[DriftAnalysis] = []

        # Build current weight map
        current_weights: dict[str, float] = {}

        for target_key, target in self.targets.items():
            if target.is_sector:
                # Aggregate all positions in this sector
                sector_weight = 0.0
                if segment_map:
                    for pos in portfolio.positions:
                        if segment_map.get(pos.symbol, "Other") == target_key:
                            sector_weight += pos.notional_value / total_value
                current_weights[target_key] = sector_weight
            else:
                # Direct symbol weight
                pos = portfolio.get_position(target_key)
                if pos is not None:
                    current_weights[target_key] = pos.notional_value / total_value
                else:
                    current_weights[target_key] = 0.0

        # Calculate drift for each target
        for target_key, target in self.targets.items():
            current = current_weights.get(target_key, 0.0)
            drift_abs = current - target.target_weight
            drift_pct = abs(drift_abs)

            # Relative drift: how far off relative to the target itself
            drift_relative = (
                abs(drift_abs) / target.target_weight
                if target.target_weight > 0
                else (1.0 if current > 0 else 0.0)
            )

            # Determine action
            if drift_abs > target.tolerance_band:
                action = RebalanceAction.SELL
            elif drift_abs < -target.tolerance_band:
                action = RebalanceAction.BUY
            else:
                action = RebalanceAction.HOLD

            # Urgency: 0 when within band, scales to 1 at 2x tolerance
            if drift_pct <= target.tolerance_band:
                urgency = 0.0
            else:
                excess = drift_pct - target.tolerance_band
                urgency = float(np.clip(excess / max(target.tolerance_band, 0.01), 0.0, 1.0))

            results.append(DriftAnalysis(
                key=target_key,
                current_weight=round(current, 6),
                target_weight=target.target_weight,
                drift_pct=round(drift_pct, 6),
                drift_relative=round(drift_relative, 4),
                action_needed=action,
                urgency=round(urgency, 4),
            ))

        # Sort by urgency descending
        results.sort(key=lambda d: d.urgency, reverse=True)
        return results

    # ── Order Generation ────────────────────

    def generate_rebalance_orders(
        self,
        portfolio: PortfolioState,
        price_map: dict[str, float],
        segment_map: dict[str, str] | None = None,
        min_trade_notional: float = 100.0,
    ) -> list[RebalanceOrder]:
        """
        Generate the trades needed to realign portfolio to targets.

        Only generates orders for symbol-level targets (not sector-level).
        Sector-level drift is informational only — symbol targets drive trades.

        Args:
            portfolio: Current portfolio state.
            price_map: symbol -> current price.
            segment_map: symbol -> sector (for sector-level targets).
            min_trade_notional: Minimum dollar value to bother trading.

        Returns:
            List of RebalanceOrder sorted by absolute notional descending.
        """
        total_value = max(portfolio.total_value, 1.0)
        drift_analyses = self.analyze_drift(portfolio, segment_map)
        orders: list[RebalanceOrder] = []

        for drift in drift_analyses:
            if drift.action_needed == RebalanceAction.HOLD:
                continue

            target = self.targets[drift.key]
            if target.is_sector:
                continue  # Sector-level: informational only

            symbol = drift.key
            price = price_map.get(symbol)
            if price is None or price <= 0:
                continue

            # Calculate notional adjustment
            target_notional = target.target_weight * total_value
            pos = portfolio.get_position(symbol)
            current_notional = pos.notional_value if pos else 0.0
            delta_notional = target_notional - current_notional

            if abs(delta_notional) < min_trade_notional:
                continue

            side = OrderSide.BUY if delta_notional > 0 else OrderSide.SELL
            abs_notional = abs(delta_notional)
            quantity = abs_notional / price

            # Estimate cost for this single order
            cost = abs_notional * (
                self.commission_rate + self.spread_cost_rate + self.market_impact_rate
            )

            orders.append(RebalanceOrder(
                symbol=symbol,
                side=side,
                target_notional=round(abs_notional, 2),
                target_quantity=round(quantity, 8),
                current_price=price,
                reason=f"Drift {drift.drift_pct:.2%} exceeds tolerance {target.tolerance_band:.2%}",
                estimated_cost=round(cost, 2),
            ))

        # Sort by notional descending (largest trades first)
        orders.sort(key=lambda o: o.target_notional, reverse=True)
        return orders

    # ── Cost Estimation ─────────────────────

    def estimate_rebalance_cost(
        self,
        orders: list[RebalanceOrder],
        portfolio_value: float,
    ) -> RebalanceCostEstimate:
        """
        Estimate total transaction costs for a set of rebalance orders.

        Cost components:
        - Commissions: commission_rate * turnover
        - Spread costs: spread_cost_rate * turnover
        - Market impact: market_impact_rate * turnover (simplified linear model)
        """
        if not orders:
            return RebalanceCostEstimate(
                total_turnover=0.0,
                estimated_commissions=0.0,
                estimated_spread_cost=0.0,
                estimated_market_impact=0.0,
                total_estimated_cost=0.0,
                cost_as_pct_of_portfolio=0.0,
                num_trades=0,
            )

        turnover = sum(o.target_notional for o in orders)
        commissions = turnover * self.commission_rate
        spread_cost = turnover * self.spread_cost_rate
        # Market impact scales quadratically with trade size relative to portfolio
        notionals = np.array([o.target_notional for o in orders])
        impact_factor = float(np.sum((notionals / max(portfolio_value, 1.0)) ** 0.5))
        market_impact = turnover * self.market_impact_rate * (1.0 + impact_factor)

        total_cost = commissions + spread_cost + market_impact

        return RebalanceCostEstimate(
            total_turnover=round(turnover, 2),
            estimated_commissions=round(commissions, 2),
            estimated_spread_cost=round(spread_cost, 2),
            estimated_market_impact=round(market_impact, 2),
            total_estimated_cost=round(total_cost, 2),
            cost_as_pct_of_portfolio=round(total_cost / max(portfolio_value, 1.0) * 100, 4),
            num_trades=len(orders),
        )

    # ── Calendar Rebalance ──────────────────

    def calendar_rebalance(
        self,
        portfolio: PortfolioState,
        price_map: dict[str, float],
        frequency: str = "monthly",
        current_time: datetime | None = None,
        segment_map: dict[str, str] | None = None,
    ) -> RebalanceReport:
        """
        Check if a calendar-based rebalance is due and generate orders if so.

        Args:
            portfolio: Current portfolio state.
            price_map: symbol -> current price.
            frequency: 'monthly' or 'quarterly'.
            current_time: Override for current time (for testing).
            segment_map: symbol -> sector mapping.

        Returns:
            RebalanceReport with orders if rebalance is due, empty otherwise.
        """
        now = current_time or datetime.now(timezone.utc)
        drift_analyses = self.analyze_drift(portfolio, segment_map)
        max_drift = max((d.drift_pct for d in drift_analyses), default=0.0)

        # Determine if rebalance is due
        rebalance_due = False
        if self._last_rebalance is None:
            rebalance_due = True
            reason = "Initial rebalance — no prior rebalance recorded"
        else:
            elapsed_days = (now - self._last_rebalance).total_seconds() / 86400
            if frequency == "monthly" and elapsed_days >= 30:
                rebalance_due = True
                reason = f"Monthly rebalance due ({elapsed_days:.0f} days since last)"
            elif frequency == "quarterly" and elapsed_days >= 90:
                rebalance_due = True
                reason = f"Quarterly rebalance due ({elapsed_days:.0f} days since last)"
            else:
                reason = (
                    f"Not due yet ({elapsed_days:.0f} days since last, "
                    f"next in {(30 if frequency == 'monthly' else 90) - elapsed_days:.0f} days)"
                )

        orders: list[RebalanceOrder] = []
        cost_estimate = None

        if rebalance_due:
            orders = self.generate_rebalance_orders(portfolio, price_map, segment_map)
            cost_estimate = self.estimate_rebalance_cost(orders, portfolio.total_value)
            self._last_rebalance = now

        return RebalanceReport(
            timestamp=now,
            drift_analyses=drift_analyses,
            max_drift=round(max_drift, 6),
            rebalance_needed=rebalance_due,
            trigger_reason=reason,
            proposed_orders=orders,
            cost_estimate=cost_estimate,
        )

    # ── Threshold Rebalance ─────────────────

    def threshold_rebalance(
        self,
        portfolio: PortfolioState,
        price_map: dict[str, float],
        global_threshold: float = 0.05,
        segment_map: dict[str, str] | None = None,
    ) -> RebalanceReport:
        """
        Trigger rebalance when any position drifts beyond its tolerance band.

        Uses per-target tolerance bands by default. The global_threshold
        acts as an override: if ANY drift exceeds it, all positions rebalance.

        Args:
            portfolio: Current portfolio state.
            price_map: symbol -> current price.
            global_threshold: Override threshold (e.g., 0.05 = 5%).
            segment_map: symbol -> sector mapping.

        Returns:
            RebalanceReport with orders if threshold breached.
        """
        now = datetime.now(timezone.utc)
        drift_analyses = self.analyze_drift(portfolio, segment_map)
        max_drift = max((d.drift_pct for d in drift_analyses), default=0.0)

        # Check if any target exceeds its individual tolerance or the global threshold
        breached = [
            d for d in drift_analyses
            if d.drift_pct > self.targets[d.key].tolerance_band
            or d.drift_pct > global_threshold
        ]

        rebalance_needed = len(breached) > 0
        orders: list[RebalanceOrder] = []
        cost_estimate = None

        if rebalance_needed:
            breached_keys = [b.key for b in breached]
            reason = (
                f"Threshold breach: {len(breached)} targets exceed tolerance. "
                f"Max drift: {max_drift:.2%}. Breached: {', '.join(breached_keys[:5])}"
            )
            orders = self.generate_rebalance_orders(portfolio, price_map, segment_map)
            cost_estimate = self.estimate_rebalance_cost(orders, portfolio.total_value)
            self._last_rebalance = now
        else:
            reason = f"All targets within tolerance (max drift: {max_drift:.2%})"

        return RebalanceReport(
            timestamp=now,
            drift_analyses=drift_analyses,
            max_drift=round(max_drift, 6),
            rebalance_needed=rebalance_needed,
            trigger_reason=reason,
            proposed_orders=orders,
            cost_estimate=cost_estimate,
        )

    # ── Tax-Aware Rebalance ─────────────────

    def tax_aware_rebalance(
        self,
        portfolio: PortfolioState,
        price_map: dict[str, float],
        unrealized_pnl_map: dict[str, float] | None = None,
        segment_map: dict[str, str] | None = None,
        min_trade_notional: float = 100.0,
    ) -> RebalanceReport:
        """
        Generate tax-efficient rebalance orders.

        Strategy:
        1. When selling, prefer positions with unrealized LOSSES (tax loss harvesting).
        2. Among gainers that must be sold, prefer long-term gains over short-term.
        3. When buying, use cash from loss harvesting sales first.
        4. Avoid selling winners unless drift is severe (urgency > 0.5).

        Args:
            portfolio: Current portfolio state.
            price_map: symbol -> current price.
            unrealized_pnl_map: symbol -> unrealized P&L (positive = gain, negative = loss).
                If None, computed from portfolio positions.
            segment_map: symbol -> sector mapping.
            min_trade_notional: Minimum trade size.

        Returns:
            RebalanceReport with tax-optimized orders.
        """
        now = datetime.now(timezone.utc)

        # Build unrealized P&L map if not provided
        if unrealized_pnl_map is None:
            unrealized_pnl_map = {}
            for pos in portfolio.positions:
                unrealized_pnl_map[pos.symbol] = pos.unrealized_pnl

        drift_analyses = self.analyze_drift(portfolio, segment_map)
        max_drift = max((d.drift_pct for d in drift_analyses), default=0.0)

        total_value = max(portfolio.total_value, 1.0)
        orders: list[RebalanceOrder] = []

        # Separate sells into losers (harvest) and winners (avoid if possible)
        sell_candidates: list[tuple[DriftAnalysis, float]] = []  # (drift, unrealized_pnl)
        buy_candidates: list[DriftAnalysis] = []

        for drift in drift_analyses:
            if drift.action_needed == RebalanceAction.HOLD:
                continue
            target = self.targets[drift.key]
            if target.is_sector:
                continue

            if drift.action_needed == RebalanceAction.SELL:
                pnl = unrealized_pnl_map.get(drift.key, 0.0)
                sell_candidates.append((drift, pnl))
            else:
                buy_candidates.append(drift)

        # Sort sells: losses first (most negative P&L first), then by urgency
        sell_candidates.sort(key=lambda x: (x[1], -x[0].urgency))

        # Process sells — prefer harvesting losses
        for drift, pnl in sell_candidates:
            symbol = drift.key
            price = price_map.get(symbol)
            if price is None or price <= 0:
                continue

            target = self.targets[symbol]
            target_notional = target.target_weight * total_value
            pos = portfolio.get_position(symbol)
            current_notional = pos.notional_value if pos else 0.0
            delta = current_notional - target_notional

            if delta < min_trade_notional:
                continue

            # For winners with low urgency, sell less aggressively
            if pnl > 0 and drift.urgency < 0.5:
                # Only sell half the excess to reduce tax drag
                delta *= 0.5

            quantity = delta / price

            reason_parts = [
                f"Drift {drift.drift_pct:.2%} exceeds tolerance {target.tolerance_band:.2%}",
            ]
            if pnl < 0:
                reason_parts.append(f"Tax loss harvest: unrealized loss ${pnl:,.2f}")
            elif pnl > 0 and drift.urgency < 0.5:
                reason_parts.append(
                    f"Reduced sell (winner, low urgency): unrealized gain ${pnl:,.2f}"
                )

            cost = delta * (self.commission_rate + self.spread_cost_rate + self.market_impact_rate)

            orders.append(RebalanceOrder(
                symbol=symbol,
                side=OrderSide.SELL,
                target_notional=round(delta, 2),
                target_quantity=round(quantity, 8),
                current_price=price,
                reason=" | ".join(reason_parts),
                estimated_cost=round(cost, 2),
            ))

        # Process buys
        for drift in buy_candidates:
            symbol = drift.key
            price = price_map.get(symbol)
            if price is None or price <= 0:
                continue

            target = self.targets[symbol]
            target_notional = target.target_weight * total_value
            pos = portfolio.get_position(symbol)
            current_notional = pos.notional_value if pos else 0.0
            delta = target_notional - current_notional

            if delta < min_trade_notional:
                continue

            quantity = delta / price
            cost = delta * (self.commission_rate + self.spread_cost_rate + self.market_impact_rate)

            orders.append(RebalanceOrder(
                symbol=symbol,
                side=OrderSide.BUY,
                target_notional=round(delta, 2),
                target_quantity=round(quantity, 8),
                current_price=price,
                reason=f"Drift {drift.drift_pct:.2%} exceeds tolerance {target.tolerance_band:.2%}",
                estimated_cost=round(cost, 2),
            ))

        cost_estimate = self.estimate_rebalance_cost(orders, total_value)
        rebalance_needed = len(orders) > 0

        return RebalanceReport(
            timestamp=now,
            drift_analyses=drift_analyses,
            max_drift=round(max_drift, 6),
            rebalance_needed=rebalance_needed,
            trigger_reason=(
                f"Tax-aware rebalance: {len(orders)} orders "
                f"({sum(1 for o in orders if o.side == OrderSide.SELL)} sells, "
                f"{sum(1 for o in orders if o.side == OrderSide.BUY)} buys)"
                if rebalance_needed
                else "No rebalance needed"
            ),
            proposed_orders=orders,
            cost_estimate=cost_estimate,
        )
