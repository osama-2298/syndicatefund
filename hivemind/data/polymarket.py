"""
Polymarket prediction market data — free, no auth.

Provides real-money crowd-sourced probabilities for:
- Fed rate decisions (97% chance of hold in March)
- Bitcoin price targets ($150K by Dec 2026: 10.5%)
- Recession odds (33.5%)
- Crypto-specific events (MicroStrategy selling, China unban, etc.)

These are NOT opinions — these are positions backed by real money.
When the market says 97% chance the Fed holds, that's $373M of conviction.
"""

from __future__ import annotations

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

GAMMA_API = "https://gamma-api.polymarket.com"


class PolymarketClient:
    """Polymarket prediction market data via Gamma API."""

    def __init__(self) -> None:
        self._client = httpx.Client(
            base_url=GAMMA_API,
            timeout=15.0,
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PolymarketClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_crypto_markets(self, limit: int = 10) -> list[dict]:
        """Get active crypto prediction markets."""
        return self._fetch_events("crypto", limit)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_economy_markets(self, limit: int = 10) -> list[dict]:
        """Get active economy/macro prediction markets."""
        return self._fetch_events("economy", limit)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_fed_markets(self, limit: int = 10) -> list[dict]:
        """Get Federal Reserve prediction markets."""
        return self._fetch_events("federal-reserve", limit)

    def get_all_relevant_markets(self) -> dict:
        """
        Fetch all markets relevant to a crypto hedge fund.
        Returns structured data by category.
        """
        result: dict = {
            "crypto": [],
            "fed": [],
            "economy": [],
            "highlights": [],
        }

        # Crypto markets
        try:
            result["crypto"] = self.get_crypto_markets(limit=15)
        except Exception as e:
            logger.warning("polymarket_crypto_failed", error=str(e))

        # Fed/rate markets
        try:
            result["fed"] = self.get_fed_markets(limit=10)
        except Exception as e:
            logger.warning("polymarket_fed_failed", error=str(e))

        # Economy/recession markets
        try:
            result["economy"] = self.get_economy_markets(limit=10)
        except Exception as e:
            logger.warning("polymarket_economy_failed", error=str(e))

        # Deduplicate: keep highest-volume contract per event (prevents double-counting)
        all_markets = result["crypto"] + result["fed"] + result["economy"]
        seen_events: dict[str, dict] = {}
        for m in all_markets:
            event_key = m.get("event_title", m.get("question", ""))
            if event_key not in seen_events or m.get("volume", 0) > seen_events[event_key].get("volume", 0):
                seen_events[event_key] = m
        deduped = list(seen_events.values())
        deduped.sort(key=lambda x: x.get("volume", 0), reverse=True)
        result["highlights"] = deduped[:10]

        return result

    def _fetch_events(self, tag_slug: str, limit: int) -> list[dict]:
        """Fetch events by tag slug and extract market data."""
        resp = self._client.get(
            "/events",
            params={"closed": "false", "tag_slug": tag_slug, "limit": limit},
        )
        resp.raise_for_status()
        events = resp.json()

        markets = []
        for event in events:
            title = event.get("title", "")
            for market in event.get("markets", []):
                outcomes = market.get("outcomes", "")
                prices = market.get("outcomePrices", "")

                # outcomes and prices can be JSON strings or lists
                import json as _json
                if isinstance(outcomes, str):
                    try:
                        outcomes = _json.loads(outcomes)
                    except (ValueError, TypeError):
                        continue
                if isinstance(prices, str):
                    try:
                        prices = _json.loads(prices)
                    except (ValueError, TypeError):
                        continue

                if not outcomes or not prices:
                    continue

                # Parse probabilities
                probabilities = {}
                for i, outcome in enumerate(outcomes):
                    if i < len(prices):
                        try:
                            probabilities[outcome] = round(float(prices[i]) * 100, 1)
                        except (ValueError, TypeError):
                            pass

                volume = 0
                for key in ["volume", "volume24hr"]:
                    try:
                        volume = float(market.get(key, 0))
                        if volume > 0:
                            break
                    except (ValueError, TypeError):
                        pass

                markets.append({
                    "event_title": title,
                    "question": market.get("question", title),
                    "probabilities": probabilities,
                    "volume": volume,
                    "volume_24h": float(market.get("volume24hr", 0) or 0),
                    "liquidity": float(market.get("liquidity", 0) or 0),
                    "best_bid": float(market.get("bestBid", 0) or 0),
                    "best_ask": float(market.get("bestAsk", 0) or 0),
                    "price_change_1d": float(market.get("oneDayPriceChange", 0) or 0),
                    "tag": tag_slug,
                })

        return markets
