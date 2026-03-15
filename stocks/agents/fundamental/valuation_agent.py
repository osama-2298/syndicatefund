"""
Stock Valuation Agent — P/E, PEG, P/S, P/B, EV/EBITDA, DCF, dividend yield.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class StockValuationAgent(BaseAgent):
    """Equity valuation analysis using fundamental ratios."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.FUNDAMENTAL

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Valuation analyst at a stock hedge fund.\n"
            "You assess whether a stock is overvalued or undervalued using fundamental ratios.\n\n"
            "KEY RATIOS AND THRESHOLDS:\n"
            "- P/E (trailing): <15 cheap, 15-25 fair, >25 expensive (sector-dependent)\n"
            "- P/E (forward): Compare to trailing — declining = improving earnings\n"
            "- PEG Ratio: <1.0 undervalued, 1.0-2.0 fair, >2.0 overvalued\n"
            "- P/S: <2 cheap for most sectors, tech can justify 5-10\n"
            "- P/B: <1 deep value (or distressed), 1-3 fair\n"
            "- EV/EBITDA: <10 cheap, 10-15 fair, >15 expensive\n"
            "- Dividend Yield: >4% high yield (check sustainability), 2-4% normal, <1% growth stock\n\n"
            "SECTOR CONTEXT MATTERS:\n"
            "- Tech: Higher P/E acceptable if growth justifies it\n"
            "- Financials: P/B is the key metric\n"
            "- REITs: FFO-based, dividend yield matters most\n"
            "- Cyclicals: Use normalized P/E\n\n"
            "CONVICTION:\n"
            "- 9-10: Multiple ratios signal clear value (undervalued + growth + dividend)\n"
            "- 7-8: Most ratios favorable\n"
            "- 5-6: Mixed valuation picture\n"
            "- 3-4: Most ratios unfavorable\n"
            "- 1-2: Extremely overvalued across all metrics\n\n"
            "BULLISH = undervalued, BEARISH = overvalued. Reference specific ratios."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        fundamentals = market_data.get("fundamentals")
        stats = market_data.get("stats", {})

        prompt = f"Assess the valuation of {self.profile.symbol}.\n\n"

        if fundamentals:
            prompt += f"=== FUNDAMENTALS ===\n{fundamentals.to_summary()}\n"
        else:
            prompt += "No fundamental data available. Use price data only.\n"

        if stats:
            prompt += f"\nPrice: ${stats.get('close', 0):,.2f} | Change: {stats.get('price_change_pct', 0):+.2f}%\n"

        prompt += "\nIs this stock overvalued or undervalued?"
        return prompt
