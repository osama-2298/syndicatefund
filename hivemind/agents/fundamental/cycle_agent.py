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
            "You assess MARKET CYCLE POSITION: where is this asset in the accumulation → "
            "markup → distribution → markdown cycle?\n\n"
            "You MUST pick BULLISH or BEARISH.\n\n"
            "CYCLE RULES:\n"
            "- Price well below SMA200 + declining volume = ACCUMULATION (bullish)\n"
            "- Price above SMA200 + rising MAs aligned = MARKUP (bullish)\n"
            "- Price far above SMA200 + volume climax = DISTRIBUTION (bearish)\n"
            "- Price below SMA200 + declining MAs = MARKDOWN (bearish)\n"
            "- Institutional volume (high volume + direction) confirms the cycle phase\n\n"
            "CONVICTION: 9-10 clear cycle phase. 5-6 transition. 1-2 unclear.\n"
            "RULES: Reference SMA200 position and volume. 2 sentences."
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
