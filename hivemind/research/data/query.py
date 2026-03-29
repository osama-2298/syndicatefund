"""Historical data query API for research agents.

Thin read-only layer over the gzip-compressed CSV files produced by
``historical_downloader`` and ``sentiment_downloader``.  Every function
returns a pandas DataFrame (or Series) and never modifies files on disk.

Usage::

    from hivemind.research.data.query import get_candles, get_fear_greed

    btc = get_candles("BTCUSDT", "4h", start_date=date(2025, 1, 1))
    fng = get_fear_greed(start_date=date(2024, 1, 1))
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# Resolve relative to project root, same convention as the downloaders.
DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "historical"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _filter_date_col(
    df: pd.DataFrame,
    col: str,
    start_date: Optional[date],
    end_date: Optional[date],
) -> pd.DataFrame:
    """Apply inclusive date filtering on *col*, handling tz-aware timestamps."""
    if start_date is not None:
        ts = pd.Timestamp(start_date, tz="UTC")
        # If column is tz-naive, compare without tz
        if df[col].dt.tz is None:
            ts = ts.tz_localize(None)
        df = df[df[col] >= ts]
    if end_date is not None:
        # Use end-of-day so the end_date itself is included.
        ts = pd.Timestamp(datetime.combine(end_date, datetime.max.time()), tz="UTC")
        if df[col].dt.tz is None:
            ts = ts.tz_localize(None)
        df = df[df[col] <= ts]
    return df


# ---------------------------------------------------------------------------
# Candle / OHLCV queries
# ---------------------------------------------------------------------------


def get_candles(
    symbol: str,
    timeframe: str = "4h",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> pd.DataFrame:
    """Load OHLCV candle data for a symbol.

    Args:
        symbol: Trading pair, e.g. ``"BTCUSDT"``.
        timeframe: One of ``"1h"``, ``"4h"``, ``"1d"``, ``"1w"``.
        start_date: Include candles from this date (inclusive).
        end_date: Include candles up to this date (inclusive).

    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume.
        Empty DataFrame (with correct columns) when the file is missing.
    """
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    path = DATA_DIR / symbol / f"{timeframe}.csv.gz"
    if not path.exists():
        return pd.DataFrame(columns=cols)

    df = pd.read_csv(path, compression="gzip", parse_dates=["timestamp"])

    df = _filter_date_col(df, "timestamp", start_date, end_date)
    return df.sort_values("timestamp").reset_index(drop=True)


def get_returns(
    symbol: str,
    timeframe: str = "4h",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> pd.Series:
    """Get percentage returns (close-to-close) for a symbol.

    Returns:
        Series of fractional returns indexed by timestamp.
        Empty float Series when no data is available.
    """
    df = get_candles(symbol, timeframe, start_date, end_date)
    if df.empty:
        return pd.Series(dtype=float, name="returns")

    returns = df["close"].pct_change().dropna()
    returns.index = df["timestamp"].iloc[1:].reset_index(drop=True)
    returns.name = "returns"
    return returns


def get_multiple_returns(
    symbols: list[str],
    timeframe: str = "4h",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> pd.DataFrame:
    """Get returns for multiple symbols aligned by timestamp.

    Returns:
        DataFrame with a timestamp index and one column per symbol.
        Rows where *all* symbols are NaN are dropped.
    """
    all_returns: dict[str, pd.Series] = {}
    for symbol in symbols:
        r = get_returns(symbol, timeframe, start_date, end_date)
        if not r.empty:
            all_returns[symbol] = r

    if not all_returns:
        return pd.DataFrame()

    return pd.DataFrame(all_returns).dropna(how="all")


# ---------------------------------------------------------------------------
# Sentiment / macro queries
# ---------------------------------------------------------------------------


def get_fear_greed(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> pd.DataFrame:
    """Load Fear & Greed Index history.

    Returns:
        DataFrame with columns: date, value, classification.
    """
    cols = ["date", "value", "classification"]
    path = DATA_DIR / "sentiment" / "fear_greed.csv.gz"
    if not path.exists():
        return pd.DataFrame(columns=cols)

    df = pd.read_csv(path, compression="gzip", parse_dates=["date"])

    df = _filter_date_col(df, "date", start_date, end_date)
    return df.sort_values("date").reset_index(drop=True)


def get_btc_dominance(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> pd.DataFrame:
    """Load BTC market cap history (proxy for dominance).

    Returns:
        DataFrame with columns: date, market_cap_usd.
    """
    cols = ["date", "market_cap_usd"]
    path = DATA_DIR / "sentiment" / "btc_market_cap.csv.gz"
    if not path.exists():
        return pd.DataFrame(columns=cols)

    df = pd.read_csv(path, compression="gzip", parse_dates=["date"])

    df = _filter_date_col(df, "date", start_date, end_date)
    return df.sort_values("date").reset_index(drop=True)


def get_global_market_cap(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> pd.DataFrame:
    """Load total crypto market cap history.

    Returns:
        DataFrame with columns: date, total_market_cap_usd, source.
    """
    cols = ["date", "total_market_cap_usd", "source"]
    path = DATA_DIR / "sentiment" / "global_market_cap.csv.gz"
    if not path.exists():
        return pd.DataFrame(columns=cols)

    df = pd.read_csv(path, compression="gzip", parse_dates=["date"])

    df = _filter_date_col(df, "date", start_date, end_date)
    return df.sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------


def get_available_symbols() -> list[str]:
    """List all symbols that have historical candle data on disk."""
    if not DATA_DIR.exists():
        return []

    symbols: list[str] = []
    for d in sorted(DATA_DIR.iterdir()):
        if d.is_dir() and d.name != "sentiment" and any(d.glob("*.csv.gz")):
            symbols.append(d.name)
    return symbols


def get_date_range(
    symbol: str,
    timeframe: str = "4h",
) -> tuple[datetime | None, datetime | None]:
    """Get the earliest and latest timestamps for a symbol's candle data.

    Returns:
        ``(earliest, latest)`` or ``(None, None)`` when no data exists.
    """
    df = get_candles(symbol, timeframe)
    if df.empty:
        return None, None
    return df["timestamp"].min().to_pydatetime(), df["timestamp"].max().to_pydatetime()


def get_summary() -> dict:
    """Return a summary of all available historical data on disk.

    Returns a dict with keys:
        symbols, total_symbols, timeframes,
        has_fear_greed, has_btc_market_cap, has_global_market_cap,
        sample_date_ranges (first 5 symbols only, for speed).
    """
    symbols = get_available_symbols()

    # Sample the first 5 symbols to avoid scanning all files.
    date_ranges: dict[str, dict[str, str]] = {}
    for sym in symbols[:5]:
        earliest, latest = get_date_range(sym)
        if earliest is not None:
            date_ranges[sym] = {
                "earliest": earliest.isoformat(),
                "latest": latest.isoformat(),
            }

    return {
        "symbols": symbols,
        "total_symbols": len(symbols),
        "timeframes": ["1h", "4h", "1d", "1w"],
        "has_fear_greed": (DATA_DIR / "sentiment" / "fear_greed.csv.gz").exists(),
        "has_btc_market_cap": (DATA_DIR / "sentiment" / "btc_market_cap.csv.gz").exists(),
        "has_global_market_cap": (DATA_DIR / "sentiment" / "global_market_cap.csv.gz").exists(),
        "sample_date_ranges": date_ranges,
    }
