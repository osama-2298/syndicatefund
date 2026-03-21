"""Pydantic models for the Intelligence Module (Fast Loop)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    CRITICAL = "critical"  # Immediate action required
    HIGH = "high"          # Needs attention this loop
    MEDIUM = "medium"      # Informational, may affect next cycle
    LOW = "low"            # Logged for analysis


class IntelEventType(str, Enum):
    NEWS_ALERT = "news_alert"
    WHALE_ALERT = "whale_alert"
    FLASH_CRASH = "flash_crash"
    FLASH_PUMP = "flash_pump"
    CORRELATION_SPIKE = "correlation_spike"
    RISK_ACTION = "risk_action"
    STOP_TRIGGERED = "stop_triggered"
    EXCHANGE_ANNOUNCEMENT = "exchange_announcement"


class IntelEvent(BaseModel):
    """A single intelligence event from the fast loop."""

    event_type: IntelEventType
    severity: AlertSeverity
    source: str  # "cryptopanic", "price_monitor", "whale_alert", "exchange"
    title: str
    detail: dict = Field(default_factory=dict)
    symbols: list[str] = Field(default_factory=list)
    acted_upon: bool = False
    action_taken: str | None = None
    scout_agent_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "source": self.source,
            "title": self.title,
            "detail": self.detail,
            "symbols": self.symbols,
            "acted_upon": self.acted_upon,
            "action_taken": self.action_taken,
            "scout_agent_id": self.scout_agent_id,
            "timestamp": self.timestamp.isoformat(),
        }


class FastLoopResult(BaseModel):
    """Result of a single fast loop iteration."""

    events: list[IntelEvent] = Field(default_factory=list)
    risk_actions_taken: int = 0
    news_checked: int = 0
    prices_checked: int = 0
    duration_ms: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "events": [e.to_dict() for e in self.events],
            "risk_actions_taken": self.risk_actions_taken,
            "news_checked": self.news_checked,
            "prices_checked": self.prices_checked,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }
