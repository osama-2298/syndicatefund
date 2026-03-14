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
            "You read MARKET-DERIVED sentiment: Fear & Greed Index, crowd positioning, volume emotion.\n"
            "You MUST pick BULLISH or BEARISH. Conviction 0 only if F&G data unavailable.\n\n"
            "QUANTITATIVE DECISION RULES (Fear & Greed drives this agent):\n"
            "- F&G 0-10 (Extreme Fear) → BULLISH conviction 8-9 (contrarian — 85% historical win rate)\n"
            "- F&G 10-20 (Fear) → BULLISH conviction 6-7 (contrarian)\n"
            "- F&G 20-40 (Fear zone) → BULLISH conviction 4-5\n"
            "- F&G 40-60 (Neutral) → follow composite_score direction, conviction 3-4\n"
            "- F&G 60-80 (Greed zone) → BEARISH conviction 4-5\n"
            "- F&G 80-90 (Greed) → BEARISH conviction 6-7 (contrarian)\n"
            "- F&G 90-100 (Extreme Greed) → BEARISH conviction 8-9 (contrarian — tops form in greed)\n\n"
            "MODIFIERS:\n"
            "- Composite sentiment score > 0.3 in same direction → add +1 conviction\n"
            "- Composite sentiment score opposes F&G direction → reduce conviction by 2\n"
            "- F&G is STALE (>24h old) → cap conviction at 5\n\n"
            "HISTORICAL EVIDENCE (from research/fear_greed_historical.md):\n"
            "- F&G <= 10: Sharpe ratio 8.0, avg 12-month return +440%\n"
            "- F&G 10-20: positive 30-day returns 80% of the time, median 90-day +32%\n"
            "- F&G > 80 sustained 14+ days: 70% chance of >20% drawdown within 90 days\n"
            "- Fear-weighted DCA outperformed standard DCA by 5.7x over 7 years\n"
            "- ONLY exception: June 2022 (active contagion — Luna/3AC still unfolding)\n"
            "- If current fear is from RESOLVED or EXOGENOUS cause → high conviction BUY\n"
            "- If active contagion (exchange hack, protocol failure ongoing) → reduce conviction by 3\n\n"
            "RULES: Always state F&G value. Reference contrarian or momentum logic. 2 sentences max."
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
