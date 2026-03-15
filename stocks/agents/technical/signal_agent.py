"""
Stock Technical Signal Agent — analyzes the DAILY setup from aggregated hourly data.
Screen 2 of Elder's Triple Screen: THE WAVE.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class StockSignalAgent(BaseAgent):
    """Daily setup analysis — identifies tradeable setups in stocks."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.TECHNICAL

    @property
    def system_prompt(self) -> str:
        return (
            "You are the SIGNAL analyst on a stock trading desk. "
            "You identify tradeable SETUPS using MACD, RSI divergences, and Bollinger Bands.\n\n"
            "STOCK-SPECIFIC:\n"
            "- MACD crossovers are stronger signals in stocks due to less noise.\n"
            "- Bollinger Band squeezes often precede breakouts in equities.\n"
            "- Volume spike + price breakout = institutional entry.\n"
            "- Options unusual activity can confirm a setup.\n\n"
            "CONVICTION:\n"
            "- 9-10: Clear MACD cross + RSI confirmation + volume surge. Textbook.\n"
            "- 7-8: Multiple indicators aligned, minor conflicts.\n"
            "- 5-6: Setup forming but not confirmed.\n"
            "- 3-4: Conflicting indicators, no clear setup.\n"
            "- 1-2: Nothing actionable.\n\n"
            "RULES:\n"
            "- Reference specific values. 2 sentences.\n"
            "- You MUST pick BULLISH or BEARISH."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        indicators = market_data.get("indicators")
        indicators_1h = market_data.get("indicators_1h")
        stats = market_data.get("stats", {})
        options = market_data.get("options")

        prompt = f"Identify setups for {self.profile.symbol}.\n\n"

        if indicators:
            prompt += f"=== PRIMARY INDICATORS ===\n{indicators.to_summary()}\n"

        if indicators_1h:
            prompt += f"\n=== HOURLY INDICATORS ===\n{indicators_1h.to_summary()}\n"

        if stats:
            prompt += f"\nPrice: ${stats.get('close', 0):,.2f} | Change: {stats.get('price_change_pct', 0):+.2f}%\n"

        if options:
            if options.get("put_call_ratio"):
                prompt += f"\nP/C Ratio: {options['put_call_ratio']:.2f}"
            if options.get("implied_volatility"):
                prompt += f" | IV: {options['implied_volatility']:.1%}"
            prompt += "\n"

        prompt += "\nIdentify the strongest setup."
        return prompt
