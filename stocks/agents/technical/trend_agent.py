"""
Stock Technical Trend Agent — analyzes the DAILY (1D) timeframe.
Screen 1 of Elder's Triple Screen: THE TIDE.

Adjusted for stocks: SMA200 respected more strictly, RSI 70/30 classic thresholds.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class StockTrendAgent(BaseAgent):
    """Daily (1D) trend analysis for stocks."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.TECHNICAL

    @property
    def system_prompt(self) -> str:
        return (
            "You are the TREND analyst on a stock trading desk. "
            "You read the DAILY (1D) chart — the big picture.\n\n"
            "You also receive a US MACRO DIGEST as background context.\n\n"
            "STOCK-SPECIFIC RULES:\n"
            "- Stocks respect SMA200 MORE strictly than crypto. Price above SMA200 = bull bias.\n"
            "- RSI 70/30 are standard overbought/oversold for stocks.\n"
            "- Golden cross (SMA50 > SMA200) is a strong bullish signal for equities.\n"
            "- Death cross (SMA50 < SMA200) is a strong bearish signal.\n"
            "- Volume confirmation matters more in stocks — institutional buying shows in volume.\n\n"
            "CONVICTION:\n"
            "- 9-10: All daily MAs aligned, RSI confirms, volume confirms. Textbook trend.\n"
            "- 7-8: Most signals agree. Clear trend with minor noise.\n"
            "- 5-6: Trend visible but weakening or transitioning.\n"
            "- 3-4: Mixed daily signals. Trend is unclear.\n"
            "- 1-2: Daily chart is pure chop.\n\n"
            "RULES:\n"
            "- Reference specific indicator values. Keep reasoning to 2 sentences.\n"
            "- You MUST pick BULLISH or BEARISH.\n"
            "- A clear daily trend overrides any short-term noise."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        indicators = market_data.get("indicators")
        stats = market_data.get("stats", {})
        us_macro = market_data.get("us_macro_digest", {})

        if indicators is None:
            return f"No daily indicators for {self.profile.symbol}. Price change: {stats.get('price_change_pct', 0):+.2f}%"

        prompt = f"Predict the trend direction for {self.profile.symbol} on the DAILY chart.\n\n"
        prompt += f"=== DAILY INDICATORS ===\n{indicators.to_summary()}\n"

        if stats:
            prompt += f"\n24h: {stats.get('price_change_pct', 0):+.2f}% | Vol: {stats.get('volume', 0):,.0f}\n"

        if us_macro:
            prompt += f"\n=== US MACRO (context) ===\n"
            prompt += f"Net Bias: {us_macro.get('net_bias', '?')} · Inflation: {us_macro.get('inflation_trend', '?')}\n"

        prompt += "\nPredict the daily trend direction."
        return prompt
