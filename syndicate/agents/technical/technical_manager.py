"""
Technical Team Manager — synthesizes 1D Trend + 4H Signal + 1H Timing into one signal.

Implements Elder's Triple Screen synthesis:
- Daily (1D) sets the STRATEGIC DIRECTION (the tide)
- 4-Hour (4H) identifies the SETUP (the wave)
- Hourly (1H) times the ENTRY (the ripple)

The manager amplifies conviction when all timeframes agree,
and reduces it when they conflict.
"""

from __future__ import annotations

from pathlib import Path

from syndicate.agents.team_manager import BaseTeamManager, _load_manager_knowledge
from syndicate.data.models import TeamType

_KNOWLEDGE_PATH = Path(__file__).parent / "manager_knowledge.md"
_KNOWLEDGE = _load_manager_knowledge(_KNOWLEDGE_PATH)
_TRADING_KB = _load_manager_knowledge(Path(__file__).parent / "trading_knowledge.md")


class TechnicalManager(BaseTeamManager):
    """Synthesizes multi-timeframe technical signals."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.TECHNICAL

    @property
    def system_prompt(self) -> str:
        base = (
            "You are the Technical Team Manager at a quantitative crypto hedge fund.\n\n"
            "You manage three technical analysts:\n"
            "- Agent 1 (TREND): Reads the DAILY (1D) chart. Sets strategic direction.\n"
            "- Agent 2 (SIGNAL): Reads the 4-HOUR (4H) chart. Identifies tradable setups.\n"
            "- Agent 3 (TIMING): Reads the HOURLY (1H) chart. Times the entry.\n\n"
            "YOUR JOB: Synthesize their signals into ONE team signal.\n\n"
            "ELDER'S TRIPLE SCREEN RULES:\n"
            "- When ALL 3 timeframes agree → AMPLIFY conviction (8-10). This is the highest quality setup.\n"
            "- When 1D and 4H agree but 1H disagrees → Trust the higher timeframes (conviction 6-7). "
            "The hourly is noisy.\n"
            "- When 1D disagrees with 4H and 1H → REDUCE conviction significantly (3-4). "
            "Trading against the daily trend is dangerous.\n"
            "- When all 3 disagree → MINIMAL conviction (1-2). No clear edge.\n\n"
            "HIERARCHY: Daily > 4H > 1H. The daily trend is the most reliable.\n\n"
            "Set timeframe_alignment:\n"
            "- FULLY_ALIGNED: all 3 agents agree on direction\n"
            "- MOSTLY_ALIGNED: 2 of 3 agree\n"
            "- CONFLICTING: all disagree or 1D vs 4H+1H\n\n"
            "RULES:\n"
            "- You MUST pick BULLISH or BEARISH. No neutral.\n"
            "- Reference specific agent signals in reasoning.\n"
            "- Always note dissent — what the minority agent sees and why it might matter.\n"
        )
        if _KNOWLEDGE:
            base += f"\n=== YOUR KNOWLEDGE BASE ===\n{_KNOWLEDGE}\n"
        if _TRADING_KB:
            base += f"\n=== TRADING KNOWLEDGE ===\n{_TRADING_KB}\n"
        return base
