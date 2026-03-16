"""
Stock Rates & Dollar Agent — Treasury 2Y/10Y, yield curve, DXY, oil, gold.
"""

from __future__ import annotations

from typing import Any

from syndicate.agents.base import BaseAgent
from syndicate.data.models import TeamType


class StockRatesDollarAgent(BaseAgent):
    """Interest rates, dollar, and cross-asset analysis for stocks."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.MACRO

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Rates & Dollar analyst at a stock hedge fund.\n"
            "You analyze interest rates, the US dollar, and commodities for their impact on equities.\n\n"
            "RATES GUIDE:\n"
            "- Rising 10Y yield → BEARISH for growth stocks (higher discount rate)\n"
            "- Rising 10Y yield → NEUTRAL/BULLISH for financials (better NIM)\n"
            "- Falling yields → BULLISH for growth, BEARISH for banks\n"
            "- Yield curve inversion (2Y > 10Y) → recession warning\n"
            "- Yield curve steepening → recovery signal\n\n"
            "DOLLAR (DXY):\n"
            "- Rising DXY → BEARISH for multinationals (hurts foreign earnings)\n"
            "- Falling DXY → BULLISH for S&P 500 (35% international revenue)\n"
            "- Extreme DXY moves → flight to safety\n\n"
            "COMMODITIES:\n"
            "- Rising oil → BULLISH energy sector, BEARISH consumer/transport\n"
            "- Rising gold → risk-off signal, potential inflation hedge demand\n\n"
            "CONVICTION:\n"
            "- 9-10: Rates, dollar, commodities all pointing same direction for equities\n"
            "- 5-6: Mixed signals across asset classes\n"
            "- 1-2: No clear directional signal from cross-asset analysis\n\n"
            "Reference specific values. 2 sentences."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        indices = market_data.get("indices")
        stats = market_data.get("stats", {})

        prompt = f"Analyze rates and cross-asset signals for {self.profile.symbol}.\n\n"

        if indices:
            prompt += "=== RATES & DOLLAR ===\n"
            if indices.treasury_2y:
                prompt += f"2Y Treasury: {indices.treasury_2y:.2f}%\n"
            if indices.treasury_10y:
                prompt += f"10Y Treasury: {indices.treasury_10y:.2f}%\n"
            if indices.yield_curve_spread is not None:
                status = "INVERTED" if indices.yield_curve_spread < 0 else "NORMAL" if indices.yield_curve_spread > 0.5 else "FLAT"
                prompt += f"Yield Curve (10Y-2Y): {indices.yield_curve_spread:+.2f}% [{status}]\n"
            if indices.dxy:
                prompt += f"DXY (Dollar Index): {indices.dxy:.1f}\n"
            if indices.oil_price:
                prompt += f"Oil: ${indices.oil_price:.2f}\n"
            if indices.gold_price:
                prompt += f"Gold: ${indices.gold_price:.2f}\n"
            if indices.vix:
                prompt += f"VIX: {indices.vix:.1f}\n"
        else:
            prompt += "No market index data available.\n"

        prompt += "\nAssess cross-asset impact on this stock."
        return prompt
