"""Immutable audit logging for the Syndicate compliance layer.

Every state-changing action (trades, config changes, risk breaches, halts) is
captured as an append-only AuditEntry.  Entries are never modified or deleted.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


# ── Enums ────────────────────────────────────────────────────────────────────


class AuditAction(str, PyEnum):
    """Canonical action verbs for audit entries."""

    TRADE_OPENED = "trade_opened"
    TRADE_CLOSED = "trade_closed"
    TRADE_MODIFIED = "trade_modified"
    STATUS_CHANGE = "status_change"
    CONFIG_CHANGE = "config_change"
    RISK_BREACH = "risk_breach"
    HALT_ACTIVATED = "halt_activated"
    HALT_DEACTIVATED = "halt_deactivated"
    KYC_VERIFIED = "kyc_verified"
    KYC_REJECTED = "kyc_rejected"
    SURVEILLANCE_ALERT = "surveillance_alert"
    LOGIN = "login"
    PERMISSION_CHANGE = "permission_change"


class EntityType(str, PyEnum):
    """High-level entity categories that can be audited."""

    TRADE = "trade"
    POSITION = "position"
    AGENT = "agent"
    TEAM = "team"
    PORTFOLIO = "portfolio"
    CONFIG = "config"
    USER = "user"
    SYSTEM = "system"


# ── Pydantic model ──────────────────────────────────────────────────────────


class AuditEntry(BaseModel):
    """Single immutable audit record."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    actor: str = Field(
        ..., description="Who performed the action (user-id, agent-class, 'system')"
    )
    action: str = Field(..., description="Action verb from AuditAction or free-form")
    entity_type: str = Field(..., description="Category from EntityType or free-form")
    entity_id: str = Field(..., description="Primary key of the affected entity")
    old_value: dict[str, Any] | None = Field(
        default=None, description="State before the change"
    )
    new_value: dict[str, Any] | None = Field(
        default=None, description="State after the change"
    )
    reason: str | None = Field(
        default=None, description="Human-readable justification"
    )
    ip_address: str | None = Field(
        default=None, description="Originating IP when available"
    )

    class Config:
        frozen = True  # Immutability: entries cannot be mutated once created


# ── AuditLogger ─────────────────────────────────────────────────────────────


class AuditLogger:
    """Thread-safe, append-only audit logger.

    Entries are held in memory and can be flushed to any persistent store via
    the ``flush`` callback.  By default they are also emitted through structlog
    for immediate observability.
    """

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._lock = threading.Lock()

    # ── Convenience logging methods ─────────────────────────────────────

    def log_trade(
        self,
        *,
        actor: str,
        action: str,
        trade_id: str,
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
        reason: str | None = None,
        ip_address: str | None = None,
    ) -> AuditEntry:
        return self._append(
            actor=actor,
            action=action,
            entity_type=EntityType.TRADE,
            entity_id=trade_id,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            ip_address=ip_address,
        )

    def log_status_change(
        self,
        *,
        actor: str,
        entity_type: str,
        entity_id: str,
        old_status: str,
        new_status: str,
        reason: str | None = None,
        ip_address: str | None = None,
    ) -> AuditEntry:
        return self._append(
            actor=actor,
            action=AuditAction.STATUS_CHANGE,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value={"status": old_status},
            new_value={"status": new_status},
            reason=reason,
            ip_address=ip_address,
        )

    def log_config_change(
        self,
        *,
        actor: str,
        config_key: str,
        old_value: Any,
        new_value: Any,
        reason: str | None = None,
        ip_address: str | None = None,
    ) -> AuditEntry:
        return self._append(
            actor=actor,
            action=AuditAction.CONFIG_CHANGE,
            entity_type=EntityType.CONFIG,
            entity_id=config_key,
            old_value={"value": old_value},
            new_value={"value": new_value},
            reason=reason,
            ip_address=ip_address,
        )

    def log_risk_breach(
        self,
        *,
        actor: str,
        entity_type: str,
        entity_id: str,
        breach_detail: dict[str, Any],
        reason: str | None = None,
    ) -> AuditEntry:
        return self._append(
            actor=actor,
            action=AuditAction.RISK_BREACH,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=None,
            new_value=breach_detail,
            reason=reason,
        )

    def log_halt(
        self,
        *,
        actor: str,
        activated: bool,
        entity_id: str = "system",
        reason: str | None = None,
        ip_address: str | None = None,
    ) -> AuditEntry:
        action = (
            AuditAction.HALT_ACTIVATED if activated else AuditAction.HALT_DEACTIVATED
        )
        return self._append(
            actor=actor,
            action=action,
            entity_type=EntityType.SYSTEM,
            entity_id=entity_id,
            old_value={"halted": not activated},
            new_value={"halted": activated},
            reason=reason,
            ip_address=ip_address,
        )

    # ── Query methods ───────────────────────────────────────────────────

    def get_by_entity(
        self, entity_type: str, entity_id: str
    ) -> list[AuditEntry]:
        with self._lock:
            return [
                e
                for e in self._entries
                if e.entity_type == entity_type and e.entity_id == entity_id
            ]

    def get_by_actor(self, actor: str) -> list[AuditEntry]:
        with self._lock:
            return [e for e in self._entries if e.actor == actor]

    def get_by_date_range(
        self, start: datetime, end: datetime
    ) -> list[AuditEntry]:
        start_iso = start.isoformat()
        end_iso = end.isoformat()
        with self._lock:
            return [
                e
                for e in self._entries
                if start_iso <= e.timestamp <= end_iso
            ]

    @property
    def entries(self) -> list[AuditEntry]:
        """Return a snapshot of all entries (defensive copy)."""
        with self._lock:
            return list(self._entries)

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    # ── Internal ────────────────────────────────────────────────────────

    def _append(
        self,
        *,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str,
        old_value: dict[str, Any] | None,
        new_value: dict[str, Any] | None,
        reason: str | None = None,
        ip_address: str | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            ip_address=ip_address,
        )
        with self._lock:
            self._entries.append(entry)

        # Emit via structlog for immediate observability / log shipping
        logger.info(
            "audit_entry",
            audit_id=entry.id,
            actor=entry.actor,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            reason=entry.reason,
        )
        return entry


# ── Module-level singleton ──────────────────────────────────────────────────

_audit_logger: AuditLogger | None = None
_singleton_lock = threading.Lock()


def get_audit_logger() -> AuditLogger:
    """Return (or create) the global AuditLogger instance."""
    global _audit_logger
    with _singleton_lock:
        if _audit_logger is None:
            _audit_logger = AuditLogger()
        return _audit_logger
