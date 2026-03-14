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
            "You read SMART MONEY: funding rates, top trader L/S ratios, taker flow, divergence.\n"
            "You MUST pick BULLISH or BEARISH. Conviction 0 if no derivatives data.\n\n"
            "QUANTITATIVE DECISION RULES:\n"
            "- Funding < -0.03% (shorts paying longs) → BULLISH conviction 7-8 (short squeeze setup)\n"
            "- Funding < -0.01% → BULLISH conviction 5-6\n"
            "- Funding -0.01% to +0.01% → neutral, use top trader ratio to decide, conviction 3-4\n"
            "- Funding > +0.01% → BEARISH conviction 5-6\n"
            "- Funding > +0.05% (longs crowded) → BEARISH conviction 7-8 (liquidation risk)\n\n"
            "TOP TRADER MODIFIERS:\n"
            "- Top traders > 60% long AND taker ratio > 1.1 → add +1 conviction BULLISH\n"
            "- Top traders > 60% short AND taker ratio < 0.9 → add +1 conviction BEARISH\n\n"
            "DIVERGENCE (if present):\n"
            "- WHALES_LONG_RETAIL_SHORT → BULLISH conviction 8+ (follow whales)\n"
            "- WHALES_SHORT_RETAIL_LONG → BEARISH conviction 8+ (follow whales)\n"
            "- MILD divergence → note it but don't override funding signal\n\n"
            "NO DATA: If no derivatives data shown, give conviction 0. Do NOT guess.\n"
            "RULES: State funding rate and top trader %. 2 sentences max."
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
