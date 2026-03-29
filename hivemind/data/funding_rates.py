"""Fetch and store historical funding rates from Binance Futures."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

# Binance Futures funding rate API limit per request
_FUNDING_RATE_LIMIT = 1000

# Funding is paid every 8 hours (00:00, 08:00, 16:00 UTC)
_FUNDING_INTERVAL_MS = 8 * 3_600_000  # 28_800_000


def _parse_date(date_str: str) -> datetime:
    """Parse an ISO date string (YYYY-MM-DD) into a UTC datetime."""
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _dt_to_ms(dt: datetime) -> int:
    """Convert a datetime to Unix milliseconds."""
    return int(dt.timestamp() * 1000)


class FundingRateStore:
    """Fetch and store funding rate history for backtesting carry strategies.

    Binance Futures endpoint: GET /fapi/v1/fundingRate
    Parameters: symbol, startTime, endTime, limit=1000
    Base URL: https://fapi.binance.com (or https://testnet.binancefuture.com)

    Funding is paid every 8 hours (00:00, 08:00, 16:00 UTC).
    Rate is in decimal (0.0001 = 0.01%).
    """

    def __init__(self, storage_dir: str = "data/funding_rates") -> None:
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
    ) -> None:
        """Paginate through Binance funding rate API.

        GET https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&startTime=...&limit=1000
        Returns: [{"symbol":"BTCUSDT","fundingTime":1700000000000,
                   "fundingRate":"0.00010000","markPrice":"37000.00"}, ...]

        Args:
            symbols: e.g. ["BTCUSDT", "ETHUSDT"]
            start_date: ISO format "2025-03-01"
            end_date: ISO format "2026-03-01"
        """
        start_dt = _parse_date(start_date)
        end_dt = _parse_date(end_date)
        start_ms = _dt_to_ms(start_dt)
        end_ms = _dt_to_ms(end_dt)

        for symbol in symbols:
            logger.info(
                "funding_rate_fetch_start",
                symbol=symbol,
                start=start_date,
                end=end_date,
            )
            records = self._paginated_fetch(symbol, start_ms, end_ms)
            self._store(symbol, records)
            logger.info(
                "funding_rate_fetch_done",
                symbol=symbol,
                records=len(records),
            )

    def load(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[dict]:
        """Load funding rates from storage.

        Returns:
            List of {"timestamp": datetime, "rate": float, "mark_price": float}
            sorted by timestamp ascending.
        """
        path = self._file_path(symbol)
        if not path.exists():
            logger.warning("funding_rate_file_missing", path=str(path))
            return []

        raw_list: list[dict[str, Any]] = json.loads(path.read_text())

        # Filter by date range
        if start is not None:
            start_ms = _dt_to_ms(start)
            raw_list = [r for r in raw_list if r["funding_time"] >= start_ms]
        if end is not None:
            end_ms = _dt_to_ms(end)
            raw_list = [r for r in raw_list if r["funding_time"] <= end_ms]

        return [
            {
                "timestamp": datetime.fromtimestamp(
                    r["funding_time"] / 1000, tz=timezone.utc
                ),
                "rate": r["funding_rate"],
                "mark_price": r["mark_price"],
            }
            for r in raw_list
        ]

    def get_latest_rate(
        self,
        symbol: str,
        as_of: datetime,
    ) -> float | None:
        """Get the most recent funding rate on or before `as_of`.

        Returns the funding rate as a decimal (e.g. 0.0001 = 0.01%), or None
        if no data is available.
        """
        path = self._file_path(symbol)
        if not path.exists():
            return None

        as_of_ms = _dt_to_ms(as_of)
        raw_list: list[dict[str, Any]] = json.loads(path.read_text())

        # Find the latest record on or before as_of
        best: dict[str, Any] | None = None
        for r in raw_list:
            if r["funding_time"] <= as_of_ms:
                if best is None or r["funding_time"] > best["funding_time"]:
                    best = r

        if best is None:
            return None
        return best["funding_rate"]

    def list_available(self) -> list[str]:
        """List symbols with stored funding rate data."""
        if not self._dir.exists():
            return []
        return [
            f.stem.upper()
            for f in sorted(self._dir.iterdir())
            if f.suffix == ".json"
        ]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _paginated_fetch(
        self, symbol: str, start_ms: int, end_ms: int
    ) -> list[dict[str, Any]]:
        """Fetch all funding rates between start_ms and end_ms, paginating."""
        all_records: list[dict[str, Any]] = []
        current_start = start_ms

        # Try Binance Futures mainnet first, fall back to testnet
        base_url = "https://fapi.binance.com"
        url = f"{base_url}/fapi/v1/fundingRate"

        with httpx.Client(timeout=30.0) as client:
            while current_start < end_ms:
                params: dict[str, Any] = {
                    "symbol": symbol,
                    "startTime": current_start,
                    "endTime": end_ms,
                    "limit": _FUNDING_RATE_LIMIT,
                }
                try:
                    resp = client.get(url, params=params)
                    resp.raise_for_status()
                except httpx.HTTPStatusError:
                    # Fallback to testnet
                    fallback_url = "https://testnet.binancefuture.com/fapi/v1/fundingRate"
                    if url != fallback_url:
                        logger.info(
                            "funding_rate_fallback",
                            original=url,
                            fallback=fallback_url,
                        )
                        url = fallback_url
                        resp = client.get(url, params=params)
                        resp.raise_for_status()
                    else:
                        raise

                raw_records = resp.json()

                if not raw_records:
                    break

                for raw in raw_records:
                    parsed = {
                        "funding_time": raw["fundingTime"],
                        "funding_rate": float(raw["fundingRate"]),
                        "mark_price": float(raw.get("markPrice", 0)),
                    }
                    # Deduplicate by funding time
                    if (
                        not all_records
                        or parsed["funding_time"] > all_records[-1]["funding_time"]
                    ):
                        all_records.append(parsed)

                # Advance past the last returned record
                last_time = raw_records[-1]["fundingTime"]
                current_start = last_time + _FUNDING_INTERVAL_MS

                # If we got fewer than the limit, we've reached the end
                if len(raw_records) < _FUNDING_RATE_LIMIT:
                    break

                # Respect rate limits
                time.sleep(0.1)

        return all_records

    def _store(self, symbol: str, records: list[dict[str, Any]]) -> None:
        """Write funding rate records to JSON, merging with existing data."""
        path = self._file_path(symbol)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Merge with existing data
        existing: list[dict[str, Any]] = []
        if path.exists():
            try:
                existing = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                existing = []

        # Deduplicate by funding_time
        existing_times = {r["funding_time"] for r in existing}
        merged = list(existing)
        for r in records:
            if r["funding_time"] not in existing_times:
                merged.append(r)
                existing_times.add(r["funding_time"])

        # Sort by time ascending
        merged.sort(key=lambda r: r["funding_time"])

        path.write_text(json.dumps(merged, separators=(",", ":")))

    def _file_path(self, symbol: str) -> Path:
        """Return the storage path for a symbol's funding rates."""
        return self._dir / f"{symbol.upper()}.json"
