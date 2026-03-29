"""
Download 5 years of OHLCV candle data from Binance public API for top 50 crypto coins.

Stores compressed CSV files at: data/historical/{SYMBOL}/{timeframe}.csv.gz
Supports resume — only fetches new candles since last stored timestamp.

Usage:
    python -m hivemind.research.data.historical_downloader
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://data-api.binance.vision/api/v3"
KLINES_ENDPOINT = f"{BASE_URL}/klines"
TICKER_ENDPOINT = f"{BASE_URL}/ticker/24hr"

TIMEFRAMES = ["1h", "4h", "1d", "1w"]

# Binance returns at most 1000 candles per request.
MAX_CANDLES_PER_REQUEST = 1000

# Concurrency / rate-limiting
MAX_CONCURRENT_REQUESTS = 10
BATCH_DELAY_SECONDS = 0.1

# How far back to look (5 years in milliseconds).
FIVE_YEARS_MS = 5 * 365.25 * 24 * 60 * 60 * 1000

TOP_N_SYMBOLS = 50

# Where data lives — relative to repo root.
DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "historical"

# Timeframe -> interval duration in milliseconds (used for pagination math).
TIMEFRAME_MS: dict[str, int] = {
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
    "1w": 7 * 24 * 60 * 60 * 1000,
}

OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _ms_to_dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def _parse_klines(raw: list[list[Any]]) -> pd.DataFrame:
    """Convert Binance kline response rows into a clean DataFrame.

    Binance returns 12-element arrays per candle.  We only keep:
        [0] open_time, [1] open, [2] high, [3] low, [4] close, [5] volume
    """
    if not raw:
        return pd.DataFrame(columns=OHLCV_COLUMNS)

    rows = []
    for k in raw:
        rows.append(
            {
                "timestamp": pd.Timestamp(_ms_to_dt(int(k[0]))),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            }
        )
    df = pd.DataFrame(rows, columns=OHLCV_COLUMNS)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


def _load_existing(path: Path) -> pd.DataFrame | None:
    """Load existing compressed CSV if present.  Returns None if missing / corrupt."""
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, compression="gzip", parse_dates=["timestamp"])
        if df.empty:
            return None
        # Ensure timezone-aware timestamps for comparison.
        if df["timestamp"].dt.tz is None:
            df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype("float64")
        return df
    except Exception as exc:
        print(f"  [warn] Could not load {path}: {exc}. Will re-download.")
        return None


def _save(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, compression="gzip")


# ---------------------------------------------------------------------------
# Network layer
# ---------------------------------------------------------------------------


async def fetch_top_symbols(client: httpx.AsyncClient) -> list[str]:
    """Return top N USDT trading pairs sorted by 24h quote volume descending."""
    print("Fetching top symbols by 24h USDT volume ...")
    resp = await client.get(TICKER_ENDPOINT, timeout=30)
    resp.raise_for_status()
    tickers = resp.json()

    # Filter to USDT pairs only and sort by quoteVolume descending.
    usdt_tickers = [
        t for t in tickers
        if t["symbol"].endswith("USDT")
        and not t["symbol"].startswith("USDT")       # exclude USDTXXX pairs
        and "BEAR" not in t["symbol"]                 # exclude leveraged tokens
        and "BULL" not in t["symbol"]
        and "UP" not in t["symbol"].replace("USDT", "")[-2:]
        and "DOWN" not in t["symbol"]
    ]

    usdt_tickers.sort(key=lambda t: float(t["quoteVolume"]), reverse=True)

    symbols = [t["symbol"] for t in usdt_tickers[:TOP_N_SYMBOLS]]
    print(f"Selected {len(symbols)} symbols: {', '.join(symbols[:10])}, ...")
    return symbols


async def _fetch_klines_page(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
) -> list[list[Any]]:
    """Fetch a single page of klines, respecting the concurrency semaphore."""
    params: dict[str, Any] = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": MAX_CANDLES_PER_REQUEST,
    }
    async with semaphore:
        resp = await client.get(KLINES_ENDPOINT, params=params, timeout=30)
        resp.raise_for_status()
        await asyncio.sleep(BATCH_DELAY_SECONDS)
        return resp.json()


async def download_klines(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
) -> pd.DataFrame:
    """Download all klines for a symbol/interval between start_ms and end_ms.

    Paginates forward in time, fetching up to 1000 candles per request.
    """
    all_rows: list[list[Any]] = []
    cursor = start_ms
    interval_ms = TIMEFRAME_MS[interval]
    page = 0

    while cursor < end_ms:
        page += 1
        data = await _fetch_klines_page(
            client, semaphore, symbol, interval, cursor, end_ms
        )

        if not data:
            break

        all_rows.extend(data)

        # Move cursor past the last candle we received to avoid duplicates.
        last_open_time = int(data[-1][0])
        new_cursor = last_open_time + interval_ms

        # Safety: if cursor didn't advance, break to avoid infinite loop.
        if new_cursor <= cursor:
            break
        cursor = new_cursor

        # If Binance returned fewer than limit, we've reached the end.
        if len(data) < MAX_CANDLES_PER_REQUEST:
            break

    return _parse_klines(all_rows)


# ---------------------------------------------------------------------------
# Per-symbol download orchestration
# ---------------------------------------------------------------------------


async def download_symbol_timeframe(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    symbol: str,
    interval: str,
) -> dict[str, Any]:
    """Download (or update) a single symbol+timeframe and save to disk.

    Returns a stats dict with candle counts.
    """
    path = DATA_DIR / symbol / f"{interval}.csv.gz"
    now_ms = _now_ms()
    five_years_ago_ms = int(now_ms - FIVE_YEARS_MS)

    existing = _load_existing(path)

    if existing is not None and not existing.empty:
        last_ts = existing["timestamp"].max()
        # Convert to ms; start just after last candle to avoid overlap.
        resume_ms = int(last_ts.timestamp() * 1000) + TIMEFRAME_MS[interval]
        if resume_ms >= now_ms:
            return {
                "symbol": symbol,
                "interval": interval,
                "status": "up-to-date",
                "existing": len(existing),
                "new": 0,
            }
        start_ms = resume_ms
        print(f"  {symbol}/{interval}: resuming from {last_ts.strftime('%Y-%m-%d %H:%M')} ({len(existing)} existing candles)")
    else:
        existing = None
        start_ms = five_years_ago_ms
        print(f"  {symbol}/{interval}: full download from {_ms_to_dt(start_ms).strftime('%Y-%m-%d')}")

    new_df = await download_klines(client, semaphore, symbol, interval, start_ms, now_ms)

    if new_df.empty and existing is None:
        return {
            "symbol": symbol,
            "interval": interval,
            "status": "no-data",
            "existing": 0,
            "new": 0,
        }

    if existing is not None and not new_df.empty:
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined.drop_duplicates(subset=["timestamp"], keep="last", inplace=True)
        combined.sort_values("timestamp", inplace=True)
        combined.reset_index(drop=True, inplace=True)
    elif existing is not None:
        combined = existing
    else:
        combined = new_df

    _save(combined, path)

    new_count = len(new_df)
    total = len(combined)
    return {
        "symbol": symbol,
        "interval": interval,
        "status": "downloaded",
        "existing": total - new_count,
        "new": new_count,
    }


async def download_symbol(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    symbol: str,
) -> list[dict[str, Any]]:
    """Download all timeframes for one symbol, sequentially per-timeframe
    (to keep progress output readable)."""
    results: list[dict[str, Any]] = []
    for interval in TIMEFRAMES:
        try:
            result = await download_symbol_timeframe(client, semaphore, symbol, interval)
            results.append(result)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            # 400 usually means symbol doesn't support this interval or is delisted.
            print(f"  {symbol}/{interval}: HTTP {status} — skipping")
            results.append({
                "symbol": symbol,
                "interval": interval,
                "status": f"error-{status}",
                "existing": 0,
                "new": 0,
            })
        except Exception as exc:
            print(f"  {symbol}/{interval}: Error {exc!r} — skipping")
            results.append({
                "symbol": symbol,
                "interval": interval,
                "status": "error",
                "existing": 0,
                "new": 0,
            })
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def async_main() -> None:
    start_wall = time.monotonic()

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async with httpx.AsyncClient(
        headers={"Accept": "application/json"},
        follow_redirects=True,
    ) as client:
        symbols = await fetch_top_symbols(client)

        all_results: list[dict[str, Any]] = []

        for idx, symbol in enumerate(symbols, 1):
            print(f"\n[{idx}/{len(symbols)}] {symbol}")
            results = await download_symbol(client, semaphore, symbol)
            all_results.extend(results)

    # ----- Summary -----
    elapsed = time.monotonic() - start_wall
    total_new = sum(r["new"] for r in all_results)
    total_existing = sum(r["existing"] for r in all_results)
    errors = [r for r in all_results if "error" in r["status"]]
    up_to_date = [r for r in all_results if r["status"] == "up-to-date"]
    no_data = [r for r in all_results if r["status"] == "no-data"]

    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"Symbols processed : {len(symbols)}")
    print(f"Timeframes        : {', '.join(TIMEFRAMES)}")
    print(f"New candles saved  : {total_new:,}")
    print(f"Existing candles   : {total_existing:,}")
    print(f"Already up-to-date : {len(up_to_date)}")
    print(f"No data available  : {len(no_data)}")
    print(f"Errors / skipped   : {len(errors)}")
    print(f"Elapsed time       : {elapsed:.1f}s")
    print(f"Data directory     : {DATA_DIR}")
    print("=" * 60)

    if errors:
        print("\nFailed downloads:")
        for r in errors:
            print(f"  {r['symbol']}/{r['interval']}: {r['status']}")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
