"""
Reddit crypto sentiment — multi-subreddit intelligence.

Fetches hot posts from the best crypto trading subreddits.
No auth needed — uses public JSON endpoints.

Subreddit tiers:
  Tier 1 (always fetch): r/CryptoCurrency, r/CryptoMarkets, r/bitcoin
  Tier 2 (fetch for depth): r/ethtrader, r/solana, r/ethfinance
  Tier 3 (contrarian signals): r/SatoshiStreetBets, r/wallstreetbetscrypto
"""

from __future__ import annotations

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

# Subreddits ranked by trading intelligence value
SUBREDDITS = {
    # Tier 1 — Core sentiment
    "CryptoCurrency": {"tier": 1, "focus": "broad crypto", "weight": 1.0},
    "CryptoMarkets": {"tier": 1, "focus": "trading/fundamentals", "weight": 1.2},
    "bitcoin": {"tier": 1, "focus": "BTC-specific", "weight": 1.0},
    # Tier 2 — Ecosystem-specific
    "ethtrader": {"tier": 2, "focus": "ETH trading", "weight": 0.8},
    "ethfinance": {"tier": 2, "focus": "ETH deep research", "weight": 0.7},
    "solana": {"tier": 2, "focus": "SOL ecosystem", "weight": 0.7},
    "cardano": {"tier": 2, "focus": "ADA ecosystem", "weight": 0.5},
    "defi": {"tier": 2, "focus": "DeFi protocols", "weight": 0.6},
    # Tier 3 — Contrarian / degen sentiment
    "SatoshiStreetBets": {"tier": 3, "focus": "retail degen", "weight": 0.4},
    "wallstreetbetscrypto": {"tier": 3, "focus": "WSB-style", "weight": 0.4},
}

USER_AGENT = "Hivemind/1.0 (crypto research bot)"

# Keywords for sentiment classification
BULLISH_WORDS = frozenset({
    "bull", "bullish", "moon", "pump", "rally", "breakout", "ath", "all time high",
    "buy", "buying", "accumulate", "long", "surge", "soar", "explode", "rocket",
    "adoption", "institutional", "etf", "approval", "green", "profit", "gains",
    "higher", "recovery", "support", "bottom", "undervalued", "cheap",
    "upgrade", "partnership", "launch", "mainnet", "halving",
})

BEARISH_WORDS = frozenset({
    "bear", "bearish", "crash", "dump", "sell", "selling", "short", "plunge",
    "collapse", "fear", "panic", "bubble", "scam", "fraud", "hack", "rug",
    "down", "lower", "resistance", "top", "capitulation", "liquidation",
    "recession", "ban", "regulation", "sec", "lawsuit", "overvalued",
    "bankrupt", "insolvent", "exploit", "vulnerability",
})

# Coin mentions — maps keywords to symbols
COIN_MENTIONS = {
    "bitcoin": "BTC", "btc": "BTC",
    "ethereum": "ETH", "eth": "ETH",
    "solana": "SOL", "sol": "SOL",
    "cardano": "ADA", "ada": "ADA",
    "dogecoin": "DOGE", "doge": "DOGE",
    "xrp": "XRP", "ripple": "XRP",
    "avalanche": "AVAX", "avax": "AVAX",
    "polkadot": "DOT", "dot": "DOT",
    "chainlink": "LINK", "link": "LINK",
    "arbitrum": "ARB", "arb": "ARB",
    "optimism": "OP",
    "sui": "SUI",
    "sei": "SEI",
    "near": "NEAR",
    "render": "RENDER",
    "pepe": "PEPE",
    "bonk": "BONK",
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
    """Classify a post as bullish/bearish and extract coin mentions."""
    text = (title + " " + selftext).lower()

    is_bullish = any(word in text for word in BULLISH_WORDS)
    is_bearish = any(word in text for word in BEARISH_WORDS)

    mentions = set()
    for keyword, symbol in COIN_MENTIONS.items():
        if keyword in text:
            mentions.add(symbol)

    return is_bullish, is_bearish, list(mentions)


def get_crypto_reddit_sentiment(limit_per_sub: int = 10) -> dict:
    """
    Fetch and analyze Reddit crypto sentiment across all subreddits.

    Returns comprehensive analysis:
    - Overall sentiment ratio and engagement
    - Per-subreddit breakdown
    - Per-coin mention counts
    - Top posts by engagement
    - Narrative themes
    """
    all_posts = []
    sub_stats = {}

    for sub_name, sub_meta in SUBREDDITS.items():
        try:
            posts = _fetch_subreddit(sub_name, limit=limit_per_sub)
            all_posts.extend(posts)

            # Per-subreddit stats
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
            "posts": [],
            "total_posts": 0,
            "subreddits_reached": 0,
            "avg_score": 0,
            "avg_comments": 0,
            "avg_upvote_ratio": 0.5,
            "bullish_keywords": 0,
            "bearish_keywords": 0,
            "sentiment_ratio": 0.5,
            "coin_mentions": {},
            "top_posts": [],
            "engagement_level": "UNKNOWN",
            "sub_stats": {},
        }

    # Overall stats
    scores = [p["score"] for p in all_posts]
    comments = [p["num_comments"] for p in all_posts]
    ratios = [p["upvote_ratio"] for p in all_posts]

    avg_score = sum(scores) / len(scores)
    avg_comments = sum(comments) / len(comments)
    avg_ratio = sum(ratios) / len(ratios)

    # Classify each post
    bullish_count = 0
    bearish_count = 0
    coin_mentions: dict[str, int] = {}

    for post in all_posts:
        is_bull, is_bear, mentions = _classify_post(post["title"], post.get("selftext", ""))
        if is_bull:
            bullish_count += 1
        if is_bear:
            bearish_count += 1
        for coin in mentions:
            coin_mentions[coin] = coin_mentions.get(coin, 0) + 1

    total_classified = bullish_count + bearish_count
    sentiment_ratio = bullish_count / max(total_classified, 1)

    # Sort coin mentions by frequency
    coin_mentions_sorted = dict(sorted(coin_mentions.items(), key=lambda x: -x[1]))

    # Engagement level
    if avg_score > 500 and avg_comments > 100:
        engagement = "HIGH"
    elif avg_score > 100 and avg_comments > 30:
        engagement = "NORMAL"
    elif avg_score > 20:
        engagement = "LOW"
    else:
        engagement = "VERY_LOW"

    # Top posts by score
    sorted_posts = sorted(all_posts, key=lambda x: -x["score"])
    top_posts = [
        {
            "title": p["title"][:100],
            "score": p["score"],
            "comments": p["num_comments"],
            "subreddit": p["subreddit"],
        }
        for p in sorted_posts[:5]
    ]

    return {
        "posts": all_posts,
        "total_posts": len(all_posts),
        "subreddits_reached": len(sub_stats),
        "avg_score": round(avg_score, 1),
        "avg_comments": round(avg_comments, 1),
        "avg_upvote_ratio": round(avg_ratio, 3),
        "bullish_keywords": bullish_count,
        "bearish_keywords": bearish_count,
        "sentiment_ratio": round(sentiment_ratio, 3),
        "coin_mentions": coin_mentions_sorted,
        "top_posts": top_posts,
        "engagement_level": engagement,
        "sub_stats": sub_stats,
    }
