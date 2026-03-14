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
            "You read SOCIAL MEDIA sentiment: Reddit (10 subreddits), CoinGecko trending, "
            "and community engagement data.\n\n"
            "Your job: predict whether the CROWD is positioned for prices to go HIGHER or LOWER.\n"
            "You MUST pick BULLISH or BEARISH.\n\n"
            "WHAT YOU LOOK FOR:\n"
            "- Reddit sentiment ratio (% bullish vs bearish posts)\n"
            "- Reddit coin-specific mentions (is this coin being talked about?)\n"
            "- CoinGecko trending (social search momentum)\n"
            "- Reddit engagement level (HIGH engagement = stronger signal)\n"
            "- Top Reddit post titles (what narratives are forming?)\n\n"
            "CONVICTION: 9-10 extreme social buzz. 5-6 moderate. 1-2 low engagement.\n"
            "RULES: Reference specific Reddit data. 2 sentences. Social data is noisy — low conviction is normal."
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
