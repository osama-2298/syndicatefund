"""
Health Monitoring and Dead Man's Switch.

Every critical component in the system registers with the HeartbeatMonitor
and periodically calls pulse().  If any component misses its heartbeat window
the monitor flags it as unhealthy.

The DeadManSwitch is the nuclear option: if the main trading loop fails to
pulse within its timeout, the switch triggers an automatic halt via the
circuit breaker.  This prevents a zombie process from leaving stale orders
on the book.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


# ═══════════════════════════════════════════
#  Enums
# ═══════════════════════════════════════════


class ComponentState(str, Enum):
    """Health state of a single monitored component."""

    HEALTHY = "HEALTHY"         # Pulsing within expected interval
    DEGRADED = "DEGRADED"       # Pulsing but slower than expected
    UNHEALTHY = "UNHEALTHY"     # Missed heartbeat window entirely
    UNKNOWN = "UNKNOWN"         # Never pulsed (just registered)


class SystemHealth(str, Enum):
    """Aggregate system health."""

    GREEN = "GREEN"             # All components healthy
    YELLOW = "YELLOW"           # Some components degraded
    RED = "RED"                 # One or more critical components unhealthy
    DEAD = "DEAD"               # Dead man's switch has fired


# ═══════════════════════════════════════════
#  Data Models
# ═══════════════════════════════════════════


class ComponentInfo(BaseModel):
    """Registration and runtime data for a monitored component."""

    name: str
    interval_seconds: float = 60.0       # Expected pulse interval
    timeout_seconds: float = 120.0       # After this long without a pulse: UNHEALTHY
    degraded_seconds: float = 90.0       # After this long without a pulse: DEGRADED
    is_critical: bool = True             # If True, unhealthy state triggers RED
    last_pulse: datetime | None = None
    pulse_count: int = 0
    state: ComponentState = ComponentState.UNKNOWN
    last_message: str = ""               # Optional status message from component
    registered_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class HealthStatus(BaseModel):
    """
    Aggregate health report for the entire system.

    Returned by HeartbeatMonitor.get_status().
    """

    system_health: SystemHealth = SystemHealth.GREEN
    components: dict[str, dict[str, Any]] = Field(default_factory=dict)
    healthy_count: int = 0
    degraded_count: int = 0
    unhealthy_count: int = 0
    unknown_count: int = 0
    dead_man_switch_active: bool = False
    dead_man_switch_remaining_seconds: float | None = None
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    @property
    def is_operational(self) -> bool:
        """True if the system is GREEN or YELLOW (can still trade)."""
        return self.system_health in (SystemHealth.GREEN, SystemHealth.YELLOW)


# ═══════════════════════════════════════════
#  HeartbeatMonitor
# ═══════════════════════════════════════════


class HeartbeatMonitor:
    """
    Central health monitor for all system components.

    Components register themselves with expected pulse intervals, then call
    pulse() periodically.  The monitor evaluates health on demand via
    check_health() or get_status().

    Thread-safe -- all operations acquire a lock.
    """

    def __init__(self) -> None:
        self._components: dict[str, ComponentInfo] = {}
        self._lock = threading.Lock()
        self._on_unhealthy_callbacks: list[Callable[[str, ComponentInfo], None]] = []

    # ── Registration ──

    def register_component(
        self,
        name: str,
        interval_seconds: float = 60.0,
        timeout_seconds: float | None = None,
        degraded_seconds: float | None = None,
        is_critical: bool = True,
    ) -> None:
        """
        Register a component for health monitoring.

        Parameters
        ----------
        name : str
            Unique identifier for the component (e.g. "order_manager",
            "binance_ws", "signal_aggregator").
        interval_seconds : float
            How often the component is expected to pulse.
        timeout_seconds : float, optional
            Seconds without a pulse before marking UNHEALTHY.
            Defaults to 2x interval.
        degraded_seconds : float, optional
            Seconds without a pulse before marking DEGRADED.
            Defaults to 1.5x interval.
        is_critical : bool
            If True, this component being UNHEALTHY makes the whole system RED.
        """
        if timeout_seconds is None:
            timeout_seconds = interval_seconds * 2.0
        if degraded_seconds is None:
            degraded_seconds = interval_seconds * 1.5

        with self._lock:
            self._components[name] = ComponentInfo(
                name=name,
                interval_seconds=interval_seconds,
                timeout_seconds=timeout_seconds,
                degraded_seconds=degraded_seconds,
                is_critical=is_critical,
            )

        logger.info(
            "component_registered",
            name=name,
            interval=interval_seconds,
            timeout=timeout_seconds,
            critical=is_critical,
        )

    def deregister_component(self, name: str) -> None:
        """Remove a component from monitoring."""
        with self._lock:
            self._components.pop(name, None)
        logger.info("component_deregistered", name=name)

    # ── Heartbeat ──

    def pulse(self, name: str, message: str = "") -> bool:
        """
        Record a heartbeat from a component.

        Parameters
        ----------
        name : str
            The component name (must be registered).
        message : str, optional
            Optional status message (e.g. "processed 42 signals").

        Returns True if the component is registered, False if unknown.
        """
        with self._lock:
            comp = self._components.get(name)
            if comp is None:
                logger.warning("pulse_from_unknown_component", name=name)
                return False

            comp.last_pulse = datetime.now(timezone.utc)
            comp.pulse_count += 1
            comp.state = ComponentState.HEALTHY
            comp.last_message = message

        return True

    # ── Health evaluation ──

    def check_health(self) -> SystemHealth:
        """
        Evaluate all components and return the aggregate system health.

        - GREEN: all components HEALTHY or UNKNOWN (just registered).
        - YELLOW: at least one DEGRADED, but no critical UNHEALTHY.
        - RED: at least one critical component is UNHEALTHY.
        """
        with self._lock:
            now = datetime.now(timezone.utc)
            has_degraded = False
            has_critical_unhealthy = False

            for comp in self._components.values():
                self._evaluate_component(comp, now)

                if comp.state == ComponentState.DEGRADED:
                    has_degraded = True
                elif comp.state == ComponentState.UNHEALTHY:
                    if comp.is_critical:
                        has_critical_unhealthy = True
                    else:
                        has_degraded = True  # Non-critical unhealthy = yellow

                    # Fire callbacks
                    for cb in self._on_unhealthy_callbacks:
                        try:
                            cb(comp.name, comp)
                        except Exception as e:
                            logger.error(
                                "unhealthy_callback_failed",
                                component=comp.name,
                                error=str(e),
                            )

            if has_critical_unhealthy:
                return SystemHealth.RED
            if has_degraded:
                return SystemHealth.YELLOW
            return SystemHealth.GREEN

    def get_status(self) -> HealthStatus:
        """
        Generate a full health report.

        Evaluates all components and returns a HealthStatus with per-component
        details and aggregate counts.
        """
        with self._lock:
            now = datetime.now(timezone.utc)
            components_info: dict[str, dict[str, Any]] = {}

            healthy = 0
            degraded = 0
            unhealthy = 0
            unknown = 0
            has_critical_unhealthy = False
            has_degraded = False

            for name, comp in self._components.items():
                self._evaluate_component(comp, now)

                seconds_since = None
                if comp.last_pulse:
                    seconds_since = (now - comp.last_pulse).total_seconds()

                components_info[name] = {
                    "state": comp.state.value,
                    "is_critical": comp.is_critical,
                    "pulse_count": comp.pulse_count,
                    "last_pulse": (
                        comp.last_pulse.isoformat() if comp.last_pulse else None
                    ),
                    "seconds_since_pulse": (
                        round(seconds_since, 1) if seconds_since is not None else None
                    ),
                    "interval_seconds": comp.interval_seconds,
                    "timeout_seconds": comp.timeout_seconds,
                    "last_message": comp.last_message,
                }

                if comp.state == ComponentState.HEALTHY:
                    healthy += 1
                elif comp.state == ComponentState.DEGRADED:
                    degraded += 1
                    has_degraded = True
                elif comp.state == ComponentState.UNHEALTHY:
                    unhealthy += 1
                    if comp.is_critical:
                        has_critical_unhealthy = True
                    else:
                        has_degraded = True
                else:
                    unknown += 1

            if has_critical_unhealthy:
                system_health = SystemHealth.RED
            elif has_degraded:
                system_health = SystemHealth.YELLOW
            else:
                system_health = SystemHealth.GREEN

            return HealthStatus(
                system_health=system_health,
                components=components_info,
                healthy_count=healthy,
                degraded_count=degraded,
                unhealthy_count=unhealthy,
                unknown_count=unknown,
            )

    def on_unhealthy(
        self,
        callback: Callable[[str, ComponentInfo], None],
    ) -> None:
        """
        Register a callback to be invoked when a component goes UNHEALTHY.

        The callback receives (component_name, ComponentInfo).
        Useful for triggering alerts or circuit-breaker halts.
        """
        with self._lock:
            self._on_unhealthy_callbacks.append(callback)

    # ── Internal ──

    def _evaluate_component(self, comp: ComponentInfo, now: datetime) -> None:
        """
        Update a component's state based on how long since its last pulse.
        Must be called under lock.
        """
        if comp.last_pulse is None:
            comp.state = ComponentState.UNKNOWN
            return

        elapsed = (now - comp.last_pulse).total_seconds()

        if elapsed <= comp.interval_seconds * 1.1:
            # Within expected interval (with 10% grace)
            comp.state = ComponentState.HEALTHY
        elif elapsed <= comp.degraded_seconds:
            comp.state = ComponentState.HEALTHY  # Still within degraded threshold
        elif elapsed <= comp.timeout_seconds:
            comp.state = ComponentState.DEGRADED
        else:
            comp.state = ComponentState.UNHEALTHY


# ═══════════════════════════════════════════
#  DeadManSwitch
# ═══════════════════════════════════════════


class DeadManSwitch:
    """
    Auto-halt if the main trading loop stops pulsing.

    The trading loop must call pulse() at least once per ``timeout_seconds``.
    If it fails to do so (crash, hang, deadlock), the switch fires the
    ``on_trigger`` callback -- typically wired to CircuitBreaker.trigger_halt().

    The switch runs a background timer thread that checks for missed pulses.
    Call start() to begin monitoring and stop() to clean up.

    Usage:
        dms = DeadManSwitch(
            timeout_seconds=120,
            on_trigger=lambda: breaker.trigger_halt(HaltReason.SYSTEM_ERROR,
                                                    "Dead man's switch fired"),
        )
        dms.start()

        # In the main loop:
        while running:
            dms.pulse()
            do_trading_cycle()

        dms.stop()
    """

    def __init__(
        self,
        timeout_seconds: float = 120.0,
        check_interval_seconds: float = 10.0,
        on_trigger: Callable[[], None] | None = None,
        name: str = "main_loop",
    ) -> None:
        self._timeout = timeout_seconds
        self._check_interval = check_interval_seconds
        self._on_trigger = on_trigger
        self._name = name

        self._last_pulse: datetime | None = None
        self._triggered = False
        self._running = False
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    def start(self) -> None:
        """Begin monitoring.  The first pulse must arrive within timeout_seconds."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._triggered = False
            self._last_pulse = datetime.now(timezone.utc)
            self._schedule_check()

        logger.info(
            "dead_man_switch_started",
            name=self._name,
            timeout=self._timeout,
        )

    def stop(self) -> None:
        """Stop monitoring and cancel pending timers."""
        with self._lock:
            self._running = False
            if self._timer:
                self._timer.cancel()
                self._timer = None

        logger.info("dead_man_switch_stopped", name=self._name)

    def pulse(self) -> None:
        """
        Record a heartbeat from the main loop.

        Must be called at least once per timeout_seconds or the switch fires.
        """
        with self._lock:
            self._last_pulse = datetime.now(timezone.utc)
            self._triggered = False

    @property
    def is_triggered(self) -> bool:
        """Has the switch fired?"""
        with self._lock:
            return self._triggered

    @property
    def remaining_seconds(self) -> float | None:
        """Seconds until the switch fires, or None if stopped."""
        with self._lock:
            if not self._running or self._last_pulse is None:
                return None
            elapsed = (
                datetime.now(timezone.utc) - self._last_pulse
            ).total_seconds()
            return max(0.0, self._timeout - elapsed)

    def get_status(self) -> dict[str, Any]:
        """Return current switch state."""
        with self._lock:
            return {
                "name": self._name,
                "running": self._running,
                "triggered": self._triggered,
                "timeout_seconds": self._timeout,
                "last_pulse": (
                    self._last_pulse.isoformat()
                    if self._last_pulse else None
                ),
                "remaining_seconds": (
                    round(self.remaining_seconds, 1)
                    if self.remaining_seconds is not None else None
                ),
            }

    # ── Internal ──

    def _schedule_check(self) -> None:
        """Schedule the next liveness check (must be called under lock)."""
        if not self._running:
            return
        self._timer = threading.Timer(self._check_interval, self._check)
        self._timer.daemon = True  # Don't prevent process exit
        self._timer.start()

    def _check(self) -> None:
        """Periodic check -- fire if pulse has timed out."""
        callback = None

        with self._lock:
            if not self._running:
                return

            now = datetime.now(timezone.utc)

            if self._last_pulse is not None:
                elapsed = (now - self._last_pulse).total_seconds()

                if elapsed >= self._timeout and not self._triggered:
                    self._triggered = True
                    logger.critical(
                        "dead_man_switch_fired",
                        name=self._name,
                        elapsed_seconds=round(elapsed, 1),
                        timeout=self._timeout,
                    )

                    # Capture callback to fire outside lock (avoid deadlocks)
                    callback = self._on_trigger

            # Schedule next check regardless of outcome (for status reporting)
            self._schedule_check()

        # Execute callback outside the lock
        if callback is not None:
            try:
                callback()
            except Exception as e:
                logger.error(
                    "dead_man_switch_callback_failed",
                    name=self._name,
                    error=str(e),
                )
