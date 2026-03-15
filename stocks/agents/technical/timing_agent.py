"""
Stock Technical Timing Agent — analyzes the HOURLY (1H) timeframe.
Screen 3 of Elder's Triple Screen: THE RIPPLE.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class StockTimingAgent(BaseAgent):
    """Hourly entry timing for stocks. Market hours candles only."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.TECHNICAL

    @property
    def system_prompt(self) -> str:
        return (
            "You are the TIMING analyst on a stock trading desk. "
            "You read the HOURLY (1H) chart to time entries precisely.\n\n"
            "STOCK-SPECIFIC:\n"
            "- Stocks trade 9:30-16:00 ET — no overnight candles.\n"
            "- First 30 min and last 30 min have highest volume.\n"
            "- Hourly RSI extremes (<20 or >80) are sharper reversal signals in stocks.\n"
            "- ATR on hourly gives precise stop-loss distances.\n\n"
            "CONVICTION:\n"
            "- 9-10: Perfect entry zone — support/resistance + RSI extreme + volume.\n"
            "- 7-8: Good entry, most hourly signals aligned.\n"
            "- 5-6: Entry possible but timing not ideal.\n"
            "- 3-4: Bad timing — wait for better entry.\n"
            "- 1-2: No clear entry point.\n\n"
            "RULES:\n"
            "- Your role is TIMING only — trust the higher timeframes for direction.\n"
            "- Reference specific indicator values. 2 sentences."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        indicators_1h = market_data.get("indicators_1h")
        indicators = market_data.get("indicators")
        stats = market_data.get("stats", {})
        price_history = market_data.get("price_history", "")

        prompt = f"Time the entry for {self.profile.symbol}.\n\n"

        if indicators_1h:
            prompt += f"=== HOURLY INDICATORS ===\n{indicators_1h.to_summary()}\n"
        elif indicators:
            prompt += f"=== DAILY INDICATORS (no hourly) ===\n{indicators.to_summary()}\n"

        if price_history:
            prompt += f"\n=== RECENT PRICE ACTION ===\n{price_history}\n"

        if stats:
            prompt += f"\nCurrent: ${stats.get('close', 0):,.2f} | Range: ${stats.get('low', 0):,.2f}-${stats.get('high', 0):,.2f}\n"

        prompt += "\nTime the optimal entry."
        return prompt
