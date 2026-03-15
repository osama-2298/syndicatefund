"""
Stock News Impact Agent — second-order effects, sector contagion, supply chain.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class StockNewsImpactAgent(BaseAgent):
    """Second-order news impact — contagion, supply chain, regulatory domino."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.NEWS

    @property
    def system_prompt(self) -> str:
        return (
            "You are the News Impact Specialist at a stock hedge fund.\n"
            "You analyze SECOND-ORDER effects of news — not the headline itself, but the ripple effects.\n\n"
            "SECOND-ORDER EFFECTS:\n"
            "- Sector contagion: Bad earnings at one company → selloff in peers\n"
            "- Supply chain: Supplier issues → downstream company problems\n"
            "- Regulatory domino: Regulation on one company → fear across sector\n"
            "- M&A rumors: Acquisition target → other potential targets re-rated\n"
            "- Competitive dynamics: One company's loss is often another's gain\n\n"
            "SECTOR CONTAGION MAP:\n"
            "- Big tech earnings miss → ALL tech stocks feel pressure\n"
            "- Bank failure → entire financial sector sells off\n"
            "- Oil price spike → energy up, airlines/transport down\n"
            "- China trade tensions → semiconductor + manufacturing exposure\n\n"
            "CONVICTION:\n"
            "- 9-10: Clear, strong second-order effect directly impacting this stock\n"
            "- 7-8: Probable sector/industry contagion\n"
            "- 5-6: Possible indirect effect\n"
            "- 3-4: Weak or speculative connection\n"
            "- 1-2: No meaningful second-order effect\n\n"
            "Reference specific news + sector data. 2 sentences."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        company_news = market_data.get("company_news", [])
        market_news = market_data.get("market_news", [])
        sector_perf = market_data.get("sector_performance")
        stats = market_data.get("stats", {})

        prompt = f"Analyze second-order news effects for {self.profile.symbol}.\n\n"

        # Combine all news for context
        all_news = company_news + market_news
        if all_news:
            prompt += f"=== ALL NEWS ({len(all_news)} articles) ===\n"
            for n in all_news[:10]:
                prompt += f"  - {n.get('headline', '?')}\n"

        if sector_perf and sector_perf.sectors:
            prompt += "\n=== SECTOR CONTEXT ===\n"
            for sector, data in list(sector_perf.sectors.items())[:5]:
                prompt += f"  {sector}: 1d {data.get('change_1d', 0):+.1f}% | 5d {data.get('change_5d', 0):+.1f}%\n"

        if stats:
            prompt += f"\n{self.profile.symbol}: ${stats.get('close', 0):,.2f} ({stats.get('price_change_pct', 0):+.2f}%)\n"

        prompt += "\nIdentify any second-order effects impacting this stock."
        return prompt
