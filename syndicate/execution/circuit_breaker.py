"""
Circuit Breakers and Kill Switch.

Enforces hard risk limits that cannot be overridden by any trading logic.
If any threshold is breached the system halts all new orders until a human
reviews and explicitly resets the breaker.

Thresholds are checked pre-trade (before submission) and post-trade (after
each fill).  The circuit breaker is the last line of defense -- it sits
between the OrderManager and the exchange connectors.
"""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


# ═══════════════════════════════════════════
#  Enums
# ═══════════════════════════════════════════


class HaltReason(str, Enum):
    """Why trading was halted."""

    DRAWDOWN = "DRAWDOWN"              # Daily or hourly loss limit breached
    FLASH_CRASH = "FLASH_CRASH"        # Sudden extreme price move detected
    RATE_LIMIT = "RATE_LIMIT"          # Too many orders in a short window
    CONSECUTIVE_LOSSES = "CONSECUTIVE_LOSSES"  # Too many losing trades in a row
    MANUAL = "MANUAL"                  # Operator pressed the kill switch
    SYSTEM_ERROR = "SYSTEM_ERROR"      # Unrecoverable system fault


class BreakerState(str, Enum):
    """Current state of the circuit breaker."""

    ACTIVE = "ACTIVE"       # Trading is allowed
    TRIPPED = "TRIPPED"     # Trading is halted, awaiting review
    COOLDOWN = "COOLDOWN"   # Temporarily paused, will auto-resume


# ═══════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════


class CircuitBreakerConfig(BaseModel):
    """
    Configurable thresholds for the circuit breaker.

    All monetary values are in the portfolio's base currency (USD).
    All percentage values are expressed as fractions (0.03 = 3%).
    """

    # Loss limits
    max_daily_loss_pct: float = 0.03        # 3% of portfolio value
    max_hourly_loss_pct: float = 0.015      # 1.5% of portfolio value
    max_daily_loss_usd: float = 5_000.0     # Hard dollar cap
    max_hourly_loss_usd: float = 2_500.0    # Hard dollar cap

    # Consecutive losses
    max_consecutive_losses: int = 5         # Halt after N losing trades in a row

    # Order rate limiting
    max_orders_per_minute: int = 30         # Prevent runaway loops
    max_orders_per_hour: int = 200          # Sustained rate limit

    # Flash crash detection
    flash_crash_threshold_pct: float = 0.10  # 10% move in a single asset
    flash_crash_window_seconds: int = 300    # Within a 5-minute window

    # Cooldown
    cooldown_seconds: int = 300             # 5-minute pause on soft trips
    auto_reset_after_cooldown: bool = False  # If True, resume automatically

    # Portfolio reference (used to convert % thresholds to USD)
    portfolio_value_usd: float = 100_000.0


# ═══════════════════════════════════════════
#  Trade Record (lightweight, for breaker tracking)
# ═══════════════════════════════════════════


class _TradeRecord(BaseModel):
    """Minimal record of a trade for circuit-breaker accounting."""

    symbol: str
    side: str
    pnl: float
    timestamp: datetime
    price: float = 0.0


# ═══════════════════════════════════════════
#  CircuitBreaker
# ═══════════════════════════════════════════


class CircuitBreaker:
    """
    Pre-trade and post-trade circuit breaker.

    Thread-safe -- all state mutations are protected by a lock so the breaker
    can be shared across async workers and the heartbeat thread.

    Usage:
        breaker = CircuitBreaker(config)

        # Before every order:
        allowed, reason = breaker.check_pre_trade(symbol, side, notional)
        if not allowed:
            reject_order(reason)

        # After every fill:
        breaker.record_trade(symbol, side, pnl)

        # Emergency:
        breaker.trigger_halt(HaltReason.MANUAL, "Operator kill switch")
    """

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        self._config = config or CircuitBreakerConfig()
        self._lock = threading.Lock()

        # State
        self._state = BreakerState.ACTIVE
        self._halt_reason: HaltReason | None = None
        self._halt_message: str = ""
        self._halt_time: datetime | None = None

        # Trade tracking
        self._trades: deque[_TradeRecord] = deque(maxlen=10_000)
        self._consecutive_losses: int = 0
        self._daily_pnl: float = 0.0
        self._daily_reset_date: str = ""  # YYYY-MM-DD, reset each day

        # Order rate tracking (timestamps of recent orders)
        self._order_timestamps: deque[datetime] = deque(maxlen=10_000)

        # Price tracking for flash-crash detection
        # symbol -> deque of (timestamp, price)
        self._price_history: dict[str, deque[tuple[datetime, float]]] = {}

        # Cooldown
        self._cooldown_until: datetime | None = None

        # Audit log
        self._event_log: deque[dict[str, Any]] = deque(maxlen=5_000)

    # ── Pre-trade check ──

    def check_pre_trade(
        self,
        symbol: str = "",
        side: str = "",
        notional_usd: float = 0.0,
        current_price: float = 0.0,
    ) -> tuple[bool, str]:
        """
        Should we allow this trade?

        Returns (allowed: bool, reason: str).  If allowed is False, reason
        explains which threshold was breached.  The order should be rejected.
        """
        with self._lock:
            # Check cooldown expiry
            self._check_cooldown_expiry()

            # Hard halt -- nothing goes through
            if self._state == BreakerState.TRIPPED:
                return False, f"Trading halted: {self._halt_reason.value if self._halt_reason else 'UNKNOWN'} -- {self._halt_message}"

            if self._state == BreakerState.COOLDOWN:
                remaining = ""
                if self._cooldown_until:
                    secs = (self._cooldown_until - datetime.now(timezone.utc)).total_seconds()
                    remaining = f" ({max(0, int(secs))}s remaining)"
                return False, f"Trading paused (cooldown){remaining}"

            now = datetime.now(timezone.utc)

            # Reset daily counters if new day
            self._maybe_reset_daily(now)

            # 1. Daily loss check
            if self._daily_pnl < 0:
                if abs(self._daily_pnl) >= self._config.max_daily_loss_usd:
                    self._trip(HaltReason.DRAWDOWN, f"Daily loss ${abs(self._daily_pnl):,.2f} exceeds ${self._config.max_daily_loss_usd:,.2f} limit")
                    return False, self._halt_message

                loss_pct = abs(self._daily_pnl) / max(self._config.portfolio_value_usd, 1.0)
                if loss_pct >= self._config.max_daily_loss_pct:
                    self._trip(HaltReason.DRAWDOWN, f"Daily loss {loss_pct:.2%} exceeds {self._config.max_daily_loss_pct:.2%} limit")
                    return False, self._halt_message

            # 2. Hourly loss check
            hourly_pnl = self._calc_hourly_pnl(now)
            if hourly_pnl < 0:
                if abs(hourly_pnl) >= self._config.max_hourly_loss_usd:
                    self._trip(HaltReason.DRAWDOWN, f"Hourly loss ${abs(hourly_pnl):,.2f} exceeds ${self._config.max_hourly_loss_usd:,.2f} limit")
                    return False, self._halt_message

                loss_pct = abs(hourly_pnl) / max(self._config.portfolio_value_usd, 1.0)
                if loss_pct >= self._config.max_hourly_loss_pct:
                    self._trip(HaltReason.DRAWDOWN, f"Hourly loss {loss_pct:.2%} exceeds {self._config.max_hourly_loss_pct:.2%} limit")
                    return False, self._halt_message

            # 3. Consecutive losses
            if self._consecutive_losses >= self._config.max_consecutive_losses:
                self._trip(
                    HaltReason.CONSECUTIVE_LOSSES,
                    f"{self._consecutive_losses} consecutive losses (limit: {self._config.max_consecutive_losses})",
                )
                return False, self._halt_message

            # 4. Order rate limit
            minute_ago = now - timedelta(minutes=1)
            hour_ago = now - timedelta(hours=1)
            orders_last_minute = sum(
                1 for t in self._order_timestamps if t >= minute_ago
            )
            orders_last_hour = sum(
                1 for t in self._order_timestamps if t >= hour_ago
            )

            if orders_last_minute >= self._config.max_orders_per_minute:
                self._enter_cooldown(
                    f"Rate limit: {orders_last_minute} orders/min "
                    f"(limit: {self._config.max_orders_per_minute})"
                )
                return False, f"Rate limit exceeded: {orders_last_minute} orders in last minute"

            if orders_last_hour >= self._config.max_orders_per_hour:
                self._enter_cooldown(
                    f"Rate limit: {orders_last_hour} orders/hour "
                    f"(limit: {self._config.max_orders_per_hour})"
                )
                return False, f"Rate limit exceeded: {orders_last_hour} orders in last hour"

            # 5. Flash crash detection
            if symbol and current_price > 0:
                flash = self._check_flash_crash(symbol, current_price, now)
                if flash:
                    self._trip(HaltReason.FLASH_CRASH, flash)
                    return False, self._halt_message

            # Record order timestamp
            self._order_timestamps.append(now)

            return True, ""

    # ── Post-trade recording ──

    def record_trade(
        self,
        symbol: str,
        side: str,
        pnl: float,
        price: float = 0.0,
    ) -> None:
        """
        Update circuit-breaker state after a trade execution.

        Call this for every fill -- the breaker tracks cumulative P&L and
        consecutive losses.
        """
        with self._lock:
            now = datetime.now(timezone.utc)
            self._maybe_reset_daily(now)

            record = _TradeRecord(
                symbol=symbol,
                side=side,
                pnl=pnl,
                timestamp=now,
                price=price,
            )
            self._trades.append(record)
            self._daily_pnl += pnl

            # Consecutive loss tracking
            if pnl < 0:
                self._consecutive_losses += 1
            elif pnl > 0:
                self._consecutive_losses = 0
            # pnl == 0 (flat) does not reset the counter

            # Update price history for flash crash detection
            if symbol and price > 0:
                if symbol not in self._price_history:
                    self._price_history[symbol] = deque(maxlen=1_000)
                self._price_history[symbol].append((now, price))

            self._log_event("TRADE_RECORDED", {
                "symbol": symbol,
                "pnl": round(pnl, 2),
                "daily_pnl": round(self._daily_pnl, 2),
                "consecutive_losses": self._consecutive_losses,
            })

    # ── Emergency controls ──

    def trigger_halt(
        self,
        reason: HaltReason = HaltReason.MANUAL,
        message: str = "Manual halt triggered",
    ) -> None:
        """
        Emergency stop -- immediately halt all trading.

        This is the kill switch.  Once triggered, trading cannot resume until
        reset() is called explicitly by an operator.
        """
        with self._lock:
            self._state = BreakerState.TRIPPED
            self._halt_reason = reason
            self._halt_message = message
            self._halt_time = datetime.now(timezone.utc)

            self._log_event("HALT_TRIGGERED", {
                "reason": reason.value,
                "message": message,
            })

            logger.critical(
                "circuit_breaker_halt",
                reason=reason.value,
                message=message,
            )

    def reset(self, operator: str = "system") -> None:
        """
        Resume trading after a halt.

        Resets the breaker to ACTIVE state and clears the consecutive-loss
        counter.  Daily P&L is NOT reset (it resets at midnight UTC).

        Parameters
        ----------
        operator : str
            Identifier of the person or system performing the reset (audit trail).
        """
        with self._lock:
            old_state = self._state
            old_reason = self._halt_reason

            self._state = BreakerState.ACTIVE
            self._halt_reason = None
            self._halt_message = ""
            self._halt_time = None
            self._cooldown_until = None
            self._consecutive_losses = 0

            self._log_event("RESET", {
                "operator": operator,
                "previous_state": old_state.value,
                "previous_reason": old_reason.value if old_reason else "",
            })

            logger.info(
                "circuit_breaker_reset",
                operator=operator,
                previous_state=old_state.value,
            )

    # ── Status ──

    def get_status(self) -> dict[str, Any]:
        """
        Return the current circuit-breaker state and statistics.

        Safe to call from any thread -- acquires the lock.
        """
        with self._lock:
            self._check_cooldown_expiry()
            now = datetime.now(timezone.utc)
            self._maybe_reset_daily(now)

            hourly_pnl = self._calc_hourly_pnl(now)
            minute_ago = now - timedelta(minutes=1)
            hour_ago = now - timedelta(hours=1)

            return {
                "state": self._state.value,
                "halt_reason": self._halt_reason.value if self._halt_reason else None,
                "halt_message": self._halt_message,
                "halt_time": self._halt_time.isoformat() if self._halt_time else None,
                "daily_pnl": round(self._daily_pnl, 2),
                "hourly_pnl": round(hourly_pnl, 2),
                "consecutive_losses": self._consecutive_losses,
                "orders_last_minute": sum(
                    1 for t in self._order_timestamps if t >= minute_ago
                ),
                "orders_last_hour": sum(
                    1 for t in self._order_timestamps if t >= hour_ago
                ),
                "total_trades_today": sum(
                    1 for tr in self._trades
                    if tr.timestamp.date() == now.date()
                ),
                "config": {
                    "max_daily_loss_pct": self._config.max_daily_loss_pct,
                    "max_daily_loss_usd": self._config.max_daily_loss_usd,
                    "max_hourly_loss_pct": self._config.max_hourly_loss_pct,
                    "max_hourly_loss_usd": self._config.max_hourly_loss_usd,
                    "max_consecutive_losses": self._config.max_consecutive_losses,
                    "max_orders_per_minute": self._config.max_orders_per_minute,
                    "flash_crash_threshold_pct": self._config.flash_crash_threshold_pct,
                    "portfolio_value_usd": self._config.portfolio_value_usd,
                },
                "cooldown_until": (
                    self._cooldown_until.isoformat()
                    if self._cooldown_until else None
                ),
            }

    @property
    def is_halted(self) -> bool:
        """Quick check -- is trading currently blocked?"""
        with self._lock:
            self._check_cooldown_expiry()
            return self._state != BreakerState.ACTIVE

    def update_portfolio_value(self, value_usd: float) -> None:
        """
        Update the portfolio value used for percentage-based thresholds.

        Call this at the start of each cycle or after significant P&L changes.
        """
        with self._lock:
            self._config.portfolio_value_usd = value_usd

    def get_event_log(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the most recent circuit-breaker events."""
        with self._lock:
            events = list(self._event_log)
            return events[-limit:]

    # ── Internal ──

    def _trip(self, reason: HaltReason, message: str) -> None:
        """Transition to TRIPPED state (must be called under lock)."""
        self._state = BreakerState.TRIPPED
        self._halt_reason = reason
        self._halt_message = message
        self._halt_time = datetime.now(timezone.utc)

        self._log_event("TRIPPED", {
            "reason": reason.value,
            "message": message,
        })

        logger.critical(
            "circuit_breaker_tripped",
            reason=reason.value,
            message=message,
            daily_pnl=round(self._daily_pnl, 2),
            consecutive_losses=self._consecutive_losses,
        )

    def _enter_cooldown(self, message: str) -> None:
        """Enter a temporary cooldown (must be called under lock)."""
        self._state = BreakerState.COOLDOWN
        self._cooldown_until = datetime.now(timezone.utc) + timedelta(
            seconds=self._config.cooldown_seconds
        )
        self._halt_message = message

        self._log_event("COOLDOWN", {
            "message": message,
            "until": self._cooldown_until.isoformat(),
        })

        logger.warning(
            "circuit_breaker_cooldown",
            message=message,
            seconds=self._config.cooldown_seconds,
        )

    def _check_cooldown_expiry(self) -> None:
        """Auto-resume from cooldown if configured (must be called under lock)."""
        if (
            self._state == BreakerState.COOLDOWN
            and self._cooldown_until
            and datetime.now(timezone.utc) >= self._cooldown_until
        ):
            if self._config.auto_reset_after_cooldown:
                self._state = BreakerState.ACTIVE
                self._halt_message = ""
                self._cooldown_until = None
                self._log_event("COOLDOWN_EXPIRED_AUTO_RESET", {})
                logger.info("circuit_breaker_cooldown_expired_auto_reset")
            else:
                # Escalate to TRIPPED -- operator must reset
                self._state = BreakerState.TRIPPED
                self._halt_reason = HaltReason.RATE_LIMIT
                self._halt_time = datetime.now(timezone.utc)
                self._log_event("COOLDOWN_ESCALATED_TO_TRIP", {})
                logger.warning("circuit_breaker_cooldown_escalated")

    def _maybe_reset_daily(self, now: datetime) -> None:
        """Reset daily counters at midnight UTC (must be called under lock)."""
        today = now.strftime("%Y-%m-%d")
        if self._daily_reset_date != today:
            if self._daily_reset_date:
                self._log_event("DAILY_RESET", {
                    "previous_date": self._daily_reset_date,
                    "final_daily_pnl": round(self._daily_pnl, 2),
                })
            self._daily_pnl = 0.0
            self._daily_reset_date = today

    def _calc_hourly_pnl(self, now: datetime) -> float:
        """Sum P&L for trades in the last 60 minutes (must be called under lock)."""
        cutoff = now - timedelta(hours=1)
        return sum(
            tr.pnl for tr in self._trades if tr.timestamp >= cutoff
        )

    def _check_flash_crash(
        self,
        symbol: str,
        current_price: float,
        now: datetime,
    ) -> str:
        """
        Detect sudden extreme price moves (must be called under lock).

        Returns an empty string if no flash crash, or a description if detected.
        """
        history = self._price_history.get(symbol)
        if not history:
            return ""

        window = now - timedelta(
            seconds=self._config.flash_crash_window_seconds
        )

        # Find the price at the start of the window
        oldest_price: float | None = None
        for ts, price in history:
            if ts >= window:
                oldest_price = price
                break

        if oldest_price is None or oldest_price == 0:
            return ""

        change_pct = abs(current_price - oldest_price) / oldest_price
        if change_pct >= self._config.flash_crash_threshold_pct:
            direction = "up" if current_price > oldest_price else "down"
            return (
                f"Flash crash detected on {symbol}: {change_pct:.2%} {direction} "
                f"in {self._config.flash_crash_window_seconds}s "
                f"(threshold: {self._config.flash_crash_threshold_pct:.2%})"
            )

        return ""

    def _log_event(self, event: str, details: dict[str, Any]) -> None:
        """Append to internal audit log (must be called under lock)."""
        self._event_log.append({
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state": self._state.value,
            **details,
        })
