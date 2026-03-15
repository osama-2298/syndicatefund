"""
Reddit stock sentiment — r/wallstreetbets, r/stocks, r/investing, r/options.

Same scraping pattern as hivemind crypto Reddit module.
"""

from __future__ import annotations

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

SUBREDDITS = {
    "wallstreetbets": {"tier": 1, "focus": "YOLO trades, momentum", "weight": 1.0},
    "stocks": {"tier": 1, "focus": "general stock discussion", "weight": 1.2},
    "investing": {"tier": 1, "focus": "long-term investing", "weight": 0.8},
    "options": {"tier": 2, "focus": "options trading", "weight": 0.9},
    "StockMarket": {"tier": 2, "focus": "market news", "weight": 0.7},
    "ValueInvesting": {"tier": 2, "focus": "value plays", "weight": 0.6},
    "Daytrading": {"tier": 3, "focus": "short-term trades", "weight": 0.5},
    "pennystocks": {"tier": 3, "focus": "small caps", "weight": 0.3},
}

USER_AGENT = "Hivemind/1.0 (stock research bot)"

BULLISH_WORDS = frozenset({
    "bull", "bullish", "moon", "pump", "rally", "breakout", "ath", "all time high",
    "buy", "buying", "long", "calls", "surge", "soar", "rocket",
    "earnings beat", "upgrade", "buy the dip", "green", "profit", "gains",
    "higher", "recovery", "support", "bottom", "undervalued", "cheap",
    "partnership", "guidance raised", "beat estimates",
})

BEARISH_WORDS = frozenset({
    "bear", "bearish", "crash", "dump", "sell", "selling", "short", "puts",
    "collapse", "fear", "panic", "bubble", "overvalued",
    "down", "lower", "resistance", "top", "capitulation", "liquidation",
    "recession", "layoffs", "miss", "guidance cut", "downgrade",
    "sec", "lawsuit", "investigation", "fraud",
})

# Popular stock ticker mentions
STOCK_MENTIONS = {
    "aapl": "AAPL", "apple": "AAPL",
    "msft": "MSFT", "microsoft": "MSFT",
    "nvda": "NVDA", "nvidia": "NVDA",
    "tsla": "TSLA", "tesla": "TSLA",
    "amzn": "AMZN", "amazon": "AMZN",
    "googl": "GOOGL", "google": "GOOGL", "goog": "GOOGL",
    "meta": "META", "facebook": "META",
    "amd": "AMD",
    "pltr": "PLTR", "palantir": "PLTR",
    "spy": "SPY",
    "gme": "GME", "gamestop": "GME",
    "amc": "AMC",
    "sofi": "SOFI",
    "rivn": "RIVN", "rivian": "RIVN",
    "coin": "COIN", "coinbase": "COIN",
}


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, max=5))
def _fetch_subreddit(subreddit: str, limit: int = 10) -> list[dict]:
    """Fetch hot posts from a subreddit."""
    url = f"https://old.reddit.com/r/{subreddit}/hot.json"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(
            url,
            params={"limit": limit},
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
        data = resp.json()

    posts = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        if post.get("stickied"):
            continue
        posts.append({
            "title": post.get("title", ""),
            "score": post.get("score", 0),
            "num_comments": post.get("num_comments", 0),
            "upvote_ratio": post.get("upvote_ratio", 0.5),
            "created_utc": post.get("created_utc", 0),
            "subreddit": subreddit,
            "selftext": (post.get("selftext", "") or "")[:200],
        })
    return posts


def _classify_post(title: str, selftext: str = "") -> tuple[bool, bool, list[str]]:
    text = (title + " " + selftext).lower()
    is_bullish = any(word in text for word in BULLISH_WORDS)
    is_bearish = any(word in text for word in BEARISH_WORDS)
    mentions = set()
    for keyword, symbol in STOCK_MENTIONS.items():
        if keyword in text:
            mentions.add(symbol)
    return is_bullish, is_bearish, list(mentions)


def get_stock_reddit_sentiment(limit_per_sub: int = 10) -> dict:
    """Fetch and analyze Reddit stock sentiment across all subreddits."""
    all_posts = []
    sub_stats = {}

    for sub_name, sub_meta in SUBREDDITS.items():
        try:
            posts = _fetch_subreddit(sub_name, limit=limit_per_sub)
            all_posts.extend(posts)
            if posts:
                scores = [p["score"] for p in posts]
                sub_stats[sub_name] = {
                    "tier": sub_meta["tier"],
                    "focus": sub_meta["focus"],
                    "posts": len(posts),
                    "avg_score": round(sum(scores) / len(scores), 1),
                    "total_comments": sum(p["num_comments"] for p in posts),
                }
        except Exception as e:
            logger.warning("reddit_fetch_failed", subreddit=sub_name, error=str(e))

    if not all_posts:
        return {
            "total_posts": 0, "sentiment_ratio": 0.5,
            "stock_mentions": {}, "top_posts": [],
            "engagement_level": "UNKNOWN",
        }

    scores = [p["score"] for p in all_posts]
    avg_score = sum(scores) / len(scores)

    bullish_count = 0
    bearish_count = 0
    stock_mentions: dict[str, int] = {}

    for post in all_posts:
        is_bull, is_bear, mentions = _classify_post(post["title"], post.get("selftext", ""))
        if is_bull:
            bullish_count += 1
        if is_bear:
            bearish_count += 1
        for ticker in mentions:
            stock_mentions[ticker] = stock_mentions.get(ticker, 0) + 1

    total_classified = bullish_count + bearish_count
    sentiment_ratio = bullish_count / max(total_classified, 1)

    stock_mentions_sorted = dict(sorted(stock_mentions.items(), key=lambda x: -x[1]))

    if avg_score > 500:
        engagement = "HIGH"
    elif avg_score > 100:
        engagement = "NORMAL"
    elif avg_score > 20:
        engagement = "LOW"
    else:
        engagement = "VERY_LOW"

    sorted_posts = sorted(all_posts, key=lambda x: -x["score"])
    top_posts = [
        {"title": p["title"][:100], "score": p["score"], "comments": p["num_comments"], "subreddit": p["subreddit"]}
        for p in sorted_posts[:5]
    ]

    return {
        "total_posts": len(all_posts),
        "subreddits_reached": len(sub_stats),
        "bullish_keywords": bullish_count,
        "bearish_keywords": bearish_count,
        "sentiment_ratio": round(sentiment_ratio, 3),
        "stock_mentions": stock_mentions_sorted,
        "top_posts": top_posts,
        "engagement_level": engagement,
        "sub_stats": sub_stats,
    }
