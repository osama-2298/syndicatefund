"""Smart Money Sentiment Agent — reads derivatives and institutional positioning."""

from __future__ import annotations
from typing import Any
from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class SmartMoneySentimentAgent(BaseAgent):
    @property
    def team_type(self) -> TeamType:
        return TeamType.SENTIMENT

    @property
    def system_prompt(self) -> str:
        return (
            "You read SMART MONEY positioning: funding rates, top trader long/short ratios, "
            "taker buy/sell flow, and whale vs retail divergence.\n\n"
            "Your job: predict whether INSTITUTIONAL/WHALE behavior favors HIGHER or LOWER prices.\n"
            "You MUST pick BULLISH or BEARISH.\n\n"
            "WHAT YOU LOOK FOR:\n"
            "- Funding rate: positive = longs crowded (contrarian bearish), negative = shorts crowded (contrarian bullish)\n"
            "- Top trader L/S ratio: whales long = bullish, whales short = bearish\n"
            "- Taker buy/sell: aggressive buyers > sellers = bullish\n"
            "- Smart money divergence: when whales and retail disagree, follow the whales\n\n"
            "CONVICTION: 9-10 extreme divergence. 7-8 clear positioning. 3-4 neutral. 1-2 no data.\n"
            "RULES: Smart money is the MOST reliable sentiment signal. Reference specific ratios. 2 sentences."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        smart_money = market_data.get("smart_money")
        prompt = f"Read smart money positioning for {self.profile.symbol}.\n\n"

        if smart_money:
            prompt += f"Funding: {smart_money.get('funding_sentiment', 'N/A')} ({smart_money.get('funding_rate_pct', 0):+.4f}%)\n"
            prompt += f"Divergence: {smart_money.get('divergence', 'ALIGNED')}\n"
        else:
            prompt += "No derivatives data available. Pick based on general market sentiment.\n"

        prompt += "\nPredict smart money direction."
        return prompt
