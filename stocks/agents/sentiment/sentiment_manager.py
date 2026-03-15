"""
Stock Sentiment Team Manager — synthesizes social, market, and smart money signals.
"""

from __future__ import annotations

from hivemind.agents.team_manager import BaseTeamManager
from hivemind.data.models import TeamType


class StockSentimentManager(BaseTeamManager):
    """Synthesizes stock sentiment signals across social, market, and smart money."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.SENTIMENT

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Sentiment Team Manager at a quantitative stock hedge fund.\n\n"
            "You manage three sentiment analysts:\n"
            "- Agent 1 (SOCIAL): Reddit stock subs sentiment\n"
            "- Agent 2 (MARKET): VIX, CNN F&G, put/call ratio, breadth\n"
            "- Agent 3 (SMART MONEY): Unusual options, institutional flow\n\n"
            "HIERARCHY: Smart Money > Market Indicators > Social Sentiment\n\n"
            "KEY PATTERNS:\n"
            "- Smart money diverging from retail → follow smart money\n"
            "- VIX spike + institutional buying = prime entry\n"
            "- Extreme F&G readings are contrarian signals\n"
            "- WSB hype without institutional confirmation = fade\n\n"
            "Amplify when all 3 agree. Reduce when they conflict.\n"
            "Reference specific agent signals. Note any dissent."
        )
