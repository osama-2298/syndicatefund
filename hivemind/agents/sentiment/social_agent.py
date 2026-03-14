"""Social Sentiment Agent — reads Reddit and CoinGecko social signals."""

from __future__ import annotations
from typing import Any
from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class SocialSentimentAgent(BaseAgent):
    @property
    def team_type(self) -> TeamType:
        return TeamType.SENTIMENT

    @property
    def system_prompt(self) -> str:
        return (
            "You read SOCIAL MEDIA sentiment: Reddit (10 subreddits) and CoinGecko trending.\n"
            "You MUST pick BULLISH or BEARISH. Conviction 0 if no social data available.\n\n"
            "QUANTITATIVE DECISION RULES:\n"
            "- Reddit sentiment > 65% bullish + HIGH engagement → BULLISH conviction 7-8\n"
            "- Reddit sentiment 55-65% bullish + this coin mentioned 3+ times → BULLISH conviction 5-6\n"
            "- Reddit sentiment 45-55% (neutral) → conviction 2-3 in direction of top posts\n"
            "- Reddit sentiment 35-45% bullish → BEARISH conviction 5-6\n"
            "- Reddit sentiment < 35% bullish + HIGH engagement → BEARISH conviction 7-8\n"
            "- Coin is TRENDING on CoinGecko → add +1 conviction\n"
            "- Engagement LOW → cap conviction at 4 (social data unreliable with low volume)\n\n"
            "RULES: Social data is NOISY. Conviction 5+ requires either HIGH engagement or 3+ mentions.\n"
            "Reference specific Reddit ratio and engagement level. 2 sentences max."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        reddit = market_data.get("reddit_sentiment", {})
        trending = market_data.get("trending", [])

        prompt = f"Read social sentiment for {self.profile.symbol}.\n\n"
        if reddit:
            ratio = reddit.get("sentiment_ratio", 0.5)
            prompt += f"Reddit: {ratio:.0%} bullish | {reddit.get('total_posts', 0)} posts | {reddit.get('engagement_level', '?')} engagement\n"
            mentions = reddit.get("coin_mentions", {})
            base = self.profile.symbol.replace("USDT", "")
            if base in mentions:
                prompt += f"This coin mentioned {mentions[base]}x on Reddit\n"
            top = reddit.get("top_posts", [])
            if top:
                for p in top[:3]:
                    prompt += f"  Hot: \"{p['title'][:60]}\" ({p['score']} pts)\n"
        if trending:
            names = [t.get("symbol", "") for t in trending[:7]]
            prompt += f"\nTrending: {', '.join(names)}\n"
            base = self.profile.symbol.replace("USDT", "")
            is_trending = any(t.get("symbol", "").upper() == base for t in trending)
            if is_trending:
                prompt += f"THIS COIN IS TRENDING on CoinGecko\n"
        prompt += "\nPredict social sentiment direction."
        return prompt
