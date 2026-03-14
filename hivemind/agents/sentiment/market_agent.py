"""Market Sentiment Agent — reads Fear & Greed, volume emotion, crowd positioning."""

from __future__ import annotations
from typing import Any
from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType, TechnicalIndicators
from hivemind.agents.sentiment.sentiment_agent import compute_sentiment_scores


class MarketSentimentAgent(BaseAgent):
    @property
    def team_type(self) -> TeamType:
        return TeamType.SENTIMENT

    @property
    def system_prompt(self) -> str:
        return (
            "You read MARKET-DERIVED sentiment: Fear & Greed Index, price/volume emotion, "
            "crowd positioning (RSI, BB), and momentum sentiment.\n\n"
            "Your job: predict whether MARKET PSYCHOLOGY favors HIGHER or LOWER prices.\n"
            "You MUST pick BULLISH or BEARISH.\n\n"
            "CONTRARIAN RULES:\n"
            "- F&G < 15 (Extreme Fear) → lean BULLISH (contrarian buy, historically 85% win rate)\n"
            "- F&G > 85 (Extreme Greed) → lean BEARISH (contrarian sell)\n"
            "- In the middle (25-75): follow momentum, not contrarian\n\n"
            "CONVICTION: 9-10 extreme F&G reading with volume confirmation. 5-6 moderate. 1-2 neutral F&G.\n"
            "RULES: Reference F&G value and crowd positioning. 2 sentences."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        indicators = market_data.get("indicators")
        stats = market_data.get("stats_24h", {})
        fear_greed = market_data.get("fear_greed")

        prompt = f"Read market sentiment for {self.profile.symbol}.\n\n"

        if fear_greed:
            prompt += f"Fear & Greed: {fear_greed['current_value']}/100 ({fear_greed['current_label']}) trend: {fear_greed.get('trend', '?')}\n"

        if indicators:
            scores = compute_sentiment_scores(indicators, stats, fear_greed)
            prompt += f"Fear/Greed Score: {scores['fear_greed_score']:+.3f} ({scores['fear_greed_label']})\n"
            prompt += f"Crowd Score: {scores['crowd_score']:+.3f} ({scores['crowd_label']})\n"
            prompt += f"Momentum Sentiment: {scores['momentum_sentiment_score']:+.3f} ({scores['momentum_sentiment_label']})\n"
            prompt += f"Contrarian Score: {scores['contrarian_score']:+.3f} ({scores['contrarian_label']})\n"
            prompt += f"Composite: {scores['composite_score']:+.3f} ({scores['composite_label']})\n"

        prompt += "\nPredict market sentiment direction."
        return prompt
