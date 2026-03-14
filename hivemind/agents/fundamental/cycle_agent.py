"""Cycle Position Agent — where is this asset in its market cycle?"""

from __future__ import annotations
from typing import Any
from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType
from hivemind.agents.fundamental.fundamental_agent import compute_fundamental_scores


class CyclePositionAgent(BaseAgent):
    @property
    def team_type(self) -> TeamType:
        return TeamType.FUNDAMENTAL

    @property
    def system_prompt(self) -> str:
        return (
            "You assess MARKET CYCLE POSITION using SMA200 and institutional volume.\n"
            "You MUST pick BULLISH or BEARISH. Conviction 0 if no indicator data.\n\n"
            "QUANTITATIVE DECISION RULES:\n"
            "- Price > SMA200 by 20%+ AND MAs aligned upward → MARKUP, BULLISH conviction 7-8\n"
            "- Price > SMA200 by 5-20% AND volume normal → EARLY MARKUP, BULLISH conviction 6-7\n"
            "- Price > SMA200 by <5% → ACCUMULATION zone, BULLISH conviction 4-5\n"
            "- Price < SMA200 by <5% → EARLY MARKDOWN, BEARISH conviction 4-5\n"
            "- Price < SMA200 by 5-20% → MARKDOWN, BEARISH conviction 6-7\n"
            "- Price < SMA200 by 20%+ AND MAs aligned downward → DEEP MARKDOWN, BEARISH conviction 7-8\n"
            "- Price > SMA200 by 50%+ → DISTRIBUTION risk, BEARISH conviction 6-7\n\n"
            "INSTITUTIONAL VOLUME MODIFIER:\n"
            "- Volume ratio > 1.5 in direction of cycle → add +1 conviction\n"
            "- Volume ratio > 1.5 AGAINST cycle direction → reduce conviction by 2\n\n"
            "RULES: State distance from SMA200 (%) and cycle phase. 2 sentences max."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        indicators = market_data.get("indicators")
        indicators_1d = market_data.get("indicators_1d")
        indicators_1w = market_data.get("indicators_1w")
        stats = market_data.get("stats_24h", {})
        coingecko = market_data.get("coingecko_coin")

        # Use daily indicators for cycle (longer term view)
        ind = indicators_1d or indicators
        if ind is None:
            return f"No indicators for {self.profile.symbol}."

        scores = compute_fundamental_scores(ind, stats, coingecko_coin=coingecko)

        prompt = f"Assess the market cycle position for {self.profile.symbol}.\n\n"
        prompt += f"Cycle Score: {scores['cycle_score']:+.3f} ({scores['cycle_label']})\n"
        if "cycle_phase" in scores:
            prompt += f"Phase: {scores['cycle_phase']}\n"
        if "pct_from_sma200" in scores:
            prompt += f"Distance from SMA200: {scores['pct_from_sma200']:+.1f}%\n"
        prompt += f"Institutional: {scores['institutional_score']:+.3f} ({scores['institutional_label']})\n"

        if indicators_1w:
            if indicators_1w.sma_50 and indicators_1w.sma_200:
                weekly_trend = "BULLISH" if indicators_1w.sma_50 > indicators_1w.sma_200 else "BEARISH"
                prompt += f"\nWeekly MA Trend: {weekly_trend}\n"

        prompt += "\nPredict cycle direction."
        return prompt
