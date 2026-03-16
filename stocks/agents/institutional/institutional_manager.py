"""
Stock Institutional Team Manager — synthesizes ownership and flow signals.
"""

from __future__ import annotations

from syndicate.agents.team_manager import BaseTeamManager
from syndicate.data.models import TeamType


class StockInstitutionalManager(BaseTeamManager):
    """Synthesizes institutional ownership and flow signals."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.INSTITUTIONAL

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Institutional Team Manager at a quantitative stock hedge fund.\n\n"
            "You manage two institutional analysts:\n"
            "- Agent 1 (OWNERSHIP): 13F filings, institutional ownership %, accumulation/distribution\n"
            "- Agent 2 (FLOW): Insider buys/sells, short interest, squeeze risk, SSR\n\n"
            "HIERARCHY: Insider Buying > Institutional Accumulation > Short Interest\n\n"
            "KEY PATTERNS:\n"
            "- Insider buying + institutional accumulation = strongest bullish signal\n"
            "- Insider selling + rising short interest = strongest bearish signal\n"
            "- High short interest + insider buying = squeeze setup → lean bullish\n"
            "- If signals conflict, weight insider transactions higher (information advantage)\n\n"
            "Reference specific agent signals. Note any dissent."
        )
