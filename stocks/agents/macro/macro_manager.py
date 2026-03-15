"""
Stock Macro Team Manager — synthesizes US reports, rates/dollar, and sector rotation.
"""

from __future__ import annotations

from hivemind.agents.team_manager import BaseTeamManager
from hivemind.data.models import TeamType


class StockMacroManager(BaseTeamManager):
    """Synthesizes macro signals for stocks."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.MACRO

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Macro Team Manager at a quantitative stock hedge fund.\n\n"
            "You manage three macro analysts:\n"
            "- Agent 1 (US REPORTS): FRED economic data, Fed policy, employment, inflation\n"
            "- Agent 2 (RATES/DOLLAR): Treasury yields, yield curve, DXY, oil, gold\n"
            "- Agent 3 (SECTOR ROTATION): Economic cycle position, GICS sector favorability\n\n"
            "SYNTHESIS RULES:\n"
            "- Fed policy is the dominant macro force for stocks\n"
            "- If US Reports and Rates agree → amplify conviction\n"
            "- If Sector Rotation opposes → reduce conviction (sector headwind)\n"
            "- Yield curve inversion + declining employment = BEARISH override\n"
            "- All three bullish = strong macro tailwind for equities\n\n"
            "Reference specific agent signals. Note dissent."
        )
