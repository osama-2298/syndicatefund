"""
Opportunity Scanner — actively discovers tradeable coins from multiple live sources.

Instead of relying on fixed lists, this scanner queries live APIs every cycle
to find coins showing unusual activity, momentum, or volume spikes.

Sources:
  1. Binance gainers/losers (biggest 24h movers)
  2. Binance volume spike detection (coins with unusual volume vs 7d avg)
  3. CoinGecko trending (social/search momentum)
  4. CoinGecko top movers (biggest price changes)
  5. CoinPaprika movers (cross-references CoinGecko)

The scanner runs BEFORE coin selection and feeds candidates to the COO.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

# Stablecoins and wrapped tokens to exclude
_EXCLUDED = {
    "USDCUSDT", "BUSDUSDT", "TUSDUSDT", "DAIUSDT", "FDUSDUSDT",
    "USDPUSDT", "USTCUSDT", "EURUSDT", "GBPUSDT", "AEURUSDT",
    "BTCDOWNUSDT", "BTCUPUSDT", "ETHDOWNUSDT", "ETHUPUSDT",
}


def _is_valid_symbol(sym: str) -> bool:
    """Check if a symbol is a tradeable USDT pair (not stable/leveraged/wrapped)."""
    if not sym.endswith("USDT"):
        return False
    if sym in _EXCLUDED:
        return False
    base = sym.replace("USDT", "")
    if base.endswith(("UP", "DOWN", "BEAR", "BULL", "3L", "3S")):
        return False
    return True


class OpportunityScanner:
    """Scans multiple sources for trading opportunities every cycle."""

    def __init__(self) -> None:
        self._client = httpx.Client(timeout=15.0, headers={"Accept": "application/json"})

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> OpportunityScanner:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def scan(self, min_volume: float = 250_000) -> dict[str, Any]:
        """Run a full opportunity scan across all sources.

        Returns:
            Dict with categorized opportunities:
            - gainers: top price gainers (24h)
            - losers: top price losers (potential mean reversion)
            - volume_spikes: coins with unusual volume
            - trending: socially trending coins
            - movers: combined and deduplicated list
        """
        results: dict[str, Any] = {
            "gainers": [],
            "losers": [],
            "volume_spikes": [],
            "trending": [],
            "new_listings": [],
            "movers": [],
            "scanned_at": time.time(),
        }

        # 1. Binance gainers/losers/volume spikes
        try:
            binance_data = self._scan_binance(min_volume)
            results["gainers"] = binance_data["gainers"]
            results["losers"] = binance_data["losers"]
            results["volume_spikes"] = binance_data["volume_spikes"]
            results["new_listings"] = binance_data["new_listings"]
        except Exception as e:
            logger.warning("opportunity_scan_binance_failed", error=str(e))

        # 2. CoinGecko trending
        try:
            results["trending"] = self._scan_coingecko_trending()
        except Exception as e:
            logger.warning("opportunity_scan_coingecko_failed", error=str(e))

        # 3. Build combined movers list
        results["movers"] = self._combine_movers(results)

        logger.info(
            "opportunity_scan_complete",
            gainers=len(results["gainers"]),
            losers=len(results["losers"]),
            volume_spikes=len(results["volume_spikes"]),
            trending=len(results["trending"]),
            total_movers=len(results["movers"]),
        )

        return results

    def _scan_binance(self, min_volume: float) -> dict[str, list]:
        """Scan Binance for gainers, losers, and volume spikes."""
        resp = self._client.get("https://data-api.binance.vision/api/v3/ticker/24hr")
        resp.raise_for_status()
        raw = resp.json()

        valid = []
        for data in raw:
            sym = data["symbol"]
            if not _is_valid_symbol(sym):
                continue
            quote_vol = float(data["quoteVolume"])
            if quote_vol < min_volume:
                continue
            valid.append({
                "symbol": sym,
                "price_change_pct": float(data["priceChangePercent"]),
                "quote_volume": quote_vol,
                "trades": int(data["count"]),
                "close": float(data["lastPrice"]),
                "high": float(data["highPrice"]),
                "low": float(data["lowPrice"]),
            })

        # Top gainers (biggest positive moves)
        gainers = sorted(valid, key=lambda x: x["price_change_pct"], reverse=True)[:20]

        # Top losers (biggest negative moves — mean reversion candidates)
        losers = sorted(valid, key=lambda x: x["price_change_pct"])[:15]

        # Volume spikes — coins with very high trade count relative to their volume tier
        # (high trade count = lots of activity, not just one big order)
        avg_trades = sum(d["trades"] for d in valid) / max(len(valid), 1)
        volume_spikes = [
            d for d in valid
            if d["trades"] > avg_trades * 3  # 3x average trade count
        ]
        volume_spikes.sort(key=lambda x: x["trades"], reverse=True)
        volume_spikes = volume_spikes[:15]

        # New listings (very high % change + relatively low volume = new or recently relisted)
        new_listings = [
            d for d in valid
            if abs(d["price_change_pct"]) > 20 and d["quote_volume"] < 5_000_000
        ]
        new_listings.sort(key=lambda x: abs(x["price_change_pct"]), reverse=True)
        new_listings = new_listings[:10]

        return {
            "gainers": gainers,
            "losers": losers,
            "volume_spikes": volume_spikes,
            "new_listings": new_listings,
        }

    def _scan_coingecko_trending(self) -> list[dict]:
        """Scan CoinGecko for trending coins."""
        try:
            resp = self._client.get("https://api.coingecko.com/api/v3/search/trending")
            resp.raise_for_status()
            data = resp.json()
            coins = data.get("coins", [])
            trending = []
            for coin in coins[:15]:
                item = coin.get("item", {})
                sym = item.get("symbol", "").upper()
                binance_sym = sym + "USDT"
                trending.append({
                    "symbol": binance_sym,
                    "name": item.get("name", ""),
                    "market_cap_rank": item.get("market_cap_rank"),
                    "price_btc": item.get("price_btc", 0),
                    "score": item.get("score", 0),
                    "source": "coingecko_trending",
                })
            return trending
        except Exception:
            return []

    def _combine_movers(self, results: dict) -> list[dict]:
        """Combine all sources into a deduplicated movers list with scores."""
        scored: dict[str, dict] = {}

        # Gainers: top movers get high scores
        for i, g in enumerate(results.get("gainers", [])[:15]):
            sym = g["symbol"]
            if sym not in scored:
                scored[sym] = {"symbol": sym, "score": 0, "reasons": [], "sources": set()}
            scored[sym]["score"] += max(1, 10 - i)  # Top gainer = 10 pts
            scored[sym]["reasons"].append(f"+{g['price_change_pct']:.1f}% 24h")
            scored[sym]["sources"].add("gainer")

        # Losers: potential mean-reversion (contrarian)
        for i, l in enumerate(results.get("losers", [])[:10]):
            sym = l["symbol"]
            if sym not in scored:
                scored[sym] = {"symbol": sym, "score": 0, "reasons": [], "sources": set()}
            scored[sym]["score"] += max(1, 5 - i)  # Lower score than gainers
            scored[sym]["reasons"].append(f"{l['price_change_pct']:.1f}% 24h (reversal?)")
            scored[sym]["sources"].add("loser")

        # Volume spikes
        for i, v in enumerate(results.get("volume_spikes", [])[:10]):
            sym = v["symbol"]
            if sym not in scored:
                scored[sym] = {"symbol": sym, "score": 0, "reasons": [], "sources": set()}
            scored[sym]["score"] += max(1, 8 - i)
            scored[sym]["reasons"].append(f"volume spike ({v['trades']:,} trades)")
            scored[sym]["sources"].add("volume_spike")

        # Trending
        for t in results.get("trending", []):
            sym = t["symbol"]
            if sym not in scored:
                scored[sym] = {"symbol": sym, "score": 0, "reasons": [], "sources": set()}
            scored[sym]["score"] += 6
            scored[sym]["reasons"].append(f"trending on CoinGecko")
            scored[sym]["sources"].add("trending")

        # New listings
        for n in results.get("new_listings", []):
            sym = n["symbol"]
            if sym not in scored:
                scored[sym] = {"symbol": sym, "score": 0, "reasons": [], "sources": set()}
            scored[sym]["score"] += 4
            scored[sym]["reasons"].append(f"new/relisted ({n['price_change_pct']:+.0f}%)")
            scored[sym]["sources"].add("new_listing")

        # Multi-source bonus: appearing in 2+ sources = stronger signal
        for data in scored.values():
            if len(data["sources"]) >= 3:
                data["score"] *= 2.0  # Triple-source = double score
            elif len(data["sources"]) >= 2:
                data["score"] *= 1.5  # Dual-source = 50% bonus

        # Sort by score descending
        movers = sorted(scored.values(), key=lambda x: -x["score"])

        # Convert sets to lists for JSON serialization
        for m in movers:
            m["sources"] = list(m["sources"])
            m["num_sources"] = len(m["sources"])

        return movers[:30]  # Top 30 opportunities
