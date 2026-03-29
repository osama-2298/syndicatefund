"""
Smart Order Router.

Routes orders to optimal venues based on fees, latency, liquidity, and available
pairs.  Supports order splitting across multiple venues, VWAP/TWAP scheduling
for large orders, and square-root market impact estimation.

This is the layer between OrderManager (which tracks lifecycle) and the actual
exchange connectors.  In paper-trading mode the router still runs -- it produces
a routing plan that the PaperTrader executes locally.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from pydantic import BaseModel, Field

from syndicate.data.models import OrderSide

logger = structlog.get_logger()


# ═══════════════════════════════════════════
#  Exchange / Venue Model
# ═══════════════════════════════════════════


class Exchange(BaseModel):
    """
    Venue descriptor.

    Holds static configuration for a single exchange or liquidity source.
    The SmartRouter uses these attributes to score and rank venues.
    """

    name: str                                # e.g. "binance", "coinbase", "kraken"
    maker_fee_bps: float = 4.0               # Maker fee in basis points
    taker_fee_bps: float = 10.0              # Taker fee in basis points
    latency_ms: float = 50.0                 # Estimated round-trip latency
    available_pairs: set[str] = Field(default_factory=set)  # e.g. {"BTCUSDT", "ETHUSDT"}
    daily_volume_usd: float = 0.0            # Estimated 24h volume across all pairs
    max_order_size_usd: float = 1_000_000.0  # Per-order notional limit
    is_active: bool = True                   # Disabled venues are skipped
    priority: int = 0                        # Manual priority boost (higher = prefer)

    def supports(self, symbol: str) -> bool:
        """Check whether this venue lists the given pair."""
        return symbol in self.available_pairs

    def effective_fee_bps(self, is_taker: bool = True) -> float:
        """Return the relevant fee tier."""
        return self.taker_fee_bps if is_taker else self.maker_fee_bps


# ═══════════════════════════════════════════
#  Routing Plan Models
# ═══════════════════════════════════════════


class RouteLeg(BaseModel):
    """A single leg of a routed order -- one venue, one quantity."""

    leg_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    venue: str
    symbol: str
    side: OrderSide
    quantity: float
    estimated_fee_bps: float = 0.0
    estimated_latency_ms: float = 0.0
    reason: str = ""  # Why this leg was chosen


class RoutingPlan(BaseModel):
    """Complete routing plan for an order, possibly spanning multiple venues."""

    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    side: OrderSide
    total_quantity: float
    legs: list[RouteLeg] = Field(default_factory=list)
    estimated_total_fee_bps: float = 0.0
    estimated_market_impact_bps: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def num_venues(self) -> int:
        return len({leg.venue for leg in self.legs})


class ScheduleSlice(BaseModel):
    """A single time-slice in a VWAP or TWAP execution schedule."""

    slice_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    start_time: datetime
    end_time: datetime
    target_quantity: float
    target_pct: float          # Fraction of total order for this slice
    venue: str = ""            # Preferred venue (can be overridden at execution)
    executed_quantity: float = 0.0
    executed: bool = False


class ExecutionSchedule(BaseModel):
    """Time-sliced execution plan (VWAP or TWAP)."""

    schedule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    algorithm: str             # "VWAP" or "TWAP"
    symbol: str
    side: OrderSide
    total_quantity: float
    slices: list[ScheduleSlice] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    estimated_impact_bps: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def remaining_quantity(self) -> float:
        return self.total_quantity - sum(s.executed_quantity for s in self.slices)

    @property
    def completion_pct(self) -> float:
        if self.total_quantity == 0:
            return 0.0
        executed = sum(s.executed_quantity for s in self.slices)
        return executed / self.total_quantity


# ═══════════════════════════════════════════
#  SmartRouter
# ═══════════════════════════════════════════


# Default volume profile for crypto markets (hourly buckets, 24 entries).
# Approximates typical BTC/USDT volume distribution across UTC hours.
# Source: empirical observation of Binance order-book depth.
_DEFAULT_HOURLY_VOLUME_PROFILE: list[float] = [
    0.032, 0.028, 0.025, 0.023, 0.022, 0.022,  # 00-05 UTC (Asia wind-down)
    0.025, 0.030, 0.038, 0.045, 0.050, 0.052,  # 06-11 UTC (Europe open)
    0.055, 0.058, 0.060, 0.062, 0.058, 0.052,  # 12-17 UTC (US open overlap)
    0.048, 0.045, 0.042, 0.040, 0.038, 0.035,  # 18-23 UTC (US session)
]


class SmartRouter:
    """
    Smart Order Router for institutional execution.

    Given a set of registered exchanges, the router finds the best venue(s)
    for each order based on:
    1. Availability -- does the venue list this pair?
    2. Fee efficiency -- lowest taker/maker fee.
    3. Latency -- fastest round-trip.
    4. Capacity -- can the venue handle the order size?
    5. Priority -- manual boosts for preferred venues.

    For large orders it can split across venues and generate VWAP/TWAP
    execution schedules to minimize market impact.
    """

    def __init__(self) -> None:
        self._exchanges: dict[str, Exchange] = {}
        self._volume_profile = _DEFAULT_HOURLY_VOLUME_PROFILE

    # ── Exchange management ──

    def register_exchange(self, exchange: Exchange) -> None:
        """Add or update an exchange in the routing table."""
        self._exchanges[exchange.name] = exchange
        logger.info(
            "exchange_registered",
            name=exchange.name,
            pairs=len(exchange.available_pairs),
            taker_fee_bps=exchange.taker_fee_bps,
        )

    def remove_exchange(self, name: str) -> None:
        """Remove an exchange from routing."""
        self._exchanges.pop(name, None)

    def set_volume_profile(self, profile: list[float]) -> None:
        """
        Override the default 24-hour volume profile.
        Must have exactly 24 entries (one per hour) that sum to ~1.0.
        """
        if len(profile) != 24:
            raise ValueError("Volume profile must have exactly 24 hourly entries")
        total = sum(profile)
        # Normalize to sum to 1.0
        self._volume_profile = [v / total for v in profile]

    # ── Core routing ──

    def route_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        prefer_maker: bool = False,
        max_venues: int = 3,
    ) -> RoutingPlan:
        """
        Find the best venue(s) for an order.

        Scoring formula per venue:
            score = -fee_bps * 2.0 - latency_ms * 0.01 + priority * 5.0

        Higher score = better venue.  The order is routed to the single best
        venue unless ``quantity`` exceeds that venue's max_order_size_usd (in
        which case it spills over to the next-best venues).
        """
        candidates = self._rank_venues(symbol, prefer_maker)

        if not candidates:
            logger.warning("no_venues_available", symbol=symbol)
            return RoutingPlan(
                symbol=symbol,
                side=side,
                total_quantity=quantity,
            )

        # Build legs -- spill to next venue if capacity exceeded
        legs: list[RouteLeg] = []
        remaining = quantity

        for exchange, score in candidates[:max_venues]:
            if remaining <= 0:
                break

            # For simplicity, treat max_order_size as a quantity cap.
            # In production this would use price to convert notional limits.
            alloc = min(remaining, exchange.max_order_size_usd)

            legs.append(RouteLeg(
                venue=exchange.name,
                symbol=symbol,
                side=side,
                quantity=alloc,
                estimated_fee_bps=exchange.effective_fee_bps(is_taker=not prefer_maker),
                estimated_latency_ms=exchange.latency_ms,
                reason=f"score={score:.2f}",
            ))
            remaining -= alloc

        if remaining > 0:
            # Could not fully route -- attach remainder to best venue anyway
            # with a warning.  In production this would trigger a reject.
            legs[0].quantity += remaining
            logger.warning(
                "order_partially_unroutable",
                symbol=symbol,
                unrouted_qty=remaining,
            )

        # Weighted average fee
        total_qty = sum(l.quantity for l in legs)
        avg_fee = (
            sum(l.estimated_fee_bps * l.quantity for l in legs) / total_qty
            if total_qty > 0 else 0.0
        )

        plan = RoutingPlan(
            symbol=symbol,
            side=side,
            total_quantity=quantity,
            legs=legs,
            estimated_total_fee_bps=round(avg_fee, 2),
            estimated_market_impact_bps=round(
                self.estimate_impact(symbol, quantity), 2
            ),
        )

        logger.info(
            "order_routed",
            symbol=symbol,
            side=side.value,
            quantity=quantity,
            venues=plan.num_venues,
            fee_bps=plan.estimated_total_fee_bps,
            impact_bps=plan.estimated_market_impact_bps,
        )
        return plan

    def split_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        num_splits: int = 3,
        prefer_maker: bool = False,
    ) -> list[RouteLeg]:
        """
        Break a large order into equal-sized child orders across venues.

        Useful when a single large order would move the book.  Each split is
        assigned to the next-best venue in round-robin fashion.
        """
        candidates = self._rank_venues(symbol, prefer_maker)
        if not candidates:
            logger.warning("split_no_venues", symbol=symbol)
            return []

        split_qty = quantity / num_splits
        legs: list[RouteLeg] = []

        for i in range(num_splits):
            exchange, score = candidates[i % len(candidates)]
            legs.append(RouteLeg(
                venue=exchange.name,
                symbol=symbol,
                side=side,
                quantity=split_qty,
                estimated_fee_bps=exchange.effective_fee_bps(
                    is_taker=not prefer_maker
                ),
                estimated_latency_ms=exchange.latency_ms,
                reason=f"split {i + 1}/{num_splits}, score={score:.2f}",
            ))

        logger.info(
            "order_split",
            symbol=symbol,
            total_qty=quantity,
            splits=num_splits,
            venues=[l.venue for l in legs],
        )
        return legs

    # ── Algorithmic scheduling ──

    def vwap_schedule(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        duration_hours: int = 4,
        start_time: datetime | None = None,
        slices_per_hour: int = 4,
    ) -> ExecutionSchedule:
        """
        Generate a Volume-Weighted Average Price execution schedule.

        Distributes quantity across time slices proportional to the expected
        volume profile.  More quantity is placed during high-volume hours to
        minimize impact.
        """
        start = start_time or datetime.now(timezone.utc)
        end = start + timedelta(hours=duration_hours)
        total_slices = duration_hours * slices_per_hour
        slice_minutes = 60 // slices_per_hour

        # Gather volume weights for each slice
        raw_weights: list[float] = []
        for i in range(total_slices):
            slice_start = start + timedelta(minutes=i * slice_minutes)
            hour = slice_start.hour
            # Sub-hour slices share the hourly weight equally
            raw_weights.append(self._volume_profile[hour] / slices_per_hour)

        # Normalize
        weight_sum = sum(raw_weights)
        if weight_sum == 0:
            weights = [1.0 / total_slices] * total_slices
        else:
            weights = [w / weight_sum for w in raw_weights]

        # Build slices
        best_venue = self._best_venue_name(symbol)
        slices: list[ScheduleSlice] = []
        allocated = 0.0

        for i in range(total_slices):
            slice_start = start + timedelta(minutes=i * slice_minutes)
            slice_end = slice_start + timedelta(minutes=slice_minutes)

            if i == total_slices - 1:
                # Last slice gets the remainder to avoid floating-point drift
                target_qty = quantity - allocated
            else:
                target_qty = round(quantity * weights[i], 8)

            allocated += target_qty

            slices.append(ScheduleSlice(
                start_time=slice_start,
                end_time=slice_end,
                target_quantity=target_qty,
                target_pct=round(weights[i], 6),
                venue=best_venue,
            ))

        schedule = ExecutionSchedule(
            algorithm="VWAP",
            symbol=symbol,
            side=side,
            total_quantity=quantity,
            slices=slices,
            start_time=start,
            end_time=end,
            estimated_impact_bps=round(
                self.estimate_impact(symbol, quantity), 2
            ),
        )

        logger.info(
            "vwap_schedule_created",
            symbol=symbol,
            quantity=quantity,
            duration_hours=duration_hours,
            total_slices=total_slices,
            impact_bps=schedule.estimated_impact_bps,
        )
        return schedule

    def twap_schedule(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        duration_hours: int = 4,
        start_time: datetime | None = None,
        slices_per_hour: int = 4,
    ) -> ExecutionSchedule:
        """
        Generate a Time-Weighted Average Price execution schedule.

        Distributes quantity equally across all time slices regardless of
        volume profile.  Simpler than VWAP but can cause more impact during
        low-volume periods.
        """
        start = start_time or datetime.now(timezone.utc)
        end = start + timedelta(hours=duration_hours)
        total_slices = duration_hours * slices_per_hour
        slice_minutes = 60 // slices_per_hour
        qty_per_slice = quantity / total_slices

        best_venue = self._best_venue_name(symbol)
        slices: list[ScheduleSlice] = []
        allocated = 0.0

        for i in range(total_slices):
            slice_start = start + timedelta(minutes=i * slice_minutes)
            slice_end = slice_start + timedelta(minutes=slice_minutes)

            if i == total_slices - 1:
                target_qty = quantity - allocated
            else:
                target_qty = round(qty_per_slice, 8)

            allocated += target_qty

            slices.append(ScheduleSlice(
                start_time=slice_start,
                end_time=slice_end,
                target_quantity=target_qty,
                target_pct=round(1.0 / total_slices, 6),
                venue=best_venue,
            ))

        schedule = ExecutionSchedule(
            algorithm="TWAP",
            symbol=symbol,
            side=side,
            total_quantity=quantity,
            slices=slices,
            start_time=start,
            end_time=end,
            estimated_impact_bps=round(
                self.estimate_impact(symbol, quantity), 2
            ),
        )

        logger.info(
            "twap_schedule_created",
            symbol=symbol,
            quantity=quantity,
            duration_hours=duration_hours,
            total_slices=total_slices,
            impact_bps=schedule.estimated_impact_bps,
        )
        return schedule

    # ── Market impact estimation ──

    def estimate_impact(
        self,
        symbol: str,
        quantity: float,
        daily_volume: float | None = None,
        volatility_bps: float = 200.0,
        participation_rate: float = 0.10,
    ) -> float:
        """
        Estimate market impact in basis points using the square-root model.

        The Almgren-Chriss square-root model approximates temporary impact as:

            impact = volatility * sqrt(quantity / daily_volume)

        Parameters
        ----------
        symbol : str
            Trading pair (used to look up venue volume if daily_volume is None).
        quantity : float
            Order size (in base currency units or notional -- must match
            daily_volume units).
        daily_volume : float, optional
            Aggregate daily volume.  If not provided, uses the sum of all
            registered venues' daily_volume_usd for this symbol.
        volatility_bps : float
            Annualized volatility in basis points.  Default 200 bps (2%) is
            conservative for large-cap crypto.
        participation_rate : float
            Expected fraction of daily volume this order represents.
            Used as a floor for the quantity/volume ratio.

        Returns
        -------
        float
            Estimated one-way market impact in basis points.
        """
        if daily_volume is None:
            daily_volume = sum(
                ex.daily_volume_usd
                for ex in self._exchanges.values()
                if ex.is_active and ex.supports(symbol)
            )

        if daily_volume <= 0:
            # No volume data -- return a conservative estimate
            return volatility_bps * 0.5

        ratio = max(quantity / daily_volume, participation_rate * 0.01)
        impact = volatility_bps * math.sqrt(ratio)
        return round(impact, 2)

    # ── Internal helpers ──

    def _rank_venues(
        self,
        symbol: str,
        prefer_maker: bool = False,
    ) -> list[tuple[Exchange, float]]:
        """
        Score and rank active venues that support the given symbol.
        Returns a list of (Exchange, score) sorted best-first.
        """
        scored: list[tuple[Exchange, float]] = []

        for exchange in self._exchanges.values():
            if not exchange.is_active or not exchange.supports(symbol):
                continue

            fee = exchange.effective_fee_bps(is_taker=not prefer_maker)
            # Score: lower fee is better, lower latency is better, higher priority is better
            score = -fee * 2.0 - exchange.latency_ms * 0.01 + exchange.priority * 5.0
            scored.append((exchange, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _best_venue_name(self, symbol: str) -> str:
        """Return the name of the top-ranked venue for a symbol, or empty string."""
        ranked = self._rank_venues(symbol)
        return ranked[0][0].name if ranked else ""
