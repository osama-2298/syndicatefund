"""
CoinGecko API client — free tier, no auth required.

Provides: market cap, supply data, price changes over multiple timeframes,
ATH/ATL distances, trending coins, global market metrics, BTC dominance.

Rate limit: ~10-30 req/min on free tier. We cache aggressively.
"""

from __future__ import annotations

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

BASE_URL = "https://api.coingecko.com/api/v3"

# Binance symbol -> CoinGecko ID mapping for top coins
SYMBOL_TO_GECKO_ID: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "MATIC": "matic-network",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "NEAR": "near",
    "APT": "aptos",
    "SUI": "sui",
    "OP": "optimism",
    "ARB": "arbitrum",
    "SEI": "sei-network",
    "FET": "fetch-ai",
    "RENDER": "render-token",
    "FIL": "filecoin",
    "AAVE": "aave",
    "MKR": "maker",
    "CRV": "curve-dao-token",
    "PEPE": "pepe",
    "SHIB": "shiba-inu",
    "FLOKI": "floki",
    "BONK": "bonk",
    "WIF": "dogwifcoin",
    "TAO": "bittensor",
    "AR": "arweave",
    "ZEC": "zcash",
    "PENDLE": "pendle",
    "STX": "blockstack",
    "INJ": "injective-protocol",
    "TIA": "celestia",
}


import threading

_dynamic_gecko_cache: dict[str, str | None] = {}
_gecko_cache_lock = threading.Lock()


def _search_gecko_id(symbol: str) -> str | None:
    """One-time CoinGecko search API call per unknown symbol."""
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{BASE_URL}/search", params={"query": symbol.lower()})
            if resp.status_code == 429:
                return None
            resp.raise_for_status()
            for coin in resp.json().get("coins", []):
                if coin.get("symbol", "").upper() == symbol.upper():
                    return coin["id"]
    except Exception:
        pass
    return None


def _symbol_to_id(symbol: str) -> str | None:
    """Convert Binance symbol (e.g., BTCUSDT) to CoinGecko ID.
    Falls back to search API for unmapped coins, with session cache."""
    base = symbol.replace("USDT", "").replace("BUSD", "")
    # Check static map first
    gid = SYMBOL_TO_GECKO_ID.get(base)
    if gid:
        return gid
    # Check dynamic cache (thread-safe)
    with _gecko_cache_lock:
        if base in _dynamic_gecko_cache:
            return _dynamic_gecko_cache[base]
    # Search API fallback (outside lock — network I/O)
    gid = _search_gecko_id(base)
    with _gecko_cache_lock:
        _dynamic_gecko_cache[base] = gid
    if gid:
        logger.info("coingecko_dynamic_id_resolved", symbol=base, gecko_id=gid)
    return gid


class CoinGeckoClient:
    """Synchronous CoinGecko free API client."""

    def __init__(self) -> None:
        self._client = httpx.Client(
            base_url=BASE_URL,
            timeout=15.0,
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> CoinGeckoClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_coins_batch(self, symbols: list[str]) -> dict[str, dict]:
        """
        Batch fetch coin data using /coins/markets endpoint.
        ONE API call for up to 250 coins — replaces 12+ individual calls.
        Returns dict of symbol -> coin data.
        """
        gecko_ids = []
        id_to_sym: dict[str, str] = {}
        for sym in symbols:
            gid = _symbol_to_id(sym)
            if gid:
                gecko_ids.append(gid)
                id_to_sym[gid] = sym

        if not gecko_ids:
            return {}

        resp = self._client.get(
            "/coins/markets",
            params={
                "vs_currency": "usd",
                "ids": ",".join(gecko_ids),
                "per_page": 250,
                "sparkline": "false",
                "price_change_percentage": "24h,7d,14d,30d,200d,1y",
            },
        )
        if resp.status_code == 429:
            logger.warning("coingecko_batch_rate_limited")
            return {}
        resp.raise_for_status()
        data = resp.json()

        results = {}
        for coin in data:
            gid = coin.get("id", "")
            sym = id_to_sym.get(gid)
            if sym is None:
                continue

            # Build price_changes dict, filtering None values
            price_changes = {}
            for period, key in [
                ("24h", "price_change_percentage_24h_in_currency"),
                ("7d", "price_change_percentage_7d_in_currency"),
                ("14d", "price_change_percentage_14d_in_currency"),
                ("30d", "price_change_percentage_30d_in_currency"),
                ("200d", "price_change_percentage_200d_in_currency"),
                ("1y", "price_change_percentage_1y_in_currency"),
            ]:
                val = coin.get(key)
                if val is None:
                    val = coin.get(f"price_change_percentage_{period}", 0)
                if val is not None:
                    price_changes[period] = round(float(val), 2)

            results[sym] = {
                "symbol": sym,
                "name": coin.get("name", ""),
                "market_cap_rank": coin.get("market_cap_rank"),
                "current_price_usd": coin.get("current_price", 0),
                "market_cap_usd": coin.get("market_cap", 0),
                "fully_diluted_valuation_usd": coin.get("fully_diluted_valuation", 0),
                "total_volume_usd": coin.get("total_volume", 0),
                "circulating_supply": coin.get("circulating_supply"),
                "total_supply": coin.get("total_supply"),
                "max_supply": coin.get("max_supply"),
                "price_changes": price_changes,
                "ath_usd": coin.get("ath", 0),
                "ath_distance_pct": round(coin.get("ath_change_percentage", 0), 2),
                "atl_usd": coin.get("atl", 0),
                "atl_distance_pct": round(coin.get("atl_change_percentage", 0), 2),
                "sentiment_votes_up_pct": 0,
                "sentiment_votes_down_pct": 0,
                "watchlist_users": 0,
            }

        return results

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_global(self) -> dict:
        """
        Get global crypto market data.
        Returns: total market cap, BTC dominance, ETH dominance, total volume,
        market cap change 24h, active cryptocurrencies count.
        """
        resp = self._client.get("/global")
        resp.raise_for_status()
        data = resp.json()["data"]

        btc_dom = data.get("market_cap_percentage", {}).get("btc", 0)
        eth_dom = data.get("market_cap_percentage", {}).get("eth", 0)
        total_mcap = data.get("total_market_cap", {}).get("usd", 0)
        total_vol = data.get("total_volume", {}).get("usd", 0)
        mcap_change = data.get("market_cap_change_percentage_24h_usd", 0)

        return {
            "total_market_cap_usd": total_mcap,
            "total_volume_usd": total_vol,
            "btc_dominance": round(btc_dom, 2),
            "eth_dominance": round(eth_dom, 2),
            "market_cap_change_24h_pct": round(mcap_change, 2),
            "active_cryptocurrencies": data.get("active_cryptocurrencies", 0),
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_coin(self, symbol: str) -> dict | None:
        """
        Get detailed data for a specific coin.
        Returns market data, supply info, and multi-timeframe price changes.
        """
        gecko_id = _symbol_to_id(symbol)
        if gecko_id is None:
            return None

        resp = self._client.get(
            f"/coins/{gecko_id}",
            params={
                "localization": "false",
                "tickers": "false",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "false",
            },
        )
        if resp.status_code == 429:
            logger.warning("coingecko_rate_limited", symbol=symbol)
            return None
        resp.raise_for_status()
        data = resp.json()

        md = data.get("market_data", {})

        # Multi-timeframe price changes
        price_changes = {}
        for period in ["24h", "7d", "14d", "30d", "60d", "200d", "1y"]:
            key = f"price_change_percentage_{period}"
            val = md.get(key)
            if val is not None:
                price_changes[period] = round(val, 2)

        # ATH/ATL distance
        ath_usd = md.get("ath", {}).get("usd", 0)
        atl_usd = md.get("atl", {}).get("usd", 0)
        current_price = md.get("current_price", {}).get("usd", 0)

        ath_distance_pct = md.get("ath_change_percentage", {}).get("usd", 0)
        atl_distance_pct = md.get("atl_change_percentage", {}).get("usd", 0)

        return {
            "symbol": symbol,
            "name": data.get("name", ""),
            "market_cap_rank": data.get("market_cap_rank"),
            "current_price_usd": current_price,
            "market_cap_usd": md.get("market_cap", {}).get("usd", 0),
            "fully_diluted_valuation_usd": md.get("fully_diluted_valuation", {}).get("usd", 0),
            "total_volume_usd": md.get("total_volume", {}).get("usd", 0),
            # Supply
            "circulating_supply": md.get("circulating_supply"),
            "total_supply": md.get("total_supply"),
            "max_supply": md.get("max_supply"),
            # Price changes
            "price_changes": price_changes,
            # ATH/ATL
            "ath_usd": ath_usd,
            "ath_distance_pct": round(ath_distance_pct, 2),
            "atl_usd": atl_usd,
            "atl_distance_pct": round(atl_distance_pct, 2),
            # Sentiment
            "sentiment_votes_up_pct": data.get("sentiment_votes_up_percentage", 0),
            "sentiment_votes_down_pct": data.get("sentiment_votes_down_percentage", 0),
            "watchlist_users": data.get("watchlist_portfolio_users", 0),
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_trending(self) -> list[dict]:
        """Get trending coins on CoinGecko (social/search momentum)."""
        resp = self._client.get("/search/trending")
        resp.raise_for_status()
        data = resp.json()

        trending = []
        for item in data.get("coins", []):
            coin = item.get("item", {})
            coin_data = coin.get("data", {})
            trending.append({
                "name": coin.get("name", ""),
                "symbol": coin.get("symbol", ""),
                "market_cap_rank": coin.get("market_cap_rank"),
                "price_change_24h_pct": coin_data.get("price_change_percentage_24h", {}).get("usd", 0),
            })

        return trending
