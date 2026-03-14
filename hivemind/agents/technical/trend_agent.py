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
            "You are the TREND analyst. You read the DAILY (1D) chart — the big picture.\n"
            "You MUST pick BULLISH or BEARISH. Conviction 0 only if data is truly unavailable.\n\n"
            "QUANTITATIVE DECISION RULES:\n"
            "- If SMA20 > SMA50 > SMA200 (golden stack) AND RSI > 50 → BULLISH conviction 8-9\n"
            "- If price > SMA200 AND RSI > 50 but MAs not fully aligned → BULLISH conviction 6-7\n"
            "- If price > SMA200 but RSI < 50 (divergence) → BULLISH conviction 4-5\n"
            "- If price < SMA200 but RSI > 50 → BEARISH conviction 4-5\n"
            "- If price < SMA200 AND RSI < 50 → BEARISH conviction 6-7\n"
            "- If SMA20 < SMA50 < SMA200 (death stack) AND RSI < 50 → BEARISH conviction 8-9\n"
            "- If composite_score > 0.3 → add +1 conviction to whatever the above gives\n"
            "- If composite_score < -0.3 → subtract 1 conviction\n"
            "- Conviction 10: ALL of golden stack + RSI > 60 + MACD bullish + composite > 0.5\n\n"
            "RULES: Reference specific values (RSI=X, SMA200=$Y). 2 sentences max."
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
