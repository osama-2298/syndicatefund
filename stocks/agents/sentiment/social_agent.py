"""
Stock Social Sentiment Agent — Reddit stock subs (WSB, r/stocks, r/investing).
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class StockSocialAgent(BaseAgent):
    """Reddit stock sentiment analysis."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.SENTIMENT

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Social Sentiment analyst at a stock hedge fund.\n"
            "You monitor r/wallstreetbets, r/stocks, r/investing, r/options.\n\n"
            "WHAT YOU LOOK FOR:\n"
            "- WSB momentum plays (high post volume + engagement → retail pile-in)\n"
            "- r/stocks/r/investing consensus shifts (longer-term sentiment)\n"
            "- Stock mention frequency (rising mentions → increasing interest)\n"
            "- Contrarian signals: extreme WSB bullishness often precedes pullbacks\n\n"
            "CONVICTION:\n"
            "- 9-10: All stock subs aligned with specific ticker mention surge.\n"
            "- 7-8: Strong directional sentiment with high engagement.\n"
            "- 5-6: Mixed signals across subreddits.\n"
            "- 3-4: Low engagement or conflicting sentiment.\n"
            "- 1-2: No meaningful stock-specific sentiment.\n\n"
            "Reference specific Reddit data points. 2 sentences."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        reddit = market_data.get("reddit_sentiment", {})
        stats = market_data.get("stats", {})

        prompt = f"Analyze social sentiment for {self.profile.symbol}.\n\n"

        if reddit:
            prompt += f"=== REDDIT STOCK SENTIMENT ===\n"
            prompt += f"Total Posts: {reddit.get('total_posts', 0)} | "
            prompt += f"Sentiment: {reddit.get('sentiment_ratio', 0.5):.0%} bullish | "
            prompt += f"Engagement: {reddit.get('engagement_level', '?')}\n"
            mentions = reddit.get("stock_mentions", {})
            base = self.profile.symbol
            if base in mentions:
                prompt += f"Mentions of {base}: {mentions[base]} times\n"
            top_posts = reddit.get("top_posts", [])
            if top_posts:
                prompt += "\nHot posts:\n"
                for p in top_posts[:3]:
                    prompt += f"  - \"{p['title']}\" ({p['score']} upvotes, r/{p['subreddit']})\n"
        else:
            prompt += "No Reddit data available.\n"

        if stats:
            prompt += f"\nPrice: ${stats.get('close', 0):,.2f} | Change: {stats.get('price_change_pct', 0):+.2f}%\n"

        prompt += "\nAnalyze the social sentiment direction."
        return prompt
