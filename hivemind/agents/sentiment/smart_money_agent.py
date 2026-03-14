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
            # Funding rate
            prompt += f"Funding: {smart_money.get('funding_sentiment', 'N/A')} ({smart_money.get('funding_rate_pct', 0):+.4f}%)\n"

            # Top trader positioning
            if "top_trader_ratio" in smart_money:
                prompt += f"Top Traders: {smart_money['top_trader_long_pct']:.0f}% long (ratio {smart_money['top_trader_ratio']:.3f}) — {smart_money.get('top_trader_signal', '')}\n"

            # Taker flow
            if "taker_buy_sell_ratio" in smart_money:
                prompt += f"Taker Flow: {smart_money['taker_buy_sell_ratio']:.3f} — {smart_money.get('taker_signal', '')}\n"

            # Divergence (only meaningful at extremes now)
            divergence = smart_money.get("divergence")
            if divergence and divergence not in ("ALIGNED", None):
                mag = smart_money.get("divergence_magnitude", 0)
                prompt += f"Smart Money Divergence: {divergence} (magnitude: {mag:.3f})\n"
            elif divergence == "ALIGNED":
                prompt += f"Smart Money vs Retail: ALIGNED (no divergence)\n"
        else:
            base = self.profile.symbol.replace("USDT", "")
            prompt += f"No derivatives data for {base} (no Binance futures). Give conviction 1-2.\n"

        prompt += "\nPredict smart money direction."
        return prompt
