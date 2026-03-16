"""
Stock Quality Agent — ROE, margins, debt/equity, FCF yield, Piotroski F-Score.
"""

from __future__ import annotations

from typing import Any

from syndicate.agents.base import BaseAgent
from syndicate.data.models import TeamType


class StockQualityAgent(BaseAgent):
    """Business quality assessment using financial health metrics."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.FUNDAMENTAL

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Quality analyst at a stock hedge fund.\n"
            "You assess business quality — can this company sustain and grow its earnings?\n\n"
            "KEY QUALITY METRICS:\n"
            "- ROE: >15% good, >25% excellent (but check leverage)\n"
            "- ROA: >5% good, >10% excellent\n"
            "- Profit Margin: compare to industry peers\n"
            "- Operating Margin: stable/rising = pricing power\n"
            "- Debt/Equity: <0.5 conservative, 0.5-1.0 moderate, >2.0 risky\n"
            "- Current Ratio: >1.5 healthy, <1.0 liquidity risk\n"
            "- Free Cash Flow: positive and growing = fundamental strength\n"
            "- Revenue Growth: >10% growth stock, <0% declining\n\n"
            "PIOTROSKI F-SCORE (simplified):\n"
            "- Positive ROA, positive FCF, rising ROA, low debt, current ratio > 1\n"
            "- Score 7-9: Strong quality | 4-6: Average | 0-3: Weak\n\n"
            "CONVICTION:\n"
            "- 9-10: Fortress balance sheet + growing margins + strong FCF\n"
            "- 7-8: Most quality metrics favorable\n"
            "- 5-6: Average quality\n"
            "- 3-4: Quality concerns (high debt, declining margins)\n"
            "- 1-2: Serious quality red flags\n\n"
            "BULLISH = high quality business, BEARISH = deteriorating quality."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        fundamentals = market_data.get("fundamentals")
        stats = market_data.get("stats", {})

        prompt = f"Assess business quality for {self.profile.symbol}.\n\n"

        if fundamentals:
            prompt += "=== QUALITY METRICS ===\n"
            if fundamentals.roe:
                prompt += f"ROE: {fundamentals.roe:.1%}\n"
            if fundamentals.roa:
                prompt += f"ROA: {fundamentals.roa:.1%}\n"
            if fundamentals.profit_margin:
                prompt += f"Profit Margin: {fundamentals.profit_margin:.1%}\n"
            if fundamentals.operating_margin:
                prompt += f"Operating Margin: {fundamentals.operating_margin:.1%}\n"
            if fundamentals.debt_to_equity:
                prompt += f"Debt/Equity: {fundamentals.debt_to_equity:.2f}\n"
            if fundamentals.current_ratio:
                prompt += f"Current Ratio: {fundamentals.current_ratio:.2f}\n"
            if fundamentals.free_cash_flow:
                prompt += f"Free Cash Flow: ${fundamentals.free_cash_flow:,.0f}\n"
            if fundamentals.revenue_growth:
                prompt += f"Revenue Growth: {fundamentals.revenue_growth:.1%}\n"
            if fundamentals.earnings_growth:
                prompt += f"Earnings Growth: {fundamentals.earnings_growth:.1%}\n"
        else:
            prompt += "No fundamental data available.\n"

        if stats:
            prompt += f"\nPrice: ${stats.get('close', 0):,.2f}\n"

        prompt += "\nAssess the business quality."
        return prompt
