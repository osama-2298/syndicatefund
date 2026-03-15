"""
Stock Ownership Agent — 13F filings, institutional ownership %, QoQ changes.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class StockOwnershipAgent(BaseAgent):
    """Institutional ownership analysis from 13F filings."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.INSTITUTIONAL

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Institutional Ownership analyst at a stock hedge fund.\n"
            "You analyze 13F filings and institutional holder patterns.\n\n"
            "KEY SIGNALS:\n"
            "- Institutional ownership >70% = well-owned, stable (but limited upside catalyst)\n"
            "- Institutional ownership <30% = under-owned (potential discovery play)\n"
            "- QoQ increase in institutional % = accumulation → BULLISH\n"
            "- QoQ decrease = distribution → BEARISH\n"
            "- Top holders adding = smart money conviction\n"
            "- Top holders reducing = potential exit signal\n\n"
            "NOTABLE PATTERNS:\n"
            "- Multiple top-10 holders adding → strong institutional conviction\n"
            "- Large new position by known activist → potential catalyst\n"
            "- Concentrated ownership by few holders → higher volatility risk\n\n"
            "CONVICTION:\n"
            "- 9-10: Strong institutional accumulation with rising % + quality holders\n"
            "- 7-8: Net accumulation by institutions\n"
            "- 5-6: Mixed institutional activity\n"
            "- 3-4: Net distribution by institutions\n"
            "- 1-2: Heavy institutional selling\n\n"
            "Reference specific holder data. 2 sentences."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        institutional = market_data.get("institutional")
        stats = market_data.get("stats", {})

        prompt = f"Analyze institutional ownership for {self.profile.symbol}.\n\n"

        if institutional:
            if institutional.institutional_pct:
                prompt += f"Institutional Ownership: {institutional.institutional_pct:.1%}\n"
            if institutional.institutional_change_qoq:
                prompt += f"QoQ Change: {institutional.institutional_change_qoq:+.1%}\n"
            if institutional.top_holders:
                prompt += "\nTop Institutional Holders:\n"
                for h in institutional.top_holders[:5]:
                    pct_str = f" ({h.get('pct', '?')}%)" if h.get("pct") else ""
                    prompt += f"  - {h.get('name', '?')}: {h.get('shares', 0):,} shares{pct_str}\n"
        else:
            prompt += "No institutional data available.\n"

        if stats:
            prompt += f"\nPrice: ${stats.get('close', 0):,.2f}\n"

        prompt += "\nAssess institutional conviction."
        return prompt
