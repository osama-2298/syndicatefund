"""CryptoPanic news sentiment — real-time crypto news with community-voted sentiment.

API: https://cryptopanic.com/api/v1/posts/
Free tier: requires auth_token (free registration), basic rate limiting.

Provides news articles pre-labeled as bullish/bearish/neutral by community votes,
making it much faster signal than raw Reddit scraping.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import httpx
import structlog

logger = structlog.get_logger()

CRYPTOPANIC_BASE = "https://cryptopanic.com/api/v1"


class NewsSentimentClient:
    """Fetch crypto news with sentiment from CryptoPanic."""

    def __init__(self, auth_token: str = ""):
        self._client = httpx.Client(timeout=15.0)
        self._auth_token = auth_token

    def get_news_sentiment(self, currencies: str = "BTC,ETH,SOL,BNB,XRP",
                           kind: str = "news", limit: int = 50) -> dict:
        """Get recent news with sentiment labels.

        Args:
            currencies: Comma-separated currency codes to filter
            kind: "news" for articles, "media" for videos/podcasts
            limit: Max results

        Returns:
            {
                "articles": list[dict],           # Recent articles with sentiment
                "overall_sentiment": "BULLISH" | "BEARISH" | "NEUTRAL",
                "bullish_count": int,
                "bearish_count": int,
                "neutral_count": int,
                "sentiment_ratio": float,          # 0-1, >0.5 = bullish
                "important_news": list[dict],      # High-impact articles
                "per_coin_sentiment": dict,         # Per-coin breakdown
            }
        """
        if not self._auth_token:
            logger.warning("cryptopanic_no_auth_token", msg="Set CRYPTOPANIC_API_KEY in .env")
            return self._empty_result()

        params = {
            "auth_token": self._auth_token,
            "public": "true",
            "kind": kind,
            "currencies": currencies,
        }

        try:
            resp = self._client.get(f"{CRYPTOPANIC_BASE}/posts/", params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("cryptopanic_fetch_failed", error=str(e))
            return self._empty_result()

        results = data.get("results", [])
        if not results:
            return self._empty_result()

        articles = []
        bullish = 0
        bearish = 0
        neutral = 0
        per_coin: dict = {}
        important = []

        for post in results[:limit]:
            title = post.get("title", "")
            url = post.get("url", "")
            source = post.get("source", {}).get("title", "")
            published = post.get("published_at", "")

            # Sentiment from community votes
            votes = post.get("votes", {})
            positive = votes.get("positive", 0)
            negative = votes.get("negative", 0)
            important_votes = votes.get("important", 0)

            # Determine sentiment
            if positive > negative * 1.5:
                sentiment = "bullish"
                bullish += 1
            elif negative > positive * 1.5:
                sentiment = "bearish"
                bearish += 1
            else:
                sentiment = "neutral"
                neutral += 1

            # Extract currencies mentioned
            currencies_mentioned = [c.get("code", "") for c in post.get("currencies", [])]

            article = {
                "title": title,
                "source": source,
                "sentiment": sentiment,
                "positive_votes": positive,
                "negative_votes": negative,
                "important_votes": important_votes,
                "currencies": currencies_mentioned,
                "published_at": published,
            }
            articles.append(article)

            # Track per-coin sentiment
            for coin in currencies_mentioned:
                if coin not in per_coin:
                    per_coin[coin] = {"bullish": 0, "bearish": 0, "neutral": 0, "total": 0}
                per_coin[coin][sentiment] += 1
                per_coin[coin]["total"] += 1

            # Flag important news
            if important_votes >= 3 or positive + negative >= 10:
                important.append(article)

        total = bullish + bearish + neutral
        ratio = bullish / max(total, 1)

        if ratio > 0.6:
            overall = "BULLISH"
        elif ratio < 0.4:
            overall = "BEARISH"
        else:
            overall = "NEUTRAL"

        # Compute per-coin sentiment ratios
        for coin in per_coin:
            t = per_coin[coin]["total"]
            if t > 0:
                per_coin[coin]["sentiment_ratio"] = per_coin[coin]["bullish"] / t

        return {
            "articles": articles[:20],
            "overall_sentiment": overall,
            "bullish_count": bullish,
            "bearish_count": bearish,
            "neutral_count": neutral,
            "sentiment_ratio": round(ratio, 3),
            "important_news": important[:5],
            "per_coin_sentiment": per_coin,
        }

    def _empty_result(self):
        return {
            "articles": [],
            "overall_sentiment": "UNKNOWN",
            "bullish_count": 0,
            "bearish_count": 0,
            "neutral_count": 0,
            "sentiment_ratio": 0.5,
            "important_news": [],
            "per_coin_sentiment": {},
        }

    def close(self):
        self._client.close()
