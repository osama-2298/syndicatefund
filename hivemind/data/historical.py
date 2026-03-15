"""Historical data storage -- fetch and store Binance klines for backtesting."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import structlog

from hivemind.data.models import Candle

logger = structlog.get_logger()

# Binance kline API limit per request
_BINANCE_KLINE_LIMIT = 1000

# Map interval strings to their duration in milliseconds
_INTERVAL_MS: dict[str, int] = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "2h": 7_200_000,
    "4h": 14_400_000,
    "6h": 21_600_000,
    "8h": 28_800_000,
    "12h": 43_200_000,
    "1d": 86_400_000,
    "3d": 259_200_000,
    "1w": 604_800_000,
}


def _parse_date(date_str: str) -> datetime:
    """Parse an ISO date string (YYYY-MM-DD) into a UTC datetime."""
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _dt_to_ms(dt: datetime) -> int:
    """Convert a datetime to Unix milliseconds."""
    return int(dt.timestamp() * 1000)


def _parse_raw_kline(raw: list) -> dict[str, Any]:
    """Parse a single raw Binance kline array into a serialisable dict."""
    return {
        "timestamp": raw[0],  # open time in ms
        "open": float(raw[1]),
        "high": float(raw[2]),
        "low": float(raw[3]),
        "close": float(raw[4]),
        "volume": float(raw[5]),
        "close_time": raw[6],
    }


def _raw_to_candle(raw: dict[str, Any]) -> Candle:
    """Convert a stored kline dict to a Candle model."""
    return Candle(
        timestamp=datetime.fromtimestamp(raw["timestamp"] / 1000, tz=timezone.utc),
        open=raw["open"],
        high=raw["high"],
        low=raw["low"],
        close=raw["close"],
        volume=raw["volume"],
    )


class HistoricalDataStore:
    """Fetch and store historical Binance klines for backtesting.

    Stores data as JSON files (one per symbol/interval) in data/historical/.
    """

    def __init__(self, storage_dir: str = "data/historical") -> None:
        self._dir = Path(storage_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_and_store(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
        intervals: list[str] | None = None,
    ) -> None:
        """Paginate through Binance kline API, store as JSON.

        Args:
            symbols: e.g. ["BTCUSDT", "ETHUSDT"]
            start_date: ISO format "2025-03-01"
            end_date: ISO format "2026-03-01"
            intervals: e.g. ["1h", "4h", "1d"]. Defaults to ["1h", "4h", "1d"].
        """
        if intervals is None:
            intervals = ["1h", "4h", "1d"]

        start_dt = _parse_date(start_date)
        end_dt = _parse_date(end_date)
        start_ms = _dt_to_ms(start_dt)
        end_ms = _dt_to_ms(end_dt)

        for symbol in symbols:
            for interval in intervals:
                logger.info(
                    "historical_fetch_start",
                    symbol=symbol,
                    interval=interval,
                    start=start_date,
                    end=end_date,
                )
                candles = self._paginated_fetch(symbol, interval, start_ms, end_ms)
                self._store(symbol, interval, candles)
                logger.info(
                    "historical_fetch_done",
                    symbol=symbol,
                    interval=interval,
                    candles=len(candles),
                )

    def load(
        self,
        symbol: str,
        interval: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Candle]:
        """Load stored candles for a date range."""
        path = self._file_path(symbol, interval)
        if not path.exists():
            logger.warning("historical_file_missing", path=str(path))
            return []

        raw_list: list[dict[str, Any]] = json.loads(path.read_text())

        # Filter by date range
        if start is not None:
            start_ms = _dt_to_ms(start)
            raw_list = [r for r in raw_list if r["timestamp"] >= start_ms]
        if end is not None:
            end_ms = _dt_to_ms(end)
            raw_list = [r for r in raw_list if r["timestamp"] <= end_ms]

        return [_raw_to_candle(r) for r in raw_list]

    def list_available(self) -> dict[str, list[str]]:
        """List available symbols and their intervals.

        Returns:
            {symbol: [interval1, interval2, ...]}
        """
        result: dict[str, list[str]] = {}
        if not self._dir.exists():
            return result

        for symbol_dir in sorted(self._dir.iterdir()):
            if not symbol_dir.is_dir():
                continue
            symbol = symbol_dir.name
            intervals = []
            for f in sorted(symbol_dir.iterdir()):
                if f.suffix == ".json":
                    intervals.append(f.stem)
            if intervals:
                result[symbol] = intervals
        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _paginated_fetch(
        self, symbol: str, interval: str, start_ms: int, end_ms: int
    ) -> list[dict[str, Any]]:
        """Fetch all klines between start_ms and end_ms by paginating in chunks of 1000."""
        all_candles: list[dict[str, Any]] = []
        current_start = start_ms
        interval_ms = _INTERVAL_MS.get(interval, 3_600_000)

        # Use configured base URL, then Binance Vision (not geo-blocked), then api.binance.com
        try:
            from hivemind.config import settings
            base_url = settings.binance_base_url.rstrip("/")
        except Exception:
            base_url = "https://data-api.binance.vision"

        kline_url = f"{base_url}/api/v3/klines"

        with httpx.Client(timeout=30.0) as client:
            while current_start < end_ms:
                params: dict[str, Any] = {
                    "symbol": symbol,
                    "interval": interval,
                    "startTime": current_start,
                    "endTime": end_ms,
                    "limit": _BINANCE_KLINE_LIMIT,
                }
                try:
                    resp = client.get(kline_url, params=params)
                    resp.raise_for_status()
                except httpx.HTTPStatusError:
                    # Fallback to Binance Vision data API (not geo-blocked)
                    fallback_url = "https://data-api.binance.vision/api/v3/klines"
                    if kline_url != fallback_url:
                        logger.info("historical_fallback_to_vision", original=kline_url)
                        kline_url = fallback_url
                        resp = client.get(kline_url, params=params)
                        resp.raise_for_status()
                    else:
                        raise
                raw_klines = resp.json()

                if not raw_klines:
                    break

                for raw in raw_klines:
                    parsed = _parse_raw_kline(raw)
                    # Deduplicate by open time
                    if not all_candles or parsed["timestamp"] > all_candles[-1]["timestamp"]:
                        all_candles.append(parsed)

                # Advance past the last returned candle
                last_open_time = raw_klines[-1][0]
                current_start = last_open_time + interval_ms

                # If we got fewer than the limit, we've reached the end
                if len(raw_klines) < _BINANCE_KLINE_LIMIT:
                    break

                # Respect rate limits: Binance allows 1200 req/min on public endpoints
                time.sleep(0.1)

        return all_candles

    def _store(self, symbol: str, interval: str, candles: list[dict[str, Any]]) -> None:
        """Write candles to a JSON file, merging with any existing data."""
        path = self._file_path(symbol, interval)
        path.parent.mkdir(parents=True, exist_ok=True)

        # If a file already exists, merge (avoiding duplicates by timestamp)
        existing: list[dict[str, Any]] = []
        if path.exists():
            try:
                existing = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                existing = []

        # Build a set of existing timestamps for O(1) dedup
        existing_ts = {c["timestamp"] for c in existing}
        merged = list(existing)
        for c in candles:
            if c["timestamp"] not in existing_ts:
                merged.append(c)
                existing_ts.add(c["timestamp"])

        # Sort by timestamp ascending
        merged.sort(key=lambda c: c["timestamp"])

        path.write_text(json.dumps(merged, separators=(",", ":")))

    def _file_path(self, symbol: str, interval: str) -> Path:
        """Return the storage path for a symbol/interval pair."""
        return self._dir / symbol.upper() / f"{interval}.json"
