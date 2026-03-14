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
            "You are the TIMING analyst on a technical trading desk. "
            "You read the HOURLY (1H) chart — the entry timeframe.\n\n"
            "Your job: determine if the short-term momentum supports entering NOW.\n"
            "You MUST pick BULLISH or BEARISH. No neutral option.\n\n"
            "WHAT YOU LOOK FOR:\n"
            "- 1H EMA crossovers (EMA12 vs EMA26) for short-term momentum\n"
            "- 1H RSI for immediate overbought/oversold\n"
            "- Short-term volume spikes or drying up\n"
            "- Recent price action momentum (last few candles)\n\n"
            "CONVICTION:\n"
            "- 9-10: 1H momentum strongly confirms direction. Rare.\n"
            "- 7-8: Clear short-term momentum in one direction.\n"
            "- 5-6: Momentum mixed but leaning.\n"
            "- 3-4: 1H is choppy. Barely a lean.\n"
            "- 1-2: Pure noise on the hourly.\n\n"
            "RULES:\n"
            "- You are the TIMING specialist. Your conviction will be LOWER than others — that is normal.\n"
            "- Short-term signals change fast. Low conviction is expected and fine.\n"
            "- Reference specific 1H indicators. Keep reasoning to 2 sentences."
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
