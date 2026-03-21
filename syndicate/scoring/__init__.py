"""
Quantitative Scoring Engine — Layer 1 of the two-layer signal architecture.

Pure math, zero LLM calls. Produces deterministic scores from market data
that form the PRIMARY trading signals. LLM agents provide interpretation
and narrative (Layer 2) on top of these scores.

Scoring domains:
- Technical: RSI, MACD, SMA alignment, Bollinger, volume, Donchian, ADX
- Sentiment: F&G extremes, funding rate extremes, per-coin CFGI
- Macro: BTC dominance, market cap momentum, composite
- On-Chain: Exchange flows, DeFi TVL, whale accumulation
- Fundamental: FDV/MCap, supply dynamics
"""

from syndicate.scoring.models import QuantScore, ScoreComponent
from syndicate.scoring.engine import QuantScoringEngine

__all__ = ["QuantScoringEngine", "QuantScore", "ScoreComponent"]
