"""SQLAlchemy ORM models for the Syndicate platform."""

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
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
)
from sqlalchemy import func
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
    __table_args__ = (
        Index("ix_contributors_api_token_hash", "api_token_hash"),
    )

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
    # v2: Contributor role preference
    preferred_role = Column(String, nullable=False, default="analyst")  # analyst/scout/watchdog/research/any
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

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
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    agents = relationship("AgentRow", back_populates="team")


class AgentRow(Base):
    __tablename__ = "agents"
    __table_args__ = (
        Index("ix_agents_team_id", "team_id"),
        Index("ix_agents_contributor_id", "contributor_id"),
        Index("ix_agents_status", "status"),
    )

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
    # v2: Contributor role system
    role_type = Column(String, nullable=False, default="analyst")  # analyst/scout/watchdog/research/founding
    fast_loop_source = Column(String, nullable=True)  # For scouts: what they monitor
    last_active_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    contributor = relationship("ContributorRow", back_populates="agents")
    team = relationship("TeamRow", back_populates="agents")
    signals = relationship("SignalRow", back_populates="agent")


class CycleRow(Base):
    __tablename__ = "cycles"
    __table_args__ = (
        Index("ix_cycles_started_at", "started_at"),
        Index("ix_cycles_completed_at", "completed_at"),
    )

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
    # v2: Cycle type and quant-only flag
    cycle_type = Column(String, nullable=False, default="slow")  # slow (4h) or fast (15min)
    quant_only = Column(Boolean, nullable=False, default=False)  # True if no LLM agents invoked
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    signals = relationship("SignalRow", back_populates="cycle")


class SignalRow(Base):
    __tablename__ = "signals"
    __table_args__ = (
        Index("ix_signals_cycle_id", "cycle_id"),
        Index("ix_signals_agent_id", "agent_id"),
        Index("ix_signals_symbol", "symbol"),
        Index("ix_signals_outcome", "outcome"),
        Index("ix_signals_created_at", "created_at"),
    )

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
    __table_args__ = (
        Index("ix_board_decisions_session_id", "session_id"),
        Index("ix_board_decisions_created_at", "created_at"),
    )

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
    __table_args__ = (
        Index("ix_ceo_posts_post_type", "post_type"),
        Index("ix_ceo_posts_created_at", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_type = Column(String, nullable=False)  # "blog", "memo", "briefing"
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)  # Short summary for previews
    market_context = Column(JSONB, nullable=True)  # Regime, F&G, BTC price at time of writing
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class ResearchReportRow(Base):
    __tablename__ = "research_reports"
    __table_args__ = (
        Index("ix_research_reports_researcher", "researcher"),
        Index("ix_research_reports_report_type", "report_type"),
        Index("ix_research_reports_created_at", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    researcher = Column(String, nullable=False)  # head_of_research, quant_researcher, strategy_researcher
    report_type = Column(String, nullable=False)  # signal_decay, performance_attribution, correlation_analysis, data_source_eval, hypothesis_test, weekly_digest, risk_analysis
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    findings = Column(JSONB, nullable=True)
    recommendations = Column(JSONB, nullable=True)
    data_context = Column(JSONB, nullable=True)  # {period, sample_size, symbols_analyzed, etc.}
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class PipelineEventType(str, PyEnum):
    """Known event types — used for validation, not as a DB enum."""
    CEO_DIRECTIVE = "ceo_directive"
    COO_SELECTION = "coo_selection"
    CRO_RULES = "cro_rules"
    TEAM_SIGNAL = "team_signal"
    AGGREGATION_RESULT = "aggregation_result"
    DISAGREEMENT = "disagreement"
    VERDICT = "verdict"
    TRADE_EXECUTED = "trade_executed"
    TRADE_CLOSED = "trade_closed"
    CEO_REVIEW = "ceo_review"
    CYCLE_END = "cycle_end"


class PipelineEventRow(Base):
    __tablename__ = "pipeline_events"
    __table_args__ = (
        Index("ix_pipeline_events_cycle_id", "cycle_id"),
        Index("ix_pipeline_events_event_type", "event_type"),
        Index("ix_pipeline_events_timestamp", "timestamp"),
    )

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_id   = Column(Integer, ForeignKey("cycles.id"), nullable=True)
    event_type = Column(String, nullable=False)  # Plain string — not a PG enum
    timestamp  = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    stage      = Column(String, nullable=False)
    actor      = Column(String, nullable=False)
    title      = Column(String, nullable=False)
    detail     = Column(JSONB, nullable=True)
    elapsed_ms = Column(Integer, nullable=True)


class AgentCommRow(Base):
    __tablename__ = "agent_comms"
    __table_args__ = (
        Index("ix_agent_comms_cycle_id", "cycle_id"),
        Index("ix_agent_comms_agent_class", "agent_class"),
        Index("ix_agent_comms_team", "team"),
        Index("ix_agent_comms_created_at", "created_at"),
    )

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_id    = Column(Integer, ForeignKey("cycles.id"), nullable=True)
    comm_type   = Column(String, nullable=False)   # agent_signal, manager_synthesis, ceo_directive, etc.
    agent_class = Column(String, nullable=True)     # "TechnicalTrendAgent", "CEO", "COO"
    agent_name  = Column(String, nullable=False)    # "Lena Karlsson"
    team        = Column(String, nullable=True)     # "technical", "sentiment", etc.
    symbol      = Column(String, nullable=True)     # "BTCUSDT" (null for executive comms)
    direction   = Column(String, nullable=True)     # "BULLISH"/"BEARISH"
    conviction  = Column(Integer, nullable=True)    # 0-10
    content     = Column(Text, nullable=False)      # Main message body
    metadata_   = Column("metadata", JSONB, nullable=False, default=dict)
    created_at  = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


# ── v2 Tables: Quant Scoring, Portfolio Risk, Fast Loop ─────────────────────

class QuantScoreRow(Base):
    """Deterministic scoring audit trail — one row per coin per cycle."""
    __tablename__ = "quant_scores"
    __table_args__ = (
        Index("ix_quant_scores_cycle_symbol", "cycle_id", "symbol"),
        Index("ix_quant_scores_created_at", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_id = Column(Integer, ForeignKey("cycles.id"), nullable=True)
    symbol = Column(String, nullable=False)
    technical_score = Column(Numeric(8, 4), nullable=True)
    sentiment_score = Column(Numeric(8, 4), nullable=True)
    macro_score = Column(Numeric(8, 4), nullable=True)
    onchain_score = Column(Numeric(8, 4), nullable=True)
    fundamental_score = Column(Numeric(8, 4), nullable=True)
    composite_score = Column(Numeric(8, 4), nullable=True)
    action = Column(String, nullable=True)  # BUY/SELL/HOLD
    confidence = Column(Numeric(8, 4), nullable=True)
    components = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class PortfolioRiskSnapshotRow(Base):
    """Portfolio-level risk state — taken each cycle and fast loop."""
    __tablename__ = "portfolio_risk_snapshots"
    __table_args__ = (
        Index("ix_prs_snapshot_at", "snapshot_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_heat = Column(Numeric(12, 6), nullable=True)
    max_drawdown_pct = Column(Numeric(12, 6), nullable=True)
    drawdown_ladder_level = Column(Integer, nullable=False, default=0)
    avg_correlation = Column(Numeric(12, 6), nullable=True)
    gross_exposure = Column(Numeric(14, 4), nullable=True)
    net_exposure = Column(Numeric(14, 4), nullable=True)
    positions_count = Column(Integer, nullable=True)
    detail = Column(JSONB, nullable=False, default=dict)
    snapshot_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class FastLoopEventRow(Base):
    """Events from the 15-minute fast intelligence loop."""
    __tablename__ = "fast_loop_events"
    __table_args__ = (
        Index("ix_fle_event_type", "event_type"),
        Index("ix_fle_created_at", "created_at"),
        Index("ix_fle_severity", "severity"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String, nullable=False)  # news_alert, whale_alert, flash_crash, risk_action
    severity = Column(String, nullable=False)  # critical, high, medium, low
    source = Column(String, nullable=False)  # twitter, cryptopanic, whale_monitor, price_monitor
    title = Column(String, nullable=False)
    detail = Column(JSONB, nullable=True)
    scout_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    acted_upon = Column(Boolean, nullable=False, default=False)
    action_taken = Column(String, nullable=True)  # reduce_position, halt_trading, alert_only
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


# ── Polymarket Tables ──────────────────────────────────────────────────────

class PmMarketRow(Base):
    __tablename__ = "pm_markets"
    __table_args__ = (
        Index("ix_pm_markets_city", "city"),
        Index("ix_pm_markets_date", "date"),
        Index("ix_pm_markets_condition_id", "condition_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condition_id = Column(String, unique=True, nullable=False)
    event_slug = Column(String, nullable=True)
    city = Column(String, nullable=False)
    date = Column(String, nullable=False)
    unit = Column(String, nullable=False, default="fahrenheit")
    bins = Column(JSONB, nullable=False, default=list)
    total_volume = Column(Numeric(18, 8), nullable=True, default=0.0)
    discovered_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    actual_high = Column(Numeric(12, 6), nullable=True)
    winning_bin = Column(Integer, nullable=True)


class PmForecastRow(Base):
    __tablename__ = "pm_forecasts"
    __table_args__ = (
        Index("ix_pm_forecasts_city_date", "city", "target_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    city = Column(String, nullable=False)
    target_date = Column(String, nullable=False)
    model = Column(String, nullable=False)
    member_highs = Column(JSONB, nullable=False, default=list)
    mean = Column(Numeric(12, 6), nullable=True)
    std = Column(Numeric(12, 6), nullable=True)
    fetched_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class PmAnalysisRow(Base):
    __tablename__ = "pm_analyses"
    __table_args__ = (
        Index("ix_pm_analyses_condition_id", "condition_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condition_id = Column(String, nullable=False)
    city = Column(String, nullable=False)
    date = Column(String, nullable=False)
    horizon_hours = Column(Float, nullable=False)
    forecast_mean = Column(Numeric(12, 6), nullable=True)
    forecast_std = Column(Numeric(12, 6), nullable=True)
    bin_probabilities = Column(JSONB, nullable=False, default=list)
    best_edge = Column(Numeric(12, 6), nullable=True)
    best_edge_bin = Column(Integer, nullable=True)
    analyzed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class PmTradeRow(Base):
    __tablename__ = "pm_trades"
    __table_args__ = (
        Index("ix_pm_trades_city", "city"),
        Index("ix_pm_trades_date", "date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condition_id = Column(String, nullable=False)
    token_id = Column(String, nullable=True)
    city = Column(String, nullable=False)
    date = Column(String, nullable=False)
    bin_label = Column(String, nullable=False)
    side = Column(String, nullable=False, default="YES")
    entry_price = Column(Numeric(18, 8), nullable=False)
    quantity = Column(Numeric(18, 8), nullable=False)
    model_prob = Column(Numeric(12, 6), nullable=True)
    edge_at_entry = Column(Numeric(12, 6), nullable=True)
    placed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    outcome = Column(Boolean, nullable=True)
    pnl = Column(Numeric(14, 4), nullable=True, default=0.0)
    is_paper = Column(Boolean, nullable=False, default=True)


class PmCalibrationRow(Base):
    __tablename__ = "pm_calibration"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    city = Column(String, nullable=False)
    date = Column(String, nullable=False)
    model = Column(String, nullable=False)
    forecast_mean = Column(Numeric(12, 6), nullable=True)
    forecast_std = Column(Numeric(12, 6), nullable=True)
    actual_high = Column(Numeric(12, 6), nullable=True)
    error = Column(Numeric(12, 6), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class PmPortfolioSnapshotRow(Base):
    __tablename__ = "pm_portfolio_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bankroll = Column(Numeric(14, 4), nullable=False)
    cash = Column(Numeric(14, 4), nullable=False)
    open_positions = Column(Integer, nullable=False, default=0)
    total_pnl = Column(Numeric(14, 4), nullable=False, default=0.0)
    total_bets = Column(Integer, nullable=False, default=0)
    wins = Column(Integer, nullable=False, default=0)
    losses = Column(Integer, nullable=False, default=0)
    snapshot_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
