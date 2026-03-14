"""
Hot Coin Detector — finds coins showing unusual activity that the COO missed.

Scans intelligence data (Reddit, CoinGecko trending, DeFiLlama) and identifies
coins that deserve analysis even though they weren't in the COO's initial picks.

This is the feedback loop: data sources can inject coins into the analysis queue.
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger()

# Map common names/tickers to Binance USDT pairs
SYMBOL_MAP: dict[str, str] = {
    "BTC": "BTCUSDT", "BITCOIN": "BTCUSDT",
    "ETH": "ETHUSDT", "ETHEREUM": "ETHUSDT",
    "SOL": "SOLUSDT", "SOLANA": "SOLUSDT",
    "XRP": "XRPUSDT", "RIPPLE": "XRPUSDT",
    "DOGE": "DOGEUSDT", "DOGECOIN": "DOGEUSDT",
    "ADA": "ADAUSDT", "CARDANO": "ADAUSDT",
    "AVAX": "AVAXUSDT", "AVALANCHE": "AVAXUSDT",
    "DOT": "DOTUSDT", "POLKADOT": "DOTUSDT",
    "LINK": "LINKUSDT", "CHAINLINK": "LINKUSDT",
    "UNI": "UNIUSDT", "UNISWAP": "UNIUSDT",
    "MATIC": "MATICUSDT", "POLYGON": "MATICUSDT",
    "ATOM": "ATOMUSDT", "COSMOS": "ATOMUSDT",
    "NEAR": "NEARUSDT",
    "APT": "APTUSDT", "APTOS": "APTUSDT",
    "SUI": "SUIUSDT",
    "OP": "OPUSDT", "OPTIMISM": "OPUSDT",
    "ARB": "ARBUSDT", "ARBITRUM": "ARBUSDT",
    "SEI": "SEIUSDT",
    "FET": "FETUSDT",
    "RENDER": "RENDERUSDT",
    "FIL": "FILUSDT", "FILECOIN": "FILUSDT",
    "AAVE": "AAVEUSDT",
    "MKR": "MKRUSDT", "MAKER": "MKRUSDT",
    "PEPE": "PEPEUSDT",
    "SHIB": "SHIBUSDT",
    "BONK": "BONKUSDT",
    "WIF": "WIFUSDT",
    "TAO": "TAOUSDT", "BITTENSOR": "TAOUSDT",
    "INJ": "INJUSDT",
    "TIA": "TIAUSDT", "CELESTIA": "TIAUSDT",
    "PENDLE": "PENDLEUSDT",
    "STX": "STXUSDT",
    "AR": "ARUSDT", "ARWEAVE": "ARUSDT",
    "HBAR": "HBARUSDT",
    "TRUMP": "TRUMPUSDT",
}


def _to_binance_symbol(name_or_ticker: str) -> str | None:
    """Convert a coin name or ticker to a Binance USDT pair."""
    upper = name_or_ticker.upper().strip()
    # Direct match
    if upper in SYMBOL_MAP:
        return SYMBOL_MAP[upper]
    # Already a Binance pair
    if upper.endswith("USDT"):
        return upper
    # Try appending USDT
    candidate = upper + "USDT"
    return candidate


def detect_hot_coins(
    intel: dict,
    already_selected: list[str],
    max_additions: int = 3,
) -> list[dict]:
    """
    Scan intelligence data for coins showing unusual activity
    that weren't in the COO's picks.

    Returns a list of hot coin dicts:
    [{"symbol": "XYZUSDT", "reason": "why it's hot", "sources": ["reddit", "trending"]}]
    """
    selected_set = set(already_selected)
    candidates: dict[str, dict] = {}  # symbol -> {score, reasons, sources}

    # ── Source 1: Reddit coin mentions ──
    reddit = intel.get("reddit_sentiment", {})
    coin_mentions = reddit.get("coin_mentions", {})

    for ticker, count in coin_mentions.items():
        binance_sym = _to_binance_symbol(ticker)
        if binance_sym is None or binance_sym in selected_set:
            continue
        if count >= 2:  # Mentioned at least twice across subreddits
            if binance_sym not in candidates:
                candidates[binance_sym] = {"score": 0, "reasons": [], "sources": set()}
            candidates[binance_sym]["score"] += count * 2
            candidates[binance_sym]["reasons"].append(f"mentioned {count}x on Reddit")
            candidates[binance_sym]["sources"].add("reddit")

    # ── Source 2: CoinGecko trending ──
    trending = intel.get("trending", [])

    for coin in trending[:10]:
        sym = coin.get("symbol", "")
        binance_sym = _to_binance_symbol(sym)
        if binance_sym is None or binance_sym in selected_set:
            continue
        rank = coin.get("market_cap_rank")
        # Only consider coins with reasonable market cap (rank < 200)
        if rank and rank < 200:
            if binance_sym not in candidates:
                candidates[binance_sym] = {"score": 0, "reasons": [], "sources": set()}
            candidates[binance_sym]["score"] += 5
            candidates[binance_sym]["reasons"].append(f"trending on CoinGecko (rank #{rank})")
            candidates[binance_sym]["sources"].add("trending")

    # ── Source 3: Reddit top posts mentioning specific coins ──
    top_posts = reddit.get("top_posts", [])
    for post in top_posts:
        title = post.get("title", "").upper()
        for ticker, binance_sym_mapped in SYMBOL_MAP.items():
            if ticker in title and binance_sym_mapped not in selected_set:
                if binance_sym_mapped not in candidates:
                    candidates[binance_sym_mapped] = {"score": 0, "reasons": [], "sources": set()}
                if "reddit_top" not in candidates[binance_sym_mapped]["sources"]:
                    score_val = post.get("score", 0)
                    candidates[binance_sym_mapped]["score"] += min(score_val / 100, 5)
                    candidates[binance_sym_mapped]["reasons"].append(
                        f"in top Reddit post ({score_val} upvotes)"
                    )
                    candidates[binance_sym_mapped]["sources"].add("reddit_top")

    # ── Filter: must appear in at least 1 source with meaningful score ──
    hot = []
    for symbol, data in candidates.items():
        if data["score"] < 3:
            continue
        hot.append({
            "symbol": symbol,
            "score": round(data["score"], 1),
            "reason": " + ".join(data["reasons"]),
            "sources": list(data["sources"]),
            "num_sources": len(data["sources"]),
        })

    # Sort by number of sources first (multi-source = stronger signal), then by score
    hot.sort(key=lambda x: (-x["num_sources"], -x["score"]))

    result = hot[:max_additions]
    if result:
        logger.info(
            "hot_coins_detected",
            count=len(result),
            coins=[h["symbol"] for h in result],
        )

    return result
