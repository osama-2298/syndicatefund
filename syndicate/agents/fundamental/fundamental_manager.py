"""Fundamental Team Manager — synthesizes Valuation + Cycle Position."""

from __future__ import annotations
from pathlib import Path
from syndicate.agents.team_manager import BaseTeamManager, _load_manager_knowledge
from syndicate.data.models import TeamType

_KNOWLEDGE_PATH = Path(__file__).parent / "manager_knowledge.md"
_KNOWLEDGE = _load_manager_knowledge(_KNOWLEDGE_PATH)
_TRADING_KB = _load_manager_knowledge(Path(__file__).parent / "trading_knowledge.md")


class FundamentalManager(BaseTeamManager):
    @property
    def team_type(self) -> TeamType:
        return TeamType.FUNDAMENTAL

    @property
    def system_prompt(self) -> str:
        base = (
            "You are the Fundamental Team Manager at a quantitative crypto hedge fund.\n\n"
            "You manage two fundamental analysts:\n"
            "- Agent 1 (VALUATION): Is this asset cheap or expensive? FDV, supply, ATH distance.\n"
            "- Agent 2 (CYCLE): Where are we in the market cycle? Accumulation, markup, distribution, markdown.\n\n"
            "YOUR JOB: Synthesize into ONE team signal.\n\n"
            "KEY TENSION: An asset can be CHEAP but in MARKDOWN (value trap). "
            "Or EXPENSIVE but in EARLY MARKUP (momentum play).\n"
            "- Cheap + Accumulation/Markup = HIGH conviction BULLISH (best setup)\n"
            "- Cheap + Markdown = LOW conviction BULLISH (value trap risk — wait for cycle turn)\n"
            "- Expensive + Distribution = HIGH conviction BEARISH\n"
            "- Expensive + Markup = MODERATE conviction — momentum works until it doesn't\n\n"
            "RULES: Pick BULLISH or BEARISH. Explain the valuation/cycle tension. Note dissent."
        )
        if _KNOWLEDGE:
            base += f"\n=== YOUR KNOWLEDGE BASE ===\n{_KNOWLEDGE}\n"
        if _TRADING_KB:
            base += f"\n=== TRADING KNOWLEDGE ===\n{_TRADING_KB}\n"
        return base
