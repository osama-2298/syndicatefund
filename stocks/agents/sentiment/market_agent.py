"""
Stock Market Sentiment Agent — VIX, CNN F&G, put/call ratio, market breadth.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class StockMarketSentimentAgent(BaseAgent):
    """Market-level sentiment via VIX, fear indicators, breadth."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.SENTIMENT

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Market Sentiment analyst at a stock hedge fund.\n"
            "You interpret VIX, CNN Fear & Greed, put/call ratios, and market breadth.\n\n"
            "VIX GUIDE:\n"
            "- VIX < 15: Extreme complacency → CAUTION (often precedes corrections)\n"
            "- VIX 15-20: Normal → NEUTRAL\n"
            "- VIX 20-25: Elevated fear → SLIGHTLY BULLISH (contrarian)\n"
            "- VIX 25-35: High fear → BULLISH (buying opportunity likely)\n"
            "- VIX > 35: Panic → VERY BULLISH but wait for stabilization\n\n"
            "CNN FEAR & GREED:\n"
            "- 0-25: Extreme Fear → contrarian bullish\n"
            "- 25-45: Fear → moderately bullish\n"
            "- 45-55: Neutral\n"
            "- 55-75: Greed → cautious\n"
            "- 75-100: Extreme Greed → contrarian bearish\n\n"
            "PUT/CALL RATIO:\n"
            "- > 1.2: Excessive hedging → contrarian bullish\n"
            "- 0.7-1.0: Normal\n"
            "- < 0.5: Extreme complacency → bearish signal\n\n"
            "Reference specific values. 2 sentences."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        indices = market_data.get("indices", {})
        cnn_fg = market_data.get("cnn_fear_greed", {})
        options = market_data.get("options", {})
        stats = market_data.get("stats", {})

        prompt = f"Analyze market sentiment for {self.profile.symbol}.\n\n"

        if indices:
            prompt += "=== MARKET INDICES ===\n"
            if indices.get("vix"):
                prompt += f"VIX: {indices['vix']:.1f}\n"
            if indices.get("spy_change") is not None:
                prompt += f"SPY: {indices['spy_change']:+.2f}%\n"
            if indices.get("advance_decline"):
                prompt += f"Advance/Decline: {indices['advance_decline']:.2f}\n"

        if cnn_fg:
            prompt += f"\nCNN Fear & Greed: {cnn_fg.get('current_value', '?')}/100 ({cnn_fg.get('current_label', '?')})\n"

        if options:
            if options.get("put_call_ratio"):
                prompt += f"\nStock P/C Ratio: {options['put_call_ratio']:.2f}\n"
            if options.get("unusual_activity"):
                prompt += "UNUSUAL OPTIONS ACTIVITY DETECTED\n"

        if stats:
            prompt += f"\n{self.profile.symbol}: ${stats.get('close', 0):,.2f} ({stats.get('price_change_pct', 0):+.2f}%)\n"

        prompt += "\nAnalyze the overall market sentiment."
        return prompt
