"""SQLAlchemy ORM models for the Hivemind platform."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── Enum types ──────────────────────────────────────────────────────────────


class ContributorStatus(str, PyEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    SUSPENDED = "suspended"


class TeamStatus(str, PyEnum):
    ACTIVE = "active"
    PROVISIONAL = "provisional"
    DISSOLVED = "dissolved"


class ActivationMode(str, PyEnum):
    ALWAYS = "always"
    CONDITIONAL = "conditional"


class AgentStatusDB(str, PyEnum):
    FOUNDING = "founding"
    REGISTERED = "registered"
    ASSIGNED = "assigned"
    ACTIVE = "active"
    PROBATION = "probation"
    FIRED = "fired"


class ProviderType(str, PyEnum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"


class SignalOutcome(str, PyEnum):
    PENDING = "pending"
    CORRECT = "correct"
    INCORRECT = "incorrect"


# ── Tables ──────────────────────────────────────────────────────────────────


class ContributorRow(Base):
    __tablename__ = "contributors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    api_key_anthropic_enc = Column(LargeBinary, nullable=True)
    api_key_openai_enc = Column(LargeBinary, nullable=True)
    api_key_google_enc = Column(LargeBinary, nullable=True)
    max_agents = Column(Integer, nullable=False, default=1)
    cost_limit_usd = Column(Numeric(precision=12, scale=4), nullable=True)
    total_cost_usd = Column(
        Numeric(precision=12, scale=4), nullable=False, default=Decimal("0")
    )
    status = Column(
        Enum(ContributorStatus), nullable=False, default=ContributorStatus.ACTIVE
    )
    api_token_hash = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    agents = relationship("AgentRow", back_populates="contributor")


class TeamRow(Base):
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    discipline = Column(Text, nullable=False)
    status = Column(Enum(TeamStatus), nullable=False, default=TeamStatus.ACTIVE)
    manager_prompt = Column(Text, nullable=True)
    manager_knowledge_base = Column(Text, nullable=True)
    data_keys = Column(JSONB, nullable=False, default=list)
    weight = Column(Float, nullable=False, default=1.0)
    activation_mode = Column(
        Enum(ActivationMode), nullable=False, default=ActivationMode.ALWAYS
    )
    activation_condition = Column(Text, nullable=True)
    min_agents = Column(Integer, nullable=False, default=2)
    is_system = Column(Boolean, nullable=False, default=False)
    created_by = Column(String, nullable=False, default="system")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    agents = relationship("AgentRow", back_populates="team")


class AgentRow(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contributor_id = Column(
        UUID(as_uuid=True), ForeignKey("contributors.id"), nullable=True
    )
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    role = Column(String, nullable=False)
    agent_class = Column(String, nullable=True)  # Python class name for founding agents
    model = Column(String, nullable=False, default="claude-sonnet-4-6")
    provider = Column(
        Enum(ProviderType), nullable=False, default=ProviderType.ANTHROPIC
    )
    system_prompt = Column(Text, nullable=True)
    status = Column(
        Enum(AgentStatusDB), nullable=False, default=AgentStatusDB.REGISTERED
    )
    total_signals = Column(Integer, nullable=False, default=0)
    correct_signals = Column(Integer, nullable=False, default=0)
    total_cost_usd = Column(
        Numeric(precision=12, scale=4), nullable=False, default=Decimal("0")
    )
    probation_started_at = Column(DateTime(timezone=True), nullable=True)
    fired_at = Column(DateTime(timezone=True), nullable=True)
    quarantine_signals_remaining = Column(Integer, nullable=False, default=0)
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    contributor = relationship("ContributorRow", back_populates="agents")
    team = relationship("TeamRow", back_populates="agents")
    signals = relationship("SignalRow", back_populates="agent")


class CycleRow(Base):
    __tablename__ = "cycles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_secs = Column(Float, nullable=True)
    regime = Column(String, nullable=True)
    coins_analyzed = Column(Integer, nullable=False, default=0)
    signals_produced = Column(Integer, nullable=False, default=0)
    orders_executed = Column(Integer, nullable=False, default=0)
    portfolio_value = Column(Numeric(precision=14, scale=4), nullable=True)
    error = Column(Text, nullable=True)

    signals = relationship("SignalRow", back_populates="cycle")


class SignalRow(Base):
    __tablename__ = "signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_id = Column(Integer, ForeignKey("cycles.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    symbol = Column(String, nullable=False)
    action = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    conviction = Column(Integer, nullable=True)
    reasoning = Column(Text, nullable=True)
    price_at_signal = Column(Numeric(precision=18, scale=8), nullable=True)
    outcome = Column(
        Enum(SignalOutcome), nullable=False, default=SignalOutcome.PENDING
    )
    evaluated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    cycle = relationship("CycleRow", back_populates="signals")
    agent = relationship("AgentRow", back_populates="signals")


class BoardDecisionRow(Base):
    __tablename__ = "board_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    decision_type = Column(String, nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    reasoning = Column(Text, nullable=True)
    decided_by = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class CeoPostRow(Base):
    __tablename__ = "ceo_posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_type = Column(String, nullable=False)  # "blog", "memo", "briefing"
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)  # Short summary for previews
    market_context = Column(JSONB, nullable=True)  # Regime, F&G, BTC price at time of writing
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
