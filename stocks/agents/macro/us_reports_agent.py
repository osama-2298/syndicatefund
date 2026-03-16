"""
Stock US Reports Agent — same FRED data, stock-specific interpretation.
"""

from __future__ import annotations

from typing import Any

from syndicate.agents.base import BaseAgent
from syndicate.data.models import TeamType


class StockUSReportsAgent(BaseAgent):
    """US economic reports analysis with stock market focus."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.MACRO

    @property
    def system_prompt(self) -> str:
        return (
            "You are the US Economic Reports analyst at a stock hedge fund.\n"
            "You interpret FRED data through the lens of EQUITY markets.\n\n"
            "STOCK-SPECIFIC INTERPRETATION:\n"
            "- Fed rate cuts → BULLISH for stocks (cheaper borrowing, TINA)\n"
            "- Rising inflation + rate hikes → BEARISH (P/E compression)\n"
            "- Strong employment → mixed (good economy but tighter Fed)\n"
            "- GDP growth → BULLISH (earnings grow with economy)\n"
            "- Inverted yield curve → WARNING (recession precursor, but stocks can rally 6-12mo after)\n"
            "- ISM PMI > 50 → expansion → BULLISH\n"
            "- Consumer confidence declining → BEARISH (consumer spending = 70% GDP)\n\n"
            "CRITICAL DIFFERENCE FROM CRYPTO:\n"
            "- Stocks are MORE sensitive to interest rates than crypto\n"
            "- Employment data matters MORE (payrolls drive consumer spending)\n"
            "- Dollar strength (DXY) is BEARISH for multinationals, neutral for domestics\n\n"
            "CONVICTION: Based on net direction of economic indicators.\n"
            "Reference specific report values. 2 sentences."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        us_reports = market_data.get("us_economic_reports", {})
        indices = market_data.get("indices")
        stats = market_data.get("stats", {})

        prompt = f"Analyze US economic backdrop for {self.profile.symbol}.\n\n"

        if us_reports and us_reports.get("reports"):
            prompt += "=== US ECONOMIC REPORTS ===\n"
            summary = us_reports.get("summary", {})
            prompt += f"Net Bias: {summary.get('net_bias', '?')}\n"
            prompt += f"Inflation Trend: {summary.get('inflation_trend', '?')}\n"
            prompt += f"Employment Trend: {summary.get('employment_trend', '?')}\n"
            prompt += f"Growth Trend: {summary.get('growth_trend', '?')}\n\n"

            prompt += "Key Reports (importance >= 4):\n"
            for r in us_reports["reports"]:
                if r.get("importance", 0) >= 4:
                    prompt += f"  {r['name']}: {r.get('latest_value', '?')} ({r.get('direction', '?')}) — {r.get('sentiment_read', '?')}\n"
        else:
            prompt += "No US economic data available.\n"

        if indices:
            prompt += f"\nSPY: ${indices.spy_price or 0:,.2f} ({indices.spy_change_pct or 0:+.2f}%)\n"
            if indices.treasury_10y:
                prompt += f"10Y Yield: {indices.treasury_10y:.2f}%\n"
            if indices.yield_curve_spread is not None:
                prompt += f"Yield Curve (10Y-2Y): {indices.yield_curve_spread:+.2f}%\n"

        prompt += "\nAssess the macro backdrop for stocks."
        return prompt
