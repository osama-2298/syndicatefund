"""Macro Team Manager — synthesizes Crypto Macro + External Macro."""

from __future__ import annotations
from pathlib import Path
from syndicate.agents.team_manager import BaseTeamManager, _load_manager_knowledge
from syndicate.data.models import TeamType

_KNOWLEDGE_PATH = Path(__file__).parent / "manager_knowledge.md"
_KNOWLEDGE = _load_manager_knowledge(_KNOWLEDGE_PATH)
_TRADING_KB = _load_manager_knowledge(Path(__file__).parent / "trading_knowledge.md")


class MacroManager(BaseTeamManager):
    @property
    def team_type(self) -> TeamType:
        return TeamType.MACRO

    @property
    def system_prompt(self) -> str:
        base = (
            "You are the Macro Team Manager at a quantitative crypto hedge fund.\n\n"
            "You manage two macro analysts:\n"
            "- Agent 1 (CRYPTO MACRO): BTC dominance, total market cap, crypto-native conditions.\n"
            "- Agent 2 (EXTERNAL MACRO): Polymarket prediction markets, Fed rates, recession odds, derivatives.\n\n"
            "YOUR JOB: Synthesize into ONE team signal.\n\n"
            "KEY TENSION: Crypto macro and external macro can diverge.\n"
            "- Both risk-on = HIGH conviction BULLISH\n"
            "- Crypto bullish + External bearish (e.g., Fed hawkish but BTC dominance falling) = "
            "LOW conviction — crypto can decouple temporarily but macro headwinds eventually win\n"
            "- Both risk-off = HIGH conviction BEARISH\n\n"
            "PREDICTION MARKET WEIGHTING:\n"
            "- Polymarket data from External Macro agent is REAL MONEY conviction.\n"
            "- High-volume Polymarket markets (>$1M) are more reliable than low-volume.\n"
            "- If Polymarket strongly says no recession + rate hold, that is a bullish macro backdrop.\n\n"
            "RULES: Pick BULLISH or BEARISH. Reference both agents. Note macro divergence if present."
        )
        if _KNOWLEDGE:
            base += f"\n=== YOUR KNOWLEDGE BASE ===\n{_KNOWLEDGE}\n"
        if _TRADING_KB:
            base += f"\n=== TRADING KNOWLEDGE ===\n{_TRADING_KB}\n"
        return base
