"""
Core data models for the Hivemind system.

Every piece of data that flows through the pipeline has a strict schema.
No dicts-of-dicts, no guessing — if it moves through the system, it's typed here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

import uuid

from pydantic import BaseModel, Field


def _new_id() -> str:
    """Generate a unique ID. Using uuid4 for simplicity and zero external deps."""
    return str(uuid.uuid4())


# ═══════════════════════════════════════════
#  Enums
# ═══════════════════════════════════════════


class SignalAction(str, Enum):
    """Possible trading actions an agent can recommend."""

    BUY = "BUY"
    SELL = "SELL"
    SHORT = "SHORT"
    HOLD = "HOLD"
    COVER = "COVER"


class TeamType(str, Enum):
    """Specialized analysis teams."""

    SENTIMENT = "sentiment"
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    MACRO = "macro"
    ONCHAIN = "onchain"
    EXECUTIVE = "executive"


class AgentStatus(str, Enum):
    """Lifecycle status of an agent."""

    ACTIVE = "active"
    FIRED = "fired"
    PROMOTED = "promoted"
    IDLE = "idle"


class MarketRegime(str, Enum):
    """Market regime as classified by the CEO agent."""

    BULL = "bull"
    BEAR = "bear"
    RANGING = "ranging"
    CRISIS = "crisis"


class OrderSide(str, Enum):
    """Trade execution side."""

    BUY = "BUY"
    SELL = "SELL"


# ═══════════════════════════════════════════
#  Market Data
# ═══════════════════════════════════════════


class Candle(BaseModel):
    """Single OHLCV candlestick."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)

    @property
    def range(self) -> float:
        return self.high - self.low


class TickerPrice(BaseModel):
    """Current price snapshot for a symbol."""

    symbol: str
    price: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TechnicalIndicators(BaseModel):
    """Computed technical indicators for a symbol at a point in time."""

    symbol: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Trend
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    ema_12: float | None = None
    ema_26: float | None = None

    # Momentum
    rsi_14: float | None = None
    macd_line: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None

    # Volatility
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    bb_width: float | None = None
    atr_14: float | None = None

    # Volume
    volume_sma_20: float | None = None
    current_volume: float | None = None
    volume_ratio: float | None = None  # current / avg

    def to_summary(self) -> str:
        """Human-readable summary for LLM consumption."""
        lines = [f"Technical Indicators for {self.symbol}:"]

        if self.rsi_14 is not None:
            zone = "OVERSOLD" if self.rsi_14 < 30 else "OVERBOUGHT" if self.rsi_14 > 70 else "NEUTRAL"
            lines.append(f"  RSI(14): {self.rsi_14:.1f} [{zone}]")

        if self.macd_line is not None and self.macd_signal is not None:
            cross = "BULLISH" if self.macd_line > self.macd_signal else "BEARISH"
            lines.append(
                f"  MACD: Line={self.macd_line:.4f}, Signal={self.macd_signal:.4f}, "
                f"Hist={self.macd_histogram:.4f} [{cross}]"
            )

        if self.bb_upper is not None:
            lines.append(
                f"  Bollinger Bands: Upper={self.bb_upper:.2f}, "
                f"Mid={self.bb_middle:.2f}, Lower={self.bb_lower:.2f}, "
                f"Width={self.bb_width:.4f}"
            )

        if self.sma_20 is not None:
            lines.append(f"  SMA(20): {self.sma_20:.2f}")
        if self.sma_50 is not None:
            lines.append(f"  SMA(50): {self.sma_50:.2f}")
        if self.sma_200 is not None:
            lines.append(f"  SMA(200): {self.sma_200:.2f}")
        if self.ema_12 is not None:
            lines.append(f"  EMA(12): {self.ema_12:.2f}, EMA(26): {self.ema_26:.2f}")

        if self.atr_14 is not None:
            lines.append(f"  ATR(14): {self.atr_14:.4f}")

        if self.volume_ratio is not None:
            vol_desc = "ABOVE AVG" if self.volume_ratio > 1.2 else "BELOW AVG" if self.volume_ratio < 0.8 else "NORMAL"
            lines.append(f"  Volume Ratio: {self.volume_ratio:.2f}x avg [{vol_desc}]")

        return "\n".join(lines)


# ═══════════════════════════════════════════
#  Agent & Signal
# ═══════════════════════════════════════════


class Signal(BaseModel):
    """
    A trading signal produced by a single agent.
    This is the fundamental unit of output in the Hivemind system.
    """

    id: str = Field(default_factory=lambda: _new_id())
    agent_id: str
    team: TeamType
    symbol: str  # e.g. "BTCUSDT"
    action: SignalAction
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def __str__(self) -> str:
        return (
            f"[{self.team.value.upper()}] {self.symbol} → {self.action.value} "
            f"(confidence: {self.confidence:.0%}) | {self.reasoning[:80]}"
        )


class AggregatedSignal(BaseModel):
    """
    The output of the Signal Aggregator — a weighted consensus for one symbol.
    """

    symbol: str
    recommended_action: SignalAction
    aggregated_confidence: float = Field(ge=0.0, le=1.0)
    contributing_signals: list[Signal]
    consensus_ratio: float  # what % of signals agree with the recommended action
    weighted_scores: dict[str, float]  # action -> weighted score
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __str__(self) -> str:
        return (
            f"{self.symbol} → {self.recommended_action.value} "
            f"(confidence: {self.aggregated_confidence:.0%}, "
            f"consensus: {self.consensus_ratio:.0%}, "
            f"signals: {len(self.contributing_signals)})"
        )


class AgentProfile(BaseModel):
    """
    An agent's identity and track record.
    This is what the COO creates when assigning a new agent.
    """

    agent_id: str = Field(default_factory=lambda: _new_id())
    team: TeamType
    symbol: str  # assigned coin
    model: str = "claude-opus-4-6"
    provider: str = "anthropic"
    status: AgentStatus = AgentStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Track record
    total_signals: int = 0
    correct_signals: int = 0
    total_pnl: float = 0.0  # cumulative P&L from this agent's signals

    @property
    def accuracy(self) -> float:
        """Win rate: fraction of signals that were correct."""
        if self.total_signals == 0:
            return 0.0
        return self.correct_signals / self.total_signals

    @property
    def weight(self) -> float:
        """
        Weight used in the Signal Aggregator.
        New agents start with a base weight. Weight grows with accuracy and volume.
        Minimum 10 signals before track record affects weight.
        """
        base_weight = 0.5
        if self.total_signals < 10:
            return base_weight
        # Weight scales from 0.1 (terrible) to 1.0 (excellent)
        # accuracy=0.5 → weight≈0.5, accuracy=0.7 → weight≈0.8
        return max(0.1, min(1.0, base_weight + (self.accuracy - 0.5) * 2))


# ═══════════════════════════════════════════
#  Risk & Portfolio
# ═══════════════════════════════════════════


class RiskLimits(BaseModel):
    """Rules set by the CRO agent. The Risk Manager enforces these."""

    max_position_pct: float = 0.05  # max 5% of portfolio per position
    max_sector_pct: float = 0.20  # max 20% in any one sector
    max_daily_drawdown_pct: float = 0.03  # halt if portfolio drops 3% in a day
    max_open_positions: int = 20
    min_signal_confidence: float = 0.6  # ignore signals below this confidence
    min_consensus_ratio: float = 0.5  # at least 50% of teams must agree


class Position(BaseModel):
    """A single open position in the portfolio."""

    symbol: str
    side: OrderSide
    entry_price: float
    quantity: float
    entry_time: datetime
    current_price: float = 0.0

    @property
    def notional_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        if self.side == OrderSide.BUY:
            return (self.current_price - self.entry_price) * self.quantity
        else:  # SHORT
            return (self.entry_price - self.current_price) * self.quantity

    @property
    def pnl_pct(self) -> float:
        if self.entry_price == 0:
            return 0.0
        if self.side == OrderSide.BUY:
            return (self.current_price - self.entry_price) / self.entry_price
        else:
            return (self.entry_price - self.current_price) / self.entry_price


class PortfolioState(BaseModel):
    """Snapshot of the current portfolio."""

    cash: float = 100_000.0  # starting capital for paper trading
    positions: list[Position] = Field(default_factory=list)
    total_realized_pnl: float = 0.0
    peak_value: float = 100_000.0  # for drawdown calculation
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_position_value(self) -> float:
        return sum(p.notional_value for p in self.positions)

    @property
    def total_value(self) -> float:
        return self.cash + self.total_position_value

    @property
    def total_unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self.positions)

    @property
    def drawdown_pct(self) -> float:
        if self.peak_value == 0:
            return 0.0
        return (self.peak_value - self.total_value) / self.peak_value

    def get_position(self, symbol: str) -> Position | None:
        for p in self.positions:
            if p.symbol == symbol:
                return p
        return None

    def position_weight(self, symbol: str) -> float:
        """What fraction of total portfolio value is this position."""
        pos = self.get_position(symbol)
        if pos is None or self.total_value == 0:
            return 0.0
        return pos.notional_value / self.total_value


class TradeParameters(BaseModel):
    """
    Risk parameters for every trade — calculated BEFORE entry.
    Based on ATR-based stops, R-multiple targets, and Chandelier trailing.
    """

    # Stop loss
    stop_loss_price: float = 0.0
    stop_loss_pct: float = 0.0  # distance from entry as %
    stop_atr_multiplier: float = 2.5  # how many ATRs below entry

    # Take profit targets (tiered)
    take_profit_1: float = 0.0  # sell 33% here
    take_profit_2: float = 0.0  # sell 33% here
    # remaining 34% trails

    # R-value (1R = distance from entry to stop)
    r_value: float = 0.0  # in dollars

    # Trailing stop
    trailing_stop_activation: float = 0.0  # price at which trailing starts
    trailing_stop_distance: float = 0.0  # ATR-based distance
    trailing_atr_multiplier: float = 3.0

    # Time stop
    max_holding_hours: int = 240  # default 10 days
    entry_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Risk amount
    risk_amount_usd: float = 0.0  # max loss if stop hit
    risk_pct_of_portfolio: float = 0.0  # what % of portfolio is at risk

    # Asset classification (affects parameters)
    asset_tier: str = "mid_cap"  # btc, top5, large_cap, mid_cap, meme


class TradeOrder(BaseModel):
    """A concrete trade instruction ready for execution, with full risk parameters."""

    id: str = Field(default_factory=lambda: _new_id())
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    source_signal_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Trade management parameters
    params: TradeParameters = Field(default_factory=TradeParameters)

    @property
    def notional_value(self) -> float:
        return self.quantity * self.price

    def __str__(self) -> str:
        sl_str = f" SL=${self.params.stop_loss_price:,.2f}" if self.params.stop_loss_price > 0 else ""
        tp_str = f" TP=${self.params.take_profit_1:,.2f}" if self.params.take_profit_1 > 0 else ""
        return (
            f"{self.side.value} {self.quantity:.6f} {self.symbol} "
            f"@ ${self.price:,.2f} (${self.notional_value:,.2f}){sl_str}{tp_str}"
        )


# ═══════════════════════════════════════════
#  Executive Layer
# ═══════════════════════════════════════════


class RegimeClassification(BaseModel):
    """Legacy — kept for backward compat. Use StrategicDirective instead."""

    regime: MarketRegime
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    risk_multiplier: float = Field(ge=0.0, le=2.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StrategicDirective(BaseModel):
    """
    Output of the CEO agent — the top-level strategic mandate for the cycle.

    The CEO sees EVERYTHING (regime, intelligence, portfolio, performance)
    and outputs directives that flow down to every other layer:
    - regime + risk_multiplier → CRO uses this to set risk rules
    - sector_weights → PM layer uses this for allocation
    - focus_strategy → COO uses this for coin selection
    - emergency_halt → stops all trading immediately
    """

    # Market regime
    regime: MarketRegime
    regime_confidence: float = Field(ge=0.0, le=1.0)
    risk_multiplier: float = Field(ge=0.0, le=2.0)

    # Sector allocation — tells PM layer where to concentrate/avoid
    # Values are relative weights (higher = overweight, lower = underweight)
    sector_weights: dict[str, float] = Field(default_factory=dict)
    # e.g. {"L1s": 1.2, "DeFi": 1.5, "Memes": 0.3, "L2s": 1.0}

    # Strategic focus — tells COO what to prioritize
    focus_strategy: str = ""
    # e.g. "Hunt high-cap DeFi momentum" or "Defensive — large caps only"

    # Emergency controls
    emergency_halt: bool = False
    halt_reason: str = ""

    # Reasoning
    reasoning: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CoinScore(BaseModel):
    """Scoring of a single coin by the COO for selection."""

    symbol: str
    volume_score: float = Field(ge=0.0, le=1.0)
    volatility_score: float = Field(ge=0.0, le=1.0)
    momentum_score: float = Field(ge=-1.0, le=1.0)
    composite_score: float = 0.0


class CoinSelection(BaseModel):
    """Output of the COO agent — which coins to analyze this cycle."""

    selected_coins: list[str]
    scores: list[CoinScore]
    reasoning: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TeamSignal(BaseModel):
    """
    Synthesized output from a Team Manager.
    One per team per coin. Replaces individual agent signals in the aggregator.
    The manager reads all its agents' signals and produces this synthesis.
    """

    id: str = Field(default_factory=lambda: _new_id())
    team: TeamType
    symbol: str
    direction: str  # "BULLISH" or "BEARISH"
    conviction: int = Field(ge=1, le=10)
    action: SignalAction  # Derived from direction + conviction
    confidence: float = Field(ge=0.0, le=1.0)  # conviction / 10

    # Synthesis metadata
    agreement_level: float = Field(ge=0.0, le=1.0)  # How much agents agreed
    dissent_summary: str = ""  # What the minority thinks
    key_factors: list[str] = Field(default_factory=list)  # Top 3 reasons

    # Team-specific
    timeframe_alignment: str = ""  # Technical: FULLY_ALIGNED / MOSTLY_ALIGNED / CONFLICTING
    manager_reasoning: str = ""

    # Traceability
    contributing_signals: list[Signal] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_signal(self) -> Signal:
        """Convert to a Signal for backward compatibility with the aggregator."""
        return Signal(
            agent_id=f"manager_{self.team.value}",
            team=self.team,
            symbol=self.symbol,
            action=self.action,
            confidence=self.confidence,
            reasoning=self.manager_reasoning,
            metadata={
                "direction": self.direction,
                "conviction": self.conviction,
                "agreement_level": self.agreement_level,
                "dissent_summary": self.dissent_summary,
                "key_factors": self.key_factors,
                "timeframe_alignment": self.timeframe_alignment,
                "is_team_signal": True,
                "num_contributing_agents": len(self.contributing_signals),
            },
        )

    def __str__(self) -> str:
        agree = f"{self.agreement_level:.0%}"
        return (
            f"[{self.team.value.upper()} TEAM] {self.symbol} → {self.direction} "
            f"(conviction: {self.conviction}/10, agreement: {agree})"
        )


class SignalRecord(BaseModel):
    """Persisted signal for performance tracking across runs."""

    signal_id: str
    agent_id: str
    symbol: str
    team: TeamType
    action: SignalAction
    confidence: float
    price_at_signal: float
    timestamp: datetime
    outcome: str = "PENDING"  # CORRECT / INCORRECT / PENDING
    price_at_evaluation: float | None = None
    pnl_pct: float | None = None


class TradeResult(BaseModel):
    """Outcome of an executed trade."""

    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    executed_price: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_paper: bool = True

    @property
    def notional_value(self) -> float:
        return self.quantity * self.executed_price
