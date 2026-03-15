"""
Stock Smart Money Agent — dark pool signals, unusual options, block trades.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class StockSmartMoneyAgent(BaseAgent):
    """Smart money flow analysis for stocks."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.SENTIMENT

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Smart Money analyst at a stock hedge fund.\n"
            "You detect institutional positioning through options flow and volume patterns.\n\n"
            "WHAT YOU LOOK FOR:\n"
            "- Unusual options volume (>5x open interest) = someone knows something\n"
            "- Heavy call buying on low IV = bullish institutional positioning\n"
            "- Heavy put buying on a rising stock = smart money hedging/exit\n"
            "- Volume spikes without news = pre-positioning\n"
            "- Insider buying (Form 4) = strongest bullish signal\n\n"
            "CONVICTION:\n"
            "- 9-10: Multiple smart money signals aligned (insider buying + unusual calls)\n"
            "- 7-8: Clear institutional positioning in one direction\n"
            "- 5-6: Some unusual activity but ambiguous\n"
            "- 3-4: Normal institutional flow\n"
            "- 1-2: No detectable smart money activity\n\n"
            "Reference specific data. 2 sentences."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        options = market_data.get("options", {})
        stats = market_data.get("stats", {})
        indicators = market_data.get("indicators")

        prompt = f"Analyze smart money flow for {self.profile.symbol}.\n\n"

        if options:
            prompt += "=== OPTIONS FLOW ===\n"
            if options.get("put_call_ratio"):
                prompt += f"Put/Call Ratio: {options['put_call_ratio']:.2f}\n"
            if options.get("unusual_activity"):
                prompt += "⚠ UNUSUAL OPTIONS ACTIVITY DETECTED\n"

        if stats:
            vol = stats.get("volume", 0)
            prompt += f"\nVolume: {vol:,.0f}\n"
            prompt += f"Price: ${stats.get('close', 0):,.2f} ({stats.get('price_change_pct', 0):+.2f}%)\n"

        if indicators and indicators.volume_ratio:
            prompt += f"Volume vs 20d avg: {indicators.volume_ratio:.2f}x\n"

        prompt += "\nAssess smart money positioning."
        return prompt
