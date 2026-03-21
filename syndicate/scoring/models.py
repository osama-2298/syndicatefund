"""Pydantic models for the Quantitative Scoring Engine."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ScoreComponent(BaseModel):
    """A single scoring factor with its value and contribution."""

    name: str
    value: float = 0.0
    weight: float = 1.0
    reason: str = ""

    @property
    def weighted_value(self) -> float:
        return self.value * self.weight


class QuantScore(BaseModel):
    """
    Complete quantitative score for a single symbol.

    This is the primary signal that drives trading decisions.
    LLM interpretation (Layer 2) can modify this score but
    cannot override it without justification.
    """

    symbol: str

    # Domain scores (each -10 to +10)
    technical_score: float = 0.0
    sentiment_score: float = 0.0
    macro_score: float = 0.0
    onchain_score: float = 0.0
    fundamental_score: float = 0.0

    # Composite (weighted combination)
    composite_score: float = 0.0

    # Individual factor breakdown for transparency
    components: dict[str, float] = Field(default_factory=dict)

    # Derived trading signal
    action: str = "HOLD"  # BUY, SELL, HOLD
    confidence: float = 0.0  # 0.0 to 1.0
    regime: str = "unknown"

    # Metadata
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "technical_score": round(self.technical_score, 3),
            "sentiment_score": round(self.sentiment_score, 3),
            "macro_score": round(self.macro_score, 3),
            "onchain_score": round(self.onchain_score, 3),
            "fundamental_score": round(self.fundamental_score, 3),
            "composite_score": round(self.composite_score, 3),
            "components": {k: round(v, 3) for k, v in self.components.items()},
            "action": self.action,
            "confidence": round(self.confidence, 4),
            "regime": self.regime,
            "timestamp": self.timestamp.isoformat(),
        }
