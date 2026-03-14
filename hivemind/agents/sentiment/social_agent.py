"""Social Sentiment Agent — reads Reddit and CoinGecko social signals. REAL ANALYST."""

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
            "You are a social media analyst at a crypto hedge fund.\n\n"
            "ANALYZE the actual content — read the Reddit titles, understand the narratives.\n\n"
            "What great social analysts do:\n"
            "- READ the top posts. 'Despite the crash, bottom is in' = contrarian bullish narrative forming.\n"
            "  'Exit everything' = panic, possibly a contrarian buy if from retail.\n"
            "- ENGAGEMENT matters: HIGH = crowd is paying attention (signal). LOW = apathy (noise).\n"
            "- LEADING vs LAGGING: are people excited BEFORE a move (leading, useful) or\n"
            "  reacting AFTER a move already happened (lagging, useless)?\n"
            "- Is the crowd right or wrong? Crypto research shows: extreme crowd sentiment\n"
            "  is a CONTRARIAN indicator ~80% of the time at extremes.\n\n"
            "VARIANT PERCEPTION: Is the Reddit crowd seeing something the price hasn't reflected?\n"
            "Or are they late to a move that already happened?\n\n"
            "WHAT WOULD INVALIDATE: 'Bullish social read invalid if engagement drops to VERY_LOW\n"
            "or if top posts shift from optimism to panic within hours.'\n\n"
            "Social data is NOISY. LOW engagement = cap conviction at 4.\n"
            "You MUST pick BULLISH or BEARISH. Conviction 0 if no social data."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        reddit = market_data.get("reddit_sentiment", {})
        trending = market_data.get("trending", [])

        prompt = f"What is the crowd saying about {self.profile.symbol}?\n\n"

        if reddit:
            prompt += f"=== REDDIT (10 crypto subreddits) ===\n"
            prompt += f"Posts analyzed: {reddit.get('total_posts', 0)} from {reddit.get('subreddits_reached', 0)} subs\n"
            ratio = reddit.get("sentiment_ratio", 0.5)
            prompt += f"Sentiment: {ratio:.0%} bullish / {1-ratio:.0%} bearish\n"
            prompt += f"Engagement: {reddit.get('engagement_level', 'UNKNOWN')}\n"
            prompt += f"Avg post score: {reddit.get('avg_score', 0):.0f} | Avg comments: {reddit.get('avg_comments', 0):.0f}\n"

            # Show coin mentions
            mentions = reddit.get("coin_mentions", {})
            base = self.profile.symbol.replace("USDT", "")
            if base in mentions:
                prompt += f"\nTHIS COIN ({base}) mentioned {mentions[base]} times across subreddits.\n"
            if mentions:
                top = list(mentions.items())[:7]
                prompt += f"Top mentioned coins: {', '.join(f'{c}({n})' for c, n in top)}\n"

            # Show actual post titles (the real gold — LLM can read these)
            top_posts = reddit.get("top_posts", [])
            if top_posts:
                prompt += f"\nTOP REDDIT POSTS (read these — they reveal the narrative):\n"
                for p in top_posts[:5]:
                    sub = p.get("subreddit", "?")
                    prompt += f"  [{p['score']} pts, r/{sub}] \"{p['title']}\"\n"
        else:
            prompt += "No Reddit data available.\n"

        if trending:
            prompt += f"\nCOINGECKO TRENDING:\n"
            base = self.profile.symbol.replace("USDT", "")
            is_trending = any(t.get("symbol", "").upper() == base for t in trending)
            if is_trending:
                prompt += f"  ** {base} IS TRENDING on CoinGecko right now **\n"
            names = [t.get("symbol", "?") for t in trending[:7]]
            prompt += f"  Top trending: {', '.join(names)}\n"

        prompt += "\nWhat is the crowd feeling? Is this noise or signal? Form your thesis."
        return prompt
