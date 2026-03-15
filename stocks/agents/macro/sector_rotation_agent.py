"""
Stock Sector Rotation Agent — economic cycle → GICS sector rotation model.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class StockSectorRotationAgent(BaseAgent):
    """Sector rotation analysis based on economic cycle."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.MACRO

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Sector Rotation analyst at a stock hedge fund.\n"
            "You identify which GICS sectors should be overweight/underweight based on the economic cycle.\n\n"
            "CLASSIC SECTOR ROTATION MODEL:\n"
            "- Early Expansion: Financials, Industrials, Consumer Discretionary\n"
            "- Mid Expansion: Technology, Communication Services, Industrials\n"
            "- Late Expansion: Energy, Materials, Health Care\n"
            "- Contraction: Utilities, Consumer Staples, Health Care, REITs\n\n"
            "SECTOR MOMENTUM:\n"
            "- Hot sectors (>2% 5d gain): Momentum continuation likely\n"
            "- Cold sectors (<-2% 5d loss): Potential rotation out or reversal\n"
            "- Sector dispersion: High dispersion = stock-picking opportunity\n\n"
            "CONVICTION:\n"
            "- 9-10: Clear cycle position + sector performance confirms rotation model\n"
            "- 7-8: Most sector signals align with cycle\n"
            "- 5-6: Mixed signals, transition period\n"
            "- 3-4: Sector rotation unclear\n"
            "- 1-2: No clear sector rotation signal\n\n"
            "BULLISH if the stock's sector is favored by cycle, BEARISH if rotating out.\n"
            "Reference specific sector data. 2 sentences."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        sector_perf = market_data.get("sector_performance")
        indices = market_data.get("indices")
        stats = market_data.get("stats", {})

        prompt = f"Analyze sector rotation for {self.profile.symbol}.\n\n"

        if sector_perf and sector_perf.sectors:
            prompt += "=== GICS SECTOR PERFORMANCE ===\n"
            for sector, data in sorted(sector_perf.sectors.items(), key=lambda x: -x[1].get("change_5d", 0)):
                prompt += (
                    f"  {sector} ({data.get('etf', '?')}): "
                    f"1d {data.get('change_1d', 0):+.1f}% | "
                    f"5d {data.get('change_5d', 0):+.1f}% | "
                    f"1m {data.get('change_1m', 0):+.1f}%\n"
                )
            if sector_perf.hot_sectors:
                prompt += f"\nHot: {', '.join(sector_perf.hot_sectors)}\n"
            if sector_perf.cold_sectors:
                prompt += f"Cold: {', '.join(sector_perf.cold_sectors)}\n"
        else:
            prompt += "No sector performance data available.\n"

        if indices:
            prompt += f"\nSPY: {indices.spy_change_pct or 0:+.2f}% | QQQ: {indices.qqq_change_pct or 0:+.2f}%\n"
            if indices.vix:
                prompt += f"VIX: {indices.vix:.1f}\n"

        prompt += f"\nIs {self.profile.symbol}'s sector favored by the current rotation?"
        return prompt
