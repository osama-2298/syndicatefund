"""
Technical Timing Agent — analyzes the HOURLY (1H) timeframe.
Answers: "Is the timing right to enter NOW?"

This is Screen 3 of Elder's Triple Screen: THE RIPPLE.
It times the exact entry within the setup identified by the 4H agent.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType, TechnicalIndicators
from hivemind.agents.technical.technical_agent import compute_technical_scores


class TechnicalTimingAgent(BaseAgent):
    """Hourly (1H) timing analysis — entry precision."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.TECHNICAL

    @property
    def system_prompt(self) -> str:
        return (
            "You are the TIMING analyst. You read the HOURLY (1H) chart — entry precision.\n"
            "You MUST pick BULLISH or BEARISH. Conviction 0 only if data unavailable.\n\n"
            "QUANTITATIVE DECISION RULES:\n"
            "- If EMA12 > EMA26 AND RSI > 50 AND composite > 0 → BULLISH conviction 6-7\n"
            "- If EMA12 > EMA26 but RSI < 50 (divergence) → BULLISH conviction 3-4\n"
            "- If EMA12 < EMA26 AND RSI < 50 AND composite < 0 → BEARISH conviction 6-7\n"
            "- If EMA12 < EMA26 but RSI > 50 → BEARISH conviction 3-4\n"
            "- If composite > 0.3 AND momentum_score > 0.2 → conviction 7-8\n"
            "- If composite < -0.3 AND momentum_score < -0.2 → conviction 7-8 BEARISH\n\n"
            "EXPECTATIONS:\n"
            "- Your conviction is naturally LOWER than other agents (3-6 is normal).\n"
            "- Short-term signals change fast. This is fine.\n"
            "- Conviction 7+ requires CLEAR 1H momentum confirmation.\n\n"
            "RULES: Reference RSI value and EMA cross direction. 2 sentences max."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        indicators_1h = market_data.get("indicators_1h")
        stats = market_data.get("stats_24h", {})

        if indicators_1h is None:
            return f"No 1H indicators for {self.profile.symbol}. Pick based on 24h momentum."

        scores = compute_technical_scores(indicators_1h, stats)

        prompt = (
            f"Predict the short-term (1H) momentum for {self.profile.symbol}.\n\n"
            f"=== 1H TECHNICAL SCORES ===\n"
            f"COMPOSITE: {scores['composite_score']:+.3f} ({scores['composite_label']})\n"
            f"Trend: {scores['trend_score']:+.3f} | Momentum: {scores['momentum_score']:+.3f}\n"
        )
        if "rsi" in scores:
            prompt += f"RSI(14): {scores['rsi']:.1f} [{scores.get('rsi_zone', '')}]\n"
        if "macd_crossover" in scores:
            prompt += f"MACD: {scores['macd_crossover']}\n"

        prompt += f"\nPredict short-term direction."
        return prompt
