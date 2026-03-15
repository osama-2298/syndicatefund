"""
Stock universe — persistent S&P 500 + Russell 1000 + hot sectors + user additions.

Components are scraped from Wikipedia (free, no API key needed).
Cached to disk to avoid hammering Wikipedia on every cycle.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx
import structlog

from stocks.config import stock_settings

logger = structlog.get_logger()

CACHE_TTL_HOURS = 24  # Refresh universe every 24 hours

# Wikipedia URLs for index components
SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# Sector ETFs for hot sector tracking
SECTOR_ETFS = {
    "Technology": "XLK",
    "Health Care": "XLV",
    "Financials": "XLF",
    "Consumer Discretionary": "XLY",
    "Communication Services": "XLC",
    "Industrials": "XLI",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Materials": "XLB",
}


def _scrape_sp500_tickers() -> list[str]:
    """Scrape S&P 500 tickers from Wikipedia."""
    try:
        import pandas as pd

        tables = pd.read_html(SP500_WIKI_URL)
        if tables:
            df = tables[0]
            # The ticker column is typically 'Symbol'
            if "Symbol" in df.columns:
                tickers = df["Symbol"].str.strip().str.replace(".", "-", regex=False).tolist()
                return sorted(set(tickers))
    except ImportError:
        pass

    # Fallback: fetch HTML and parse manually
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(SP500_WIKI_URL, headers={"User-Agent": "Hivemind/1.0"})
            resp.raise_for_status()
            html = resp.text

        # Simple regex-based extraction
        import re
        # Look for ticker symbols in the first table
        pattern = r'<td[^>]*><a[^>]*>([A-Z]{1,5})</a>'
        tickers = re.findall(pattern, html)
        # Filter to likely ticker symbols
        tickers = [t for t in tickers if 1 <= len(t) <= 5 and t.isalpha()]
        return sorted(set(tickers[:600]))  # Safety cap
    except Exception as e:
        logger.warning("sp500_scrape_failed", error=str(e))
        return []


class StockWatchlist:
    """
    Manages the stock universe: S&P 500 + user additions + hot stocks.
    Persists to disk to avoid re-scraping every cycle.
    """

    def __init__(self, storage_path: str | None = None) -> None:
        self._path = Path(storage_path or stock_settings.stock_watchlist_path)
        self._sp500: list[str] = []
        self._user_additions: list[str] = []
        self._hot_stocks: list[str] = []
        self._last_refresh: float = 0.0
        self._load()

    @property
    def universe(self) -> list[str]:
        """Full deduplicated universe."""
        all_tickers = set(self._sp500) | set(self._user_additions) | set(self._hot_stocks)
        return sorted(all_tickers)

    @property
    def sp500(self) -> list[str]:
        return list(self._sp500)

    def refresh_if_stale(self) -> None:
        """Refresh universe from Wikipedia if cache is stale."""
        if time.time() - self._last_refresh < CACHE_TTL_HOURS * 3600:
            return

        logger.info("watchlist_refreshing")
        tickers = _scrape_sp500_tickers()
        if tickers:
            self._sp500 = tickers
            self._last_refresh = time.time()
            self._save()
            logger.info("watchlist_refreshed", sp500_count=len(tickers))

    def add_user_stock(self, symbol: str) -> None:
        symbol = symbol.upper().strip()
        if symbol and symbol not in self._user_additions:
            self._user_additions.append(symbol)
            self._save()

    def set_hot_stocks(self, symbols: list[str]) -> None:
        self._hot_stocks = [s.upper().strip() for s in symbols]
        self._save()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            self._sp500 = data.get("sp500", [])
            self._user_additions = data.get("user_additions", [])
            self._hot_stocks = data.get("hot_stocks", [])
            self._last_refresh = data.get("last_refresh", 0.0)
        except Exception as e:
            logger.error("watchlist_load_failed", error=str(e))

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "sp500": self._sp500,
            "user_additions": self._user_additions,
            "hot_stocks": self._hot_stocks,
            "last_refresh": self._last_refresh,
        }
        self._path.write_text(json.dumps(data, indent=2))
