"""Historical data layer -- drop-in replacement for DataLayer using stored data."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from syndicate.data.data_layer import CoinData, MarketSnapshot
from syndicate.data.historical import HistoricalDataStore
from syndicate.data.models import Candle
from syndicate.data.technical_indicators import compute_indicators, format_price_history

logger = structlog.get_logger()

# How many candles to load for each timeframe when building a snapshot.
# Matches the limits used in the live DataLayer (data_layer.py).
_CANDLE_LIMITS = {
    "1h": 200,
    "4h": 200,
    "1d": 200,
    "1w": 200,
}


class HistoricalDataLayer:
    """Drop-in replacement for DataLayer using stored historical data.

    Builds a MarketSnapshot from historical candle files rather than hitting
    the Binance API live.  Sentiment, macro, on-chain, and other enrichment
    fields are set to ``None`` -- agents that need them handle missing data
    gracefully.
    """

    def __init__(self, store: HistoricalDataStore) -> None:
        self._store = store

    def build_snapshot(
        self,
        symbols: list[str],
        as_of_date: datetime,
    ) -> MarketSnapshot:
        """Build MarketSnapshot from historical data as of a specific date.

        Loads candles up to *as_of_date*, computes indicators from the
        historical candle series.  For sentiment / macro / on-chain data the
        snapshot fields are left as ``None`` -- analysis agents already handle
        missing data gracefully.
        """
        snapshot = MarketSnapshot()
        t0 = time.monotonic()

        for symbol in symbols:
            coin = CoinData(symbol)

            # Load candles for each timeframe up to as_of_date
            for interval, limit in _CANDLE_LIMITS.items():
                candles = self._load_candles(symbol, interval, as_of_date, limit)
                if not candles:
                    continue

                # Compute indicators
                try:
                    indicators = compute_indicators(candles, symbol)
                except Exception:
                    indicators = None

                # Assign to the correct timeframe slot on CoinData
                if interval == "1h":
                    coin.indicators_1h = indicators
                elif interval == "4h":
                    coin.indicators_4h = indicators
                    if candles:
                        coin.price_history_4h = format_price_history(candles, last_n=20)
                elif interval == "1d":
                    coin.indicators_1d = indicators
                    if candles:
                        coin.price_history_1d = format_price_history(candles, last_n=20)
                elif interval == "1w":
                    coin.indicators_1w = indicators

            # Set current price from the latest available candle (prefer 1h, fall back to 4h, 1d)
            coin.current_price = self._get_latest_price(symbol, as_of_date)

            # Build a synthetic stats_24h dict from daily candles
            coin.stats_24h = self._build_stats_24h(symbol, as_of_date)

            snapshot.coins[symbol] = coin

        snapshot.fetch_times["historical"] = round(time.monotonic() - t0, 4)
        return snapshot

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_candles(
        self,
        symbol: str,
        interval: str,
        as_of: datetime,
        limit: int,
    ) -> list[Candle]:
        """Load up to *limit* candles ending at or before *as_of*."""
        candles = self._store.load(symbol, interval, end=as_of)
        # Take the last `limit` candles (oldest first, like live data)
        if len(candles) > limit:
            candles = candles[-limit:]
        return candles

    def _get_latest_price(self, symbol: str, as_of: datetime) -> float:
        """Get the most recent close price as of the given date."""
        for interval in ("1h", "4h", "1d"):
            candles = self._store.load(symbol, interval, end=as_of)
            if candles:
                return candles[-1].close
        return 0.0

    def _build_stats_24h(self, symbol: str, as_of: datetime) -> dict[str, Any]:
        """Build a synthetic 24h stats dict from hourly (or 4h) candles."""
        # Try 1h first for better granularity, fall back to 4h
        start_24h = as_of - timedelta(hours=24)
        candles = self._store.load(symbol, "1h", start=start_24h, end=as_of)
        if len(candles) < 2:
            candles = self._store.load(symbol, "4h", start=start_24h, end=as_of)
        if not candles:
            return {}

        opens = [c.open for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        closes = [c.close for c in candles]
        volumes = [c.volume for c in candles]

        open_price = opens[0]
        close_price = closes[-1]
        high_price = max(highs)
        low_price = min(lows)
        total_volume = sum(volumes)
        price_change = close_price - open_price
        price_change_pct = (price_change / open_price * 100) if open_price > 0 else 0.0

        return {
            "symbol": symbol,
            "price_change": price_change,
            "price_change_pct": round(price_change_pct, 4),
            "high": high_price,
            "low": low_price,
            "volume": total_volume,
            "quote_volume": total_volume * close_price,  # approximate
            "open": open_price,
            "close": close_price,
            "trades": 0,
        }
