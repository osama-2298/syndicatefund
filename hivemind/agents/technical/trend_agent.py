"""
Technical Trend Agent — analyzes the DAILY (1D) timeframe.
Answers: "Is the higher-timeframe trend bullish or bearish?"

This is Screen 1 of Elder's Triple Screen: THE TIDE.
It sets the directional bias. Lower timeframes should not contradict this
unless they have very strong evidence.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType, TechnicalIndicators
from hivemind.agents.technical.technical_agent import compute_technical_scores


class TechnicalTrendAgent(BaseAgent):
    """Daily (1D) trend analysis — the strategic direction."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.TECHNICAL

    @property
    def system_prompt(self) -> str:
        return (
            "You are the TREND analyst on a technical trading desk. "
            "You read the DAILY (1D) chart — the big picture.\n\n"
            "Your job: determine the STRATEGIC DIRECTION. Is the multi-day trend bullish or bearish?\n"
            "You MUST pick BULLISH or BEARISH. No neutral option.\n\n"
            "WHAT YOU LOOK FOR:\n"
            "- SMA 50/200 alignment (golden cross vs death cross)\n"
            "- Price position relative to SMA200 (above = bull, below = bear)\n"
            "- Daily RSI trend (sustained above 50 = bull, below 50 = bear)\n"
            "- Daily MACD direction (above signal line = bull)\n\n"
            "CONVICTION:\n"
            "- 9-10: All daily MAs aligned, RSI confirms, MACD confirms. Textbook trend.\n"
            "- 7-8: Most signals agree. Clear trend with minor noise.\n"
            "- 5-6: Trend visible but weakening or transitioning.\n"
            "- 3-4: Mixed daily signals. Trend is unclear.\n"
            "- 1-2: Daily chart is pure chop. Pick whichever side the SMA200 favors.\n\n"
            "RULES:\n"
            "- You set the STRATEGIC BIAS. Your opinion carries the most weight on the team.\n"
            "- Reference specific indicator values. Keep reasoning to 2 sentences.\n"
            "- A clear daily trend overrides any short-term noise."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        indicators_1d = market_data.get("indicators_1d")
        if indicators_1d is None:
            indicators_1d = market_data.get("indicators")  # fallback to primary
        stats = market_data.get("stats_24h", {})

        if indicators_1d is None:
            return f"No daily indicators available for {self.profile.symbol}. Pick based on 24h price change: {stats.get('price_change_pct', 0):+.2f}%"

        scores = compute_technical_scores(indicators_1d, stats)

        return (
            f"Predict the trend direction for {self.profile.symbol} on the DAILY (1D) chart.\n\n"
            f"=== DAILY TECHNICAL SCORES ===\n"
            f"COMPOSITE: {scores['composite_score']:+.3f} ({scores['composite_label']})\n"
            f"Trend: {scores['trend_score']:+.3f} ({scores.get('trend_label', 'N/A')})\n"
            f"Momentum: {scores['momentum_score']:+.3f} ({scores.get('momentum_label', 'N/A')})\n"
            f"Volume: {scores['volume_score']:+.3f}\n"
            + (f"MA Alignment: {scores.get('ma_alignment', 'N/A')}\n" if 'ma_alignment' in scores else "")
            + (f"RSI(14): {scores['rsi']:.1f} [{scores.get('rsi_zone', '')}]\n" if 'rsi' in scores else "")
            + (f"MACD: {scores.get('macd_crossover', 'N/A')}\n" if 'macd_crossover' in scores else "")
            + f"\nPredict the daily trend direction."
        )
