"""
Binance market data client.

Fetches OHLCV candles, ticker prices, and order book data from Binance public API.
No API key needed for read-only market data.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from hivemind.data.models import Candle, TickerPrice

logger = structlog.get_logger()

# Binance kline intervals
VALID_INTERVALS = {
    "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "8h", "12h",
    "1d", "3d", "1w", "1M",
}


class BinanceClient:
    """
    Synchronous Binance public API client.
    Uses only public endpoints — no authentication required for market data.
    """

    def __init__(self, base_url: str | None = None) -> None:
        from hivemind.config import settings
        self._base_url = base_url or settings.binance_base_url
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=30.0,
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> BinanceClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # ─── Price ───

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_price(self, symbol: str) -> TickerPrice:
        """Get current price for a symbol (e.g. 'BTCUSDT')."""
        resp = self._client.get("/api/v3/ticker/price", params={"symbol": symbol})
        resp.raise_for_status()
        data = resp.json()
        return TickerPrice(
            symbol=data["symbol"],
            price=float(data["price"]),
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_prices(self, symbols: list[str] | None = None) -> list[TickerPrice]:
        """Get current prices for multiple symbols, or all symbols if none specified."""
        params = {}
        if symbols:
            # Binance accepts JSON array for multiple symbols
            import json
            params["symbols"] = json.dumps(symbols)

        resp = self._client.get("/api/v3/ticker/price", params=params)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data:
            if symbols is None or item["symbol"] in symbols:
                results.append(
                    TickerPrice(symbol=item["symbol"], price=float(item["price"]))
                )
        return results

    # ─── Klines (OHLCV) ───

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_klines(
        self,
        symbol: str,
        interval: str = "4h",
        limit: int = 100,
    ) -> list[Candle]:
        """
        Fetch OHLCV candlestick data.

        Args:
            symbol: Trading pair (e.g. 'BTCUSDT')
            interval: Candle interval (e.g. '1h', '4h', '1d')
            limit: Number of candles (max 1000)

        Returns:
            List of Candle objects, oldest first.
        """
        if interval not in VALID_INTERVALS:
            raise ValueError(f"Invalid interval '{interval}'. Must be one of {VALID_INTERVALS}")
        if limit < 1 or limit > 1000:
            raise ValueError(f"Limit must be 1-1000, got {limit}")

        resp = self._client.get(
            "/api/v3/klines",
            params={
                "symbol": symbol,
                "interval": interval,
                "limit": limit,
            },
        )
        resp.raise_for_status()
        raw_klines = resp.json()

        candles = []
        for k in raw_klines:
            candles.append(
                Candle(
                    timestamp=datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc),
                    open=float(k[1]),
                    high=float(k[2]),
                    low=float(k[3]),
                    close=float(k[4]),
                    volume=float(k[5]),
                )
            )

        logger.info(
            "fetched_klines",
            symbol=symbol,
            interval=interval,
            count=len(candles),
        )
        return candles

    # ─── 24h Ticker Stats ───

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_24h_stats(self, symbol: str) -> dict:
        """Get 24-hour rolling window price change statistics."""
        resp = self._client.get("/api/v3/ticker/24hr", params={"symbol": symbol})
        resp.raise_for_status()
        data = resp.json()
        return {
            "symbol": data["symbol"],
            "price_change": float(data["priceChange"]),
            "price_change_pct": float(data["priceChangePercent"]),
            "high": float(data["highPrice"]),
            "low": float(data["lowPrice"]),
            "volume": float(data["volume"]),
            "quote_volume": float(data["quoteVolume"]),
            "open": float(data["openPrice"]),
            "close": float(data["lastPrice"]),
            "trades": int(data["count"]),
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_all_24h_stats(self, quote_asset: str = "USDT", min_volume: float = 0) -> list[dict]:
        """
        Fetch 24h stats for ALL symbols in one API call, filtered to quote asset.
        Returns list sorted by quote volume descending.
        """
        resp = self._client.get("/api/v3/ticker/24hr")
        resp.raise_for_status()
        raw = resp.json()

        results = []
        for data in raw:
            symbol = data["symbol"]
            if not symbol.endswith(quote_asset):
                continue
            quote_volume = float(data["quoteVolume"])
            if quote_volume < min_volume:
                continue
            results.append({
                "symbol": symbol,
                "price_change": float(data["priceChange"]),
                "price_change_pct": float(data["priceChangePercent"]),
                "high": float(data["highPrice"]),
                "low": float(data["lowPrice"]),
                "volume": float(data["volume"]),
                "quote_volume": quote_volume,
                "open": float(data["openPrice"]),
                "close": float(data["lastPrice"]),
                "trades": int(data["count"]),
            })

        results.sort(key=lambda x: x["quote_volume"], reverse=True)
        logger.info("fetched_all_24h_stats", count=len(results), quote_asset=quote_asset)
        return results

    # ─── Order Book Depth ───

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_order_book(self, symbol: str, limit: int = 20) -> dict:
        """
        Get order book depth — bid/ask pressure analysis.
        Returns buy/sell volume imbalance which signals short-term direction.
        """
        resp = self._client.get(
            "/api/v3/depth",
            params={"symbol": symbol, "limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()

        bids = data.get("bids", [])
        asks = data.get("asks", [])

        # Calculate total bid/ask volume
        bid_volume = sum(float(b[1]) for b in bids)
        ask_volume = sum(float(a[1]) for a in asks)

        # Bid/ask value in USD
        if bids and asks:
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            spread = best_ask - best_bid
            spread_pct = (spread / best_bid) * 100 if best_bid > 0 else 0
            bid_value = sum(float(b[0]) * float(b[1]) for b in bids)
            ask_value = sum(float(a[0]) * float(a[1]) for a in asks)
        else:
            best_bid = best_ask = spread = spread_pct = 0
            bid_value = ask_value = 0

        total_value = bid_value + ask_value
        bid_ratio = bid_value / max(total_value, 1)

        # Buy/sell pressure assessment
        if bid_ratio > 0.65:
            pressure = "STRONG_BUY_PRESSURE"
        elif bid_ratio > 0.55:
            pressure = "MODERATE_BUY_PRESSURE"
        elif bid_ratio > 0.45:
            pressure = "BALANCED"
        elif bid_ratio > 0.35:
            pressure = "MODERATE_SELL_PRESSURE"
        else:
            pressure = "STRONG_SELL_PRESSURE"

        return {
            "symbol": symbol,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": round(spread, 8),
            "spread_pct": round(spread_pct, 6),
            "bid_volume": round(bid_volume, 4),
            "ask_volume": round(ask_volume, 4),
            "bid_value_usd": round(bid_value, 2),
            "ask_value_usd": round(ask_value, 2),
            "bid_ratio": round(bid_ratio, 3),
            "pressure": pressure,
            "depth_levels": limit,
        }

    # ─── Exchange Info ───

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_tradeable_symbols(self) -> list[str]:
        """Get all USDT trading pairs that are currently active."""
        resp = self._client.get("/api/v3/exchangeInfo")
        resp.raise_for_status()
        data = resp.json()

        symbols = []
        for s in data["symbols"]:
            if (
                s["status"] == "TRADING"
                and s["quoteAsset"] == "USDT"
                and s["isSpotTradingAllowed"]
            ):
                symbols.append(s["symbol"])

        logger.info("fetched_tradeable_symbols", count=len(symbols))
        return sorted(symbols)
