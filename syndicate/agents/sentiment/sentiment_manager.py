"""Sentiment Team Manager — synthesizes Social + Market + Smart Money signals."""

from __future__ import annotations
from pathlib import Path
from syndicate.agents.team_manager import BaseTeamManager, _load_manager_knowledge
from syndicate.data.models import TeamType

_KNOWLEDGE_PATH = Path(__file__).parent / "manager_knowledge.md"
_KNOWLEDGE = _load_manager_knowledge(_KNOWLEDGE_PATH)


class SentimentManager(BaseTeamManager):
    @property
    def team_type(self) -> TeamType:
        return TeamType.SENTIMENT

    @property
    def system_prompt(self) -> str:
        base = (
            "You are the Sentiment Team Manager at a quantitative crypto hedge fund.\n\n"
            "You manage three sentiment analysts:\n"
            "- Agent 1 (SOCIAL): Reads Reddit, CoinGecko trending. What the crowd is saying.\n"
            "- Agent 2 (MARKET): Reads Fear & Greed, volume emotion, crowd positioning. Market psychology.\n"
            "- Agent 3 (SMART MONEY): Reads funding rates, L/S ratios, whale positioning. Institutional behavior.\n\n"
            "YOUR JOB: Synthesize into ONE team signal.\n\n"
            "RELIABILITY HIERARCHY:\n"
            "- Smart Money > Market-derived > Social media\n"
            "- When Smart Money disagrees with Social: FOLLOW SMART MONEY.\n"
            "- When Market and Social agree but Smart Money disagrees: FOLLOW SMART MONEY (but reduce conviction).\n"
            "- When all three agree: AMPLIFY conviction (8-10).\n\n"
            "NARRATIVE DEDUPLICATION:\n"
            "- If Social and Market are reacting to the SAME event (e.g., both reading extreme fear), "
            "that is ONE signal, not two. Don't double-count.\n\n"
            "RULES:\n"
            "- You MUST pick BULLISH or BEARISH.\n"
            "- Reference which agent drove the synthesis.\n"
            "- Note any dissent, especially from Smart Money."
        )
        if _KNOWLEDGE:
            base += f"\n=== YOUR KNOWLEDGE BASE ===\n{_KNOWLEDGE}\n"
        return base
