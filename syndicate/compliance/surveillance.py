"""Trade surveillance engine for the Syndicate compliance layer.

Detects abusive or anomalous trading patterns:
  - Wash trading
  - Spoofing / layering
  - Concentration risk
  - Unusual-pattern deviations
  - Front-running
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum as PyEnum
from typing import Any, Sequence

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


# ── Enums ────────────────────────────────────────────────────────────────────


class AlertSeverity(str, PyEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertType(str, PyEnum):
    WASH_TRADE = "wash_trade"
    SPOOFING = "spoofing"
    CONCENTRATION = "concentration"
    UNUSUAL_PATTERN = "unusual_pattern"
    FRONT_RUNNING = "front_running"


# ── Data models ─────────────────────────────────────────────────────────────


class TradeRecord(BaseModel):
    """Lightweight trade representation consumed by surveillance detectors."""

    trade_id: str
    timestamp: datetime
    actor: str
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    price: float
    order_type: str = "market"  # market / limit
    cancelled: bool = False
    cancelled_at: datetime | None = None


class OrderRecord(BaseModel):
    """Order (including non-filled) for spoofing detection."""

    order_id: str
    timestamp: datetime
    actor: str
    symbol: str
    side: str
    quantity: float
    price: float
    filled: bool = False
    cancelled: bool = False
    cancelled_at: datetime | None = None
    lifetime_seconds: float | None = None


class SurveillanceAlert(BaseModel):
    """A flagged surveillance finding."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    alert_type: str = Field(..., description="AlertType value")
    severity: str = Field(..., description="AlertSeverity value")
    actor: str | None = Field(default=None, description="Responsible entity if known")
    symbol: str | None = Field(default=None)
    description: str = Field(..., description="Human-readable summary")
    evidence: dict[str, Any] = Field(
        default_factory=dict, description="Supporting data points"
    )
    recommended_action: str | None = Field(
        default=None,
        description="Suggested remediation (e.g. 'halt_actor', 'review_manually')",
    )

    class Config:
        frozen = True


# ── Detector implementations ────────────────────────────────────────────────


class WashTradeDetector:
    """Flag buy+sell of the same asset by the same actor within a short window."""

    def __init__(self, window_seconds: int = 300, min_overlap_pct: float = 0.80):
        self.window = timedelta(seconds=window_seconds)
        self.min_overlap_pct = min_overlap_pct

    def scan(self, trades: Sequence[TradeRecord]) -> list[SurveillanceAlert]:
        alerts: list[SurveillanceAlert] = []
        by_actor_symbol: dict[tuple[str, str], list[TradeRecord]] = {}
        for t in trades:
            by_actor_symbol.setdefault((t.actor, t.symbol), []).append(t)

        for (actor, symbol), group in by_actor_symbol.items():
            buys = sorted(
                [t for t in group if t.side == "buy"], key=lambda t: t.timestamp
            )
            sells = sorted(
                [t for t in group if t.side == "sell"], key=lambda t: t.timestamp
            )

            for buy in buys:
                for sell in sells:
                    if buy.trade_id == sell.trade_id:
                        continue
                    time_gap = abs((sell.timestamp - buy.timestamp).total_seconds())
                    if time_gap > self.window.total_seconds():
                        continue
                    overlap_qty = min(buy.quantity, sell.quantity)
                    overlap_pct = overlap_qty / max(buy.quantity, sell.quantity)
                    if overlap_pct >= self.min_overlap_pct:
                        alerts.append(
                            SurveillanceAlert(
                                alert_type=AlertType.WASH_TRADE,
                                severity=AlertSeverity.HIGH,
                                actor=actor,
                                symbol=symbol,
                                description=(
                                    f"Potential wash trade: {actor} bought and sold "
                                    f"{symbol} within {time_gap:.0f}s "
                                    f"(qty overlap {overlap_pct:.0%})"
                                ),
                                evidence={
                                    "buy_trade_id": buy.trade_id,
                                    "sell_trade_id": sell.trade_id,
                                    "buy_qty": buy.quantity,
                                    "sell_qty": sell.quantity,
                                    "time_gap_seconds": time_gap,
                                },
                                recommended_action="review_manually",
                            )
                        )
        return alerts


class SpoofingDetector:
    """Flag large orders cancelled within a short lifetime."""

    def __init__(
        self,
        max_lifetime_seconds: float = 5.0,
        size_percentile_threshold: float = 0.90,
    ):
        self.max_lifetime = max_lifetime_seconds
        self.size_pct_threshold = size_percentile_threshold

    def scan(self, orders: Sequence[OrderRecord]) -> list[SurveillanceAlert]:
        alerts: list[SurveillanceAlert] = []
        by_symbol: dict[str, list[OrderRecord]] = {}
        for o in orders:
            by_symbol.setdefault(o.symbol, []).append(o)

        for symbol, group in by_symbol.items():
            quantities = sorted([o.quantity for o in group])
            if not quantities:
                continue
            threshold_idx = int(len(quantities) * self.size_pct_threshold)
            size_threshold = quantities[min(threshold_idx, len(quantities) - 1)]

            for order in group:
                if not order.cancelled:
                    continue
                lifetime = order.lifetime_seconds
                if lifetime is None and order.cancelled_at is not None:
                    lifetime = (
                        order.cancelled_at - order.timestamp
                    ).total_seconds()
                if lifetime is None:
                    continue

                if lifetime <= self.max_lifetime and order.quantity >= size_threshold:
                    alerts.append(
                        SurveillanceAlert(
                            alert_type=AlertType.SPOOFING,
                            severity=AlertSeverity.CRITICAL,
                            actor=order.actor,
                            symbol=symbol,
                            description=(
                                f"Potential spoofing: {order.actor} placed large "
                                f"{order.side} order ({order.quantity} {symbol}) "
                                f"and cancelled within {lifetime:.1f}s"
                            ),
                            evidence={
                                "order_id": order.order_id,
                                "quantity": order.quantity,
                                "lifetime_seconds": lifetime,
                                "size_threshold": size_threshold,
                            },
                            recommended_action="halt_actor",
                        )
                    )
        return alerts


class ConcentrationMonitor:
    """Alert when a single-name exposure exceeds configurable thresholds."""

    def __init__(
        self,
        warn_pct: float = 0.20,
        critical_pct: float = 0.35,
    ):
        self.warn_pct = warn_pct
        self.critical_pct = critical_pct

    def check(
        self,
        positions: dict[str, float],
        total_portfolio_value: float,
    ) -> list[SurveillanceAlert]:
        """positions: mapping of symbol -> notional exposure."""
        alerts: list[SurveillanceAlert] = []
        if total_portfolio_value <= 0:
            return alerts

        for symbol, exposure in positions.items():
            pct = abs(exposure) / total_portfolio_value
            if pct >= self.critical_pct:
                severity = AlertSeverity.CRITICAL
            elif pct >= self.warn_pct:
                severity = AlertSeverity.MEDIUM
            else:
                continue

            alerts.append(
                SurveillanceAlert(
                    alert_type=AlertType.CONCENTRATION,
                    severity=severity,
                    symbol=symbol,
                    description=(
                        f"Concentration alert: {symbol} represents "
                        f"{pct:.1%} of portfolio (threshold: "
                        f"warn={self.warn_pct:.0%}, critical={self.critical_pct:.0%})"
                    ),
                    evidence={
                        "symbol": symbol,
                        "exposure": exposure,
                        "portfolio_value": total_portfolio_value,
                        "concentration_pct": round(pct, 4),
                    },
                    recommended_action=(
                        "reduce_position" if severity == AlertSeverity.CRITICAL else "review_manually"
                    ),
                )
            )
        return alerts


class UnusualPatternDetector:
    """Flag deviations from a strategy baseline (e.g. trade frequency, sizing)."""

    def __init__(
        self,
        frequency_std_threshold: float = 2.5,
        size_std_threshold: float = 2.5,
    ):
        self.freq_threshold = frequency_std_threshold
        self.size_threshold = size_std_threshold

    def scan(
        self,
        recent_trades: Sequence[TradeRecord],
        baseline_avg_frequency_per_hour: float,
        baseline_avg_size: float,
        baseline_size_std: float,
    ) -> list[SurveillanceAlert]:
        alerts: list[SurveillanceAlert] = []
        if not recent_trades:
            return alerts

        # --- Frequency check ---
        if len(recent_trades) >= 2:
            timestamps = sorted(t.timestamp for t in recent_trades)
            span_hours = max(
                (timestamps[-1] - timestamps[0]).total_seconds() / 3600.0, 0.01
            )
            actual_freq = len(recent_trades) / span_hours
            if baseline_avg_frequency_per_hour > 0:
                freq_ratio = actual_freq / baseline_avg_frequency_per_hour
                if freq_ratio > self.freq_threshold:
                    alerts.append(
                        SurveillanceAlert(
                            alert_type=AlertType.UNUSUAL_PATTERN,
                            severity=AlertSeverity.MEDIUM,
                            description=(
                                f"Trading frequency {actual_freq:.1f}/hr is "
                                f"{freq_ratio:.1f}x the baseline "
                                f"({baseline_avg_frequency_per_hour:.1f}/hr)"
                            ),
                            evidence={
                                "actual_frequency_per_hour": round(actual_freq, 2),
                                "baseline_frequency_per_hour": baseline_avg_frequency_per_hour,
                                "ratio": round(freq_ratio, 2),
                            },
                            recommended_action="review_manually",
                        )
                    )

        # --- Size check ---
        if baseline_size_std > 0:
            for trade in recent_trades:
                z_score = (trade.quantity - baseline_avg_size) / baseline_size_std
                if abs(z_score) > self.size_threshold:
                    alerts.append(
                        SurveillanceAlert(
                            alert_type=AlertType.UNUSUAL_PATTERN,
                            severity=AlertSeverity.HIGH if abs(z_score) > 4.0 else AlertSeverity.MEDIUM,
                            actor=trade.actor,
                            symbol=trade.symbol,
                            description=(
                                f"Unusual trade size: {trade.quantity} {trade.symbol} "
                                f"(z-score {z_score:+.1f}, baseline {baseline_avg_size:.2f}"
                                f" +/- {baseline_size_std:.2f})"
                            ),
                            evidence={
                                "trade_id": trade.trade_id,
                                "quantity": trade.quantity,
                                "z_score": round(z_score, 2),
                                "baseline_avg": baseline_avg_size,
                                "baseline_std": baseline_size_std,
                            },
                            recommended_action="review_manually",
                        )
                    )
        return alerts


class FrontRunningDetector:
    """Flag trades placed shortly before known events (announcements, signals)."""

    def __init__(self, lookahead_seconds: int = 300):
        self.lookahead = timedelta(seconds=lookahead_seconds)

    def scan(
        self,
        trades: Sequence[TradeRecord],
        known_events: Sequence[dict[str, Any]],
    ) -> list[SurveillanceAlert]:
        """known_events: list of dicts with at least 'timestamp', 'symbol', 'event_type'."""
        alerts: list[SurveillanceAlert] = []
        for event in known_events:
            event_time = event["timestamp"]
            if isinstance(event_time, str):
                event_time = datetime.fromisoformat(event_time)
            event_symbol = event.get("symbol")

            for trade in trades:
                if event_symbol and trade.symbol != event_symbol:
                    continue
                delta = (event_time - trade.timestamp).total_seconds()
                if 0 < delta <= self.lookahead.total_seconds():
                    alerts.append(
                        SurveillanceAlert(
                            alert_type=AlertType.FRONT_RUNNING,
                            severity=AlertSeverity.CRITICAL,
                            actor=trade.actor,
                            symbol=trade.symbol,
                            description=(
                                f"Potential front-running: {trade.actor} traded "
                                f"{trade.symbol} {delta:.0f}s before "
                                f"\"{event.get('event_type', 'event')}\""
                            ),
                            evidence={
                                "trade_id": trade.trade_id,
                                "trade_timestamp": trade.timestamp.isoformat(),
                                "event_timestamp": event_time.isoformat(),
                                "event_type": event.get("event_type"),
                                "seconds_before_event": round(delta, 1),
                            },
                            recommended_action="halt_actor",
                        )
                    )
        return alerts


# ── Convenience facade ──────────────────────────────────────────────────────


class SurveillanceEngine:
    """Aggregates all detectors and runs a full sweep."""

    def __init__(
        self,
        wash_window_seconds: int = 300,
        spoof_lifetime_seconds: float = 5.0,
        concentration_warn_pct: float = 0.20,
        concentration_critical_pct: float = 0.35,
        front_run_lookahead_seconds: int = 300,
    ):
        self.wash_detector = WashTradeDetector(window_seconds=wash_window_seconds)
        self.spoof_detector = SpoofingDetector(max_lifetime_seconds=spoof_lifetime_seconds)
        self.concentration_monitor = ConcentrationMonitor(
            warn_pct=concentration_warn_pct, critical_pct=concentration_critical_pct
        )
        self.unusual_detector = UnusualPatternDetector()
        self.front_run_detector = FrontRunningDetector(
            lookahead_seconds=front_run_lookahead_seconds
        )

    def run_full_sweep(
        self,
        *,
        trades: Sequence[TradeRecord] | None = None,
        orders: Sequence[OrderRecord] | None = None,
        positions: dict[str, float] | None = None,
        portfolio_value: float = 0.0,
        known_events: Sequence[dict[str, Any]] | None = None,
        baseline_freq_per_hour: float = 0.0,
        baseline_avg_size: float = 0.0,
        baseline_size_std: float = 0.0,
    ) -> list[SurveillanceAlert]:
        all_alerts: list[SurveillanceAlert] = []

        if trades:
            all_alerts.extend(self.wash_detector.scan(trades))

            if known_events:
                all_alerts.extend(
                    self.front_run_detector.scan(trades, known_events)
                )

            if baseline_freq_per_hour > 0 or baseline_size_std > 0:
                all_alerts.extend(
                    self.unusual_detector.scan(
                        trades,
                        baseline_freq_per_hour,
                        baseline_avg_size,
                        baseline_size_std,
                    )
                )

        if orders:
            all_alerts.extend(self.spoof_detector.scan(orders))

        if positions and portfolio_value > 0:
            all_alerts.extend(
                self.concentration_monitor.check(positions, portfolio_value)
            )

        if all_alerts:
            logger.warning(
                "surveillance_alerts",
                count=len(all_alerts),
                critical=sum(
                    1 for a in all_alerts if a.severity == AlertSeverity.CRITICAL
                ),
            )

        return all_alerts
