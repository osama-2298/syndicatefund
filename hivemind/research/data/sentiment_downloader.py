"""
Sentiment & Macro Historical Data Downloader.

Downloads and stores historical sentiment/macro datasets for research:
  1. Fear & Greed Index — full history from alternative.me (back to Feb 2018)
  2. BTC Market Cap — from CoinGecko market_chart (5 years of daily data)
  3. Total Crypto Market Cap — from CoinGecko global market cap chart

All data is stored as gzip-compressed CSVs under data/historical/sentiment/.
Respects CoinGecko free-tier rate limits (10-15 req/min) with explicit sleeps
and exponential backoff retries.

Usage:
    python -m hivemind.research.data.sentiment_downloader
    python -m hivemind.research.data.sentiment_downloader --only fear_greed
    python -m hivemind.research.data.sentiment_downloader --only btc_market_cap
    python -m hivemind.research.data.sentiment_downloader --only global_market_cap
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger()

# ── Paths ──────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # hivemind repo root
SENTIMENT_DIR = PROJECT_ROOT / "data" / "historical" / "sentiment"

# ── API URLs ───────────────────────────────────────────────────────────────────

FEAR_GREED_URL = "https://api.alternative.me/fng/"
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# CoinGecko free tier: 10-15 req/min. We space requests 6s apart to stay safe.
COINGECKO_DELAY_SECONDS = 6.0

# ── Retry config ───────────────────────────────────────────────────────────────
# Retry on connection errors and 429/5xx responses, up to 5 attempts with
# exponential backoff (2s, 4s, 8s, 16s, 32s max).

_RETRY_KWARGS = dict(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)),
    reraise=True,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _ensure_dir() -> Path:
    """Create the sentiment output directory if it doesn't exist."""
    SENTIMENT_DIR.mkdir(parents=True, exist_ok=True)
    return SENTIMENT_DIR


def _save_csv(df: pd.DataFrame, filename: str) -> Path:
    """Save a DataFrame as gzip-compressed CSV. Returns the output path."""
    out = _ensure_dir() / filename
    df.to_csv(out, index=False, compression="gzip")
    logger.info("saved", path=str(out), rows=len(df), size_kb=round(out.stat().st_size / 1024, 1))
    return out


def _raise_for_rate_limit(resp: httpx.Response) -> None:
    """Raise HTTPStatusError on 429 so tenacity can retry with backoff."""
    if resp.status_code == 429:
        logger.warning("rate_limited", url=str(resp.url), status=429)
        resp.raise_for_status()


# ── 1. Fear & Greed Index ──────────────────────────────────────────────────────


@retry(**_RETRY_KWARGS)
def _fetch_fear_greed_raw() -> list[dict]:
    """Fetch the complete Fear & Greed history from alternative.me.

    limit=0 returns ALL available data (back to Feb 2018).
    The API is free and has no auth requirement.
    """
    logger.info("fetching_fear_greed", url=FEAR_GREED_URL)
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(FEAR_GREED_URL, params={"limit": 0, "format": "json"})
        _raise_for_rate_limit(resp)
        resp.raise_for_status()
        data = resp.json()

    entries = data.get("data", [])
    if not entries:
        raise ValueError("Fear & Greed API returned no data entries")

    logger.info("fear_greed_fetched", entries=len(entries))
    return entries


def download_fear_greed() -> Path:
    """Download full Fear & Greed history and save as CSV.

    Output columns:
        date         — datetime (UTC, date only)
        value        — int 0-100
        classification — str (Extreme Fear / Fear / Neutral / Greed / Extreme Greed)
    """
    entries = _fetch_fear_greed_raw()

    rows = []
    for entry in entries:
        ts = int(entry["timestamp"])
        rows.append({
            "date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
            "value": int(entry["value"]),
            "classification": entry["value_classification"],
        })

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)

    logger.info(
        "fear_greed_processed",
        rows=len(df),
        date_range=f"{df['date'].min().date()} to {df['date'].max().date()}",
    )
    return _save_csv(df, "fear_greed.csv.gz")


# ── 2. BTC Market Cap ─────────────────────────────────────────────────────────


@retry(**_RETRY_KWARGS)
def _fetch_coingecko_market_chart(coin_id: str, days: int) -> dict:
    """Fetch /coins/{id}/market_chart from CoinGecko.

    Returns raw JSON with keys: prices, market_caps, total_volumes.
    Each value is a list of [unix_timestamp_ms, float] pairs.

    For days > 90, CoinGecko returns daily granularity automatically.
    """
    url = f"{COINGECKO_BASE}/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days}

    logger.info("fetching_coingecko_market_chart", coin_id=coin_id, days=days)
    with httpx.Client(timeout=30.0, headers={"Accept": "application/json"}) as client:
        resp = client.get(url, params=params)
        _raise_for_rate_limit(resp)
        resp.raise_for_status()
        return resp.json()


def download_btc_market_cap() -> Path:
    """Download BTC market cap history from CoinGecko (up to 5 years daily).

    CoinGecko /coins/bitcoin/market_chart?vs_currency=usd&days=1825 returns
    daily [timestamp_ms, market_cap] pairs.

    Output columns:
        date           — datetime (UTC, date only)
        market_cap_usd — float
    """
    data = _fetch_coingecko_market_chart("bitcoin", days=1825)

    market_caps = data.get("market_caps", [])
    if not market_caps:
        raise ValueError("CoinGecko returned no market_caps data for bitcoin")

    rows = []
    for ts_ms, mcap in market_caps:
        if mcap is None or mcap <= 0:
            continue
        rows.append({
            "date": datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d"),
            "market_cap_usd": mcap,
        })

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    # CoinGecko sometimes returns multiple points per day at sub-daily granularity.
    # Keep the last reading per day (closest to 00:00 UTC of the next day).
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)

    logger.info(
        "btc_market_cap_processed",
        rows=len(df),
        date_range=f"{df['date'].min().date()} to {df['date'].max().date()}",
    )
    return _save_csv(df, "btc_market_cap.csv.gz")


# ── 3. Total Crypto Market Cap ─────────────────────────────────────────────────


@retry(**_RETRY_KWARGS)
def _fetch_total_market_cap_chart(days: int) -> list[list]:
    """Attempt to fetch total crypto market cap history.

    Strategy (ordered by preference):
      1. /global/market_cap_chart — may be premium-only on CoinGecko.
      2. Fallback: sum the top 250 coins' market caps from /coins/markets.
         This gives a single snapshot (not historical), so we note the limitation.
      3. Alternative fallback: download total market cap via the same market_chart
         endpoint but using a broad index. CoinGecko doesn't have a "total" coin,
         but the /global endpoint gives current totals.

    For historical total market cap, the cleanest free approach is to use the
    market_chart endpoint for a stablecoin-excluded total proxy. Since no single
    free endpoint gives historical total market cap reliably, we attempt the
    /global/market_cap_chart endpoint first and fall back to computing a snapshot
    series from multiple coins.

    Returns list of [timestamp_ms, total_market_cap_usd] pairs.
    """
    # Attempt 1: /global/market_cap_chart (may require API key / Pro plan)
    url = f"{COINGECKO_BASE}/global/market_cap_chart"
    params = {"vs_currency": "usd", "days": days}

    logger.info("fetching_global_market_cap_chart", days=days)
    with httpx.Client(timeout=30.0, headers={"Accept": "application/json"}) as client:
        resp = client.get(url, params=params)

        if resp.status_code == 429:
            logger.warning("rate_limited", url=url)
            resp.raise_for_status()

        if resp.status_code in (401, 403, 404):
            # Premium-only endpoint — fall back to building from coin data
            logger.warning(
                "global_market_cap_chart_unavailable",
                status=resp.status_code,
                detail="Endpoint likely requires CoinGecko Pro. Falling back to coin-level aggregation.",
            )
            return []

        resp.raise_for_status()
        data = resp.json()

    # The response shape has "market_cap_chart" -> "data" -> list of pairs
    # or just a top-level "market_caps" key depending on the API version.
    chart_data = data.get("market_cap_chart", {}).get("data", [])
    if not chart_data:
        chart_data = data.get("market_caps", [])
    return chart_data


@retry(**_RETRY_KWARGS)
def _fetch_top_coins_market_caps(per_page: int = 250) -> list[dict]:
    """Fetch current market caps for top N coins by market cap.

    Used as a fallback when the /global/market_cap_chart endpoint is unavailable.
    Returns list of coin dicts with at minimum {id, market_cap, ...}.
    """
    url = f"{COINGECKO_BASE}/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": per_page,
        "page": 1,
        "sparkline": "false",
    }

    logger.info("fetching_top_coins_markets", per_page=per_page)
    with httpx.Client(timeout=30.0, headers={"Accept": "application/json"}) as client:
        resp = client.get(url, params=params)
        _raise_for_rate_limit(resp)
        resp.raise_for_status()
        return resp.json()


def download_global_market_cap() -> Path:
    """Download total crypto market cap history and save as CSV.

    Attempts CoinGecko /global/market_cap_chart first (premium).
    Falls back to a current-snapshot approach using /coins/markets if the
    historical endpoint is unavailable, plus the /global endpoint for the
    official total.

    Output columns:
        date               — datetime (UTC)
        total_market_cap_usd — float
        source             — str ("chart_history" | "snapshot")
    """
    # Rate limit pause before CoinGecko call (after btc_market_cap)
    time.sleep(COINGECKO_DELAY_SECONDS)

    chart_data = _fetch_total_market_cap_chart(days=1825)

    if chart_data:
        # We got historical data from the chart endpoint
        rows = []
        for ts_ms, mcap in chart_data:
            if mcap is None or mcap <= 0:
                continue
            rows.append({
                "date": datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d"),
                "total_market_cap_usd": mcap,
                "source": "chart_history",
            })

        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)

        logger.info(
            "global_market_cap_processed",
            rows=len(df),
            source="chart_history",
            date_range=f"{df['date'].min().date()} to {df['date'].max().date()}",
        )
        return _save_csv(df, "global_market_cap.csv.gz")

    # Fallback: snapshot from /global + /coins/markets
    logger.info("global_market_cap_fallback", detail="Using snapshot from /global endpoint")

    time.sleep(COINGECKO_DELAY_SECONDS)

    # Get official total from /global
    global_total = _fetch_global_total()

    time.sleep(COINGECKO_DELAY_SECONDS)

    # Get top 250 coins breakdown
    top_coins = _fetch_top_coins_market_caps(per_page=250)
    top_250_sum = sum(c.get("market_cap", 0) or 0 for c in top_coins)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    rows = [{
        "date": now_str,
        "total_market_cap_usd": global_total,
        "source": "snapshot",
    }]

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], utc=True)

    coverage_pct = (top_250_sum / global_total * 100) if global_total > 0 else 0

    logger.info(
        "global_market_cap_snapshot",
        total_usd=f"${global_total:,.0f}",
        top_250_sum=f"${top_250_sum:,.0f}",
        top_250_coverage_pct=f"{coverage_pct:.1f}%",
        note="Historical data requires CoinGecko Pro. Only current snapshot saved.",
    )
    return _save_csv(df, "global_market_cap.csv.gz")


@retry(**_RETRY_KWARGS)
def _fetch_global_total() -> float:
    """Fetch current total crypto market cap from /global endpoint."""
    url = f"{COINGECKO_BASE}/global"
    logger.info("fetching_global_total")
    with httpx.Client(timeout=15.0, headers={"Accept": "application/json"}) as client:
        resp = client.get(url)
        _raise_for_rate_limit(resp)
        resp.raise_for_status()
        data = resp.json()
    return data.get("data", {}).get("total_market_cap", {}).get("usd", 0)


# ── Orchestrator ───────────────────────────────────────────────────────────────


DOWNLOADERS = {
    "fear_greed": download_fear_greed,
    "btc_market_cap": download_btc_market_cap,
    "global_market_cap": download_global_market_cap,
}


def download_all(only: str | None = None) -> dict[str, Path | str]:
    """Run all (or one) downloaders. Returns dict of name -> output path or error."""
    targets = {only: DOWNLOADERS[only]} if only else DOWNLOADERS
    results: dict[str, Path | str] = {}

    for name, fn in targets.items():
        logger.info("downloading", dataset=name)
        t0 = time.monotonic()
        try:
            path = fn()
            elapsed = round(time.monotonic() - t0, 1)
            results[name] = path
            logger.info("download_complete", dataset=name, path=str(path), seconds=elapsed)
        except Exception as e:
            elapsed = round(time.monotonic() - t0, 1)
            results[name] = f"FAILED: {e}"
            logger.error("download_failed", dataset=name, error=str(e), seconds=elapsed)

        # Rate-limit pause between CoinGecko-hitting downloaders
        if name in ("btc_market_cap",) and "global_market_cap" in targets:
            logger.info("rate_limit_pause", seconds=COINGECKO_DELAY_SECONDS)
            time.sleep(COINGECKO_DELAY_SECONDS)

    return results


# ── CLI ────────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download historical sentiment and macro data for Hivemind research.",
    )
    parser.add_argument(
        "--only",
        choices=list(DOWNLOADERS.keys()),
        default=None,
        help="Download only a specific dataset instead of all.",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("Hivemind Sentiment & Macro Data Downloader")
    print(f"Output directory: {SENTIMENT_DIR}")
    print("=" * 70)
    print()

    results = download_all(only=args.only)

    print()
    print("-" * 70)
    print("Results:")
    print("-" * 70)
    for name, result in results.items():
        if isinstance(result, Path):
            size_kb = round(result.stat().st_size / 1024, 1)
            print(f"  {name:25s} -> {result}  ({size_kb} KB)")
        else:
            print(f"  {name:25s} -> {result}")
    print("-" * 70)

    # Exit with error code if any downloads failed
    failed = [n for n, r in results.items() if isinstance(r, str)]
    if failed:
        print(f"\nWARNING: {len(failed)} download(s) failed: {', '.join(failed)}")
        sys.exit(1)
    else:
        print(f"\nAll {len(results)} dataset(s) downloaded successfully.")


if __name__ == "__main__":
    main()
