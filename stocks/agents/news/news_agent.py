"""
Stock News Analysis Agent — 24/7 news analysis, headline impact classification.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class StockNewsAgent(BaseAgent):
    """Primary news analysis — classifies headline impact."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.NEWS

    @property
    def system_prompt(self) -> str:
        return (
            "You are the News Analysis specialist at a stock hedge fund.\n"
            "You analyze company and market news headlines for trading signals.\n\n"
            "NEWS IMPACT HIERARCHY (most to least impact):\n"
            "1. Fed policy announcements → moves entire market\n"
            "2. Earnings surprises → moves individual stock 5-20%\n"
            "3. M&A / takeover activity → large stock-specific moves\n"
            "4. Regulatory actions (SEC, antitrust) → can be devastating\n"
            "5. Analyst upgrades/downgrades → short-term catalyst\n"
            "6. Geopolitical events → broad risk-on/off\n"
            "7. Management changes → moderate impact\n"
            "8. Product launches → sector-dependent impact\n\n"
            "TIMING MATTERS:\n"
            "- Breaking news → highest impact (first 1-4 hours)\n"
            "- Day-old news → already priced in (lower impact)\n"
            "- Consensus-forming news → trend reinforcement\n\n"
            "CONVICTION:\n"
            "- 9-10: Breaking material news directly about this stock\n"
            "- 7-8: Significant news affecting stock or sector\n"
            "- 5-6: Moderate news, some relevance\n"
            "- 3-4: Minor news or already priced in\n"
            "- 1-2: No relevant news\n\n"
            "Reference specific headlines. 2 sentences."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        company_news = market_data.get("company_news", [])
        market_news = market_data.get("market_news", [])
        stats = market_data.get("stats", {})

        prompt = f"Analyze news for {self.profile.symbol}.\n\n"

        if company_news:
            prompt += f"=== COMPANY NEWS ({len(company_news)} articles) ===\n"
            for n in company_news[:7]:
                source = f" [{n.get('source', '')}]" if n.get("source") else ""
                prompt += f"  - {n.get('headline', '?')}{source}\n"
        else:
            prompt += "No company-specific news found.\n"

        if market_news:
            prompt += f"\n=== MARKET NEWS ({len(market_news)} articles) ===\n"
            for n in market_news[:5]:
                source = f" [{n.get('source', '')}]" if n.get("source") else ""
                prompt += f"  - {n.get('headline', '?')}{source}\n"

        if stats:
            prompt += f"\nPrice: ${stats.get('close', 0):,.2f} ({stats.get('price_change_pct', 0):+.2f}%)\n"

        prompt += "\nAssess the news impact direction."
        return prompt
