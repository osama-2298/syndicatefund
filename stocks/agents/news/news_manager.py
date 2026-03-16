"""
Stock News Team Manager — synthesizes direct news and second-order impact signals.
"""

from __future__ import annotations

from syndicate.agents.team_manager import BaseTeamManager
from syndicate.data.models import TeamType


class StockNewsManager(BaseTeamManager):
    """Synthesizes news analysis and impact signals."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.NEWS

    @property
    def system_prompt(self) -> str:
        return (
            "You are the News Team Manager at a quantitative stock hedge fund.\n\n"
            "You manage two news analysts:\n"
            "- Agent 1 (NEWS): Direct headline analysis, impact classification\n"
            "- Agent 2 (IMPACT): Second-order effects, sector contagion, supply chain\n\n"
            "SYNTHESIS RULES:\n"
            "- Breaking direct news > speculative second-order effects\n"
            "- If both agents see impact → amplify conviction\n"
            "- Fed/macro news > company-specific when market-wide\n"
            "- No news = low conviction (not necessarily neutral)\n\n"
            "Reference specific agent signals. Note any dissent."
        )
