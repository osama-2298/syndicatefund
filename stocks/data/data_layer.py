"""
Stock Data Layer — single source of truth for all stock market data.

Same architecture as crypto DataLayer:
  Data Sources → StockDataLayer.fetch_all() → StockMarketSnapshot → team-specific slices
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import structlog

from syndicate.data.models import TechnicalIndicators
from syndicate.data.technical_indicators import compute_indicators, format_price_history
from syndicate.data.us_economic_reports import USReportsSnapshot
from stocks.data.models import (
    EarningsData,
    InstitutionalData,
    MarketIndicesSnapshot,
    NewsItem,
    OptionsSnapshot,
    SectorPerformance,
    ShortSellingData,
    StockFundamentals,
)
from stocks.data.yahoo_finance import (
    get_earnings_data,
    get_fundamentals,
    get_options_snapshot,
    get_short_data,
    get_stock_candles,
    get_stock_stats_24h,
)
from stocks.data.sec_edgar import get_institutional_data
from stocks.data.stock_news import get_stock_news

logger = structlog.get_logger()


class StockData:
    """All raw data for a single stock."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.current_price: float = 0.0
        self.stats: dict = {}

        # Technical (multi-timeframe)
        self.indicators_1h: TechnicalIndicators | None = None
        self.indicators_1d: TechnicalIndicators | None = None
        self.indicators_1w: TechnicalIndicators | None = None
        self.price_history_1d: str = ""

        # Fundamental
        self.fundamentals: StockFundamentals | None = None
        self.earnings: EarningsData | None = None

        # Short selling
        self.short_data: ShortSellingData | None = None

        # Options
        self.options: OptionsSnapshot | None = None

        # Institutional
        self.institutional: InstitutionalData | None = None

        # News
        self.news: list[NewsItem] = []


class StockMarketSnapshot:
    """Complete stock market snapshot for one cycle."""

    def __init__(self) -> None:
        self.stocks: dict[str, StockData] = {}

        # Global market data
        self.indices: MarketIndicesSnapshot | None = None
        self.sector_performance: SectorPerformance | None = None
        self.reddit_sentiment: dict | None = None
        self.market_news: list[NewsItem] = []
        self.us_economic_reports: USReportsSnapshot | None = None
        self.prediction_markets: dict | None = None
        self.cnn_fear_greed: dict | None = None

        # Metadata
        self.fetch_times: dict[str, float] = {}
        self.errors: list[str] = []

    # ─── Team-Specific Data Packets ───

    def for_technical(self, symbol: str) -> dict[str, Any]:
        """Technical team: multi-timeframe indicators, options IV."""
        stock = self.stocks.get(symbol)
        if stock is None:
            return {}
        return {
            "indicators": stock.indicators_1d,
            "indicators_1h": stock.indicators_1h,
            "indicators_1w": stock.indicators_1w,
            "price_history": stock.price_history_1d,
            "stats": stock.stats,
            "options": {
                "put_call_ratio": stock.options.put_call_ratio if stock.options else None,
                "implied_volatility": stock.options.implied_volatility if stock.options else None,
            } if stock.options else None,
            "us_macro_digest": self.us_economic_reports.to_digest() if self.us_economic_reports else {},
        }

    def for_sentiment(self, symbol: str) -> dict[str, Any]:
        """Sentiment team: Reddit, CNN F&G, options flow, market breadth."""
        stock = self.stocks.get(symbol)
        if stock is None:
            return {}
        return {
            "reddit_sentiment": self.reddit_sentiment,
            "cnn_fear_greed": self.cnn_fear_greed,
            "indices": {
                "vix": self.indices.vix if self.indices else None,
                "spy_change": self.indices.spy_change_pct if self.indices else None,
                "advance_decline": self.indices.advance_decline_ratio if self.indices else None,
            } if self.indices else {},
            "options": {
                "put_call_ratio": stock.options.put_call_ratio if stock.options else None,
                "unusual_activity": stock.options.unusual_activity_flag if stock.options else False,
            } if stock.options else {},
            "stats": stock.stats,
            "indicators": stock.indicators_1d,
            "us_macro_digest": self.us_economic_reports.to_digest() if self.us_economic_reports else {},
        }

    def for_fundamental(self, symbol: str) -> dict[str, Any]:
        """Fundamental team: valuation, earnings, quality metrics."""
        stock = self.stocks.get(symbol)
        if stock is None:
            return {}
        return {
            "fundamentals": stock.fundamentals,
            "earnings": stock.earnings,
            "indicators_1d": stock.indicators_1d,
            "indicators_1w": stock.indicators_1w,
            "stats": stock.stats,
        }

    def for_macro(self, symbol: str) -> dict[str, Any]:
        """Macro team: indices, rates, sectors, US reports, prediction markets."""
        stock = self.stocks.get(symbol)
        if stock is None:
            return {}
        us_reports_data: dict[str, Any] = {}
        if self.us_economic_reports:
            us_reports_data = {
                "reports": [
                    {
                        "name": r.name,
                        "importance": r.importance,
                        "category": r.category,
                        "what": r.what,
                        "latest_value": r.latest_value,
                        "previous_value": r.previous_value,
                        "change": r.change,
                        "direction": r.direction,
                        "sentiment_read": r.sentiment_read,
                    }
                    for r in self.us_economic_reports.reports
                ],
                "summary": self.us_economic_reports.summary,
            }
        return {
            "indices": self.indices,
            "sector_performance": self.sector_performance,
            "us_economic_reports": us_reports_data,
            "prediction_markets": self.prediction_markets,
            "cnn_fear_greed": self.cnn_fear_greed,
            "stats": stock.stats,
        }

    def for_institutional(self, symbol: str) -> dict[str, Any]:
        """Institutional team: 13F, insider transactions, short interest."""
        stock = self.stocks.get(symbol)
        if stock is None:
            return {}
        return {
            "institutional": stock.institutional,
            "short_data": stock.short_data,
            "options": stock.options,
            "stats": stock.stats,
        }

    def for_news(self, symbol: str) -> dict[str, Any]:
        """News team: company news + market news."""
        stock = self.stocks.get(symbol)
        if stock is None:
            return {}
        return {
            "company_news": [
                {"headline": n.headline, "source": n.source, "category": n.category}
                for n in stock.news
            ],
            "market_news": [
                {"headline": n.headline, "source": n.source, "category": n.category}
                for n in self.market_news[:10]
            ],
            "sector_performance": self.sector_performance,
            "stats": stock.stats,
        }


class StockDataLayer:
    """Fetches all data from all sources in one coordinated pass."""

    def fetch_all(self, symbols: list[str]) -> StockMarketSnapshot:
        snapshot = StockMarketSnapshot()

        # ── Per-stock data (parallel) ──
        t0 = time.monotonic()

        def _fetch_stock(symbol: str) -> tuple[str, StockData]:
            stock = StockData(symbol)
            try:
                stock.stats = get_stock_stats_24h(symbol)
                stock.current_price = stock.stats.get("close", 0.0)

                # Multi-timeframe indicators
                try:
                    candles_1d = get_stock_candles(symbol, period="1y", interval="1d")
                    if candles_1d:
                        stock.indicators_1d = compute_indicators(candles_1d, symbol)
                        stock.price_history_1d = format_price_history(candles_1d, last_n=20)
                except Exception:
                    pass

                try:
                    candles_1h = get_stock_candles(symbol, period="1mo", interval="1h")
                    if candles_1h:
                        stock.indicators_1h = compute_indicators(candles_1h, symbol)
                except Exception:
                    pass

                try:
                    candles_1w = get_stock_candles(symbol, period="2y", interval="1wk")
                    if candles_1w:
                        stock.indicators_1w = compute_indicators(candles_1w, symbol)
                except Exception:
                    pass

                # Fundamentals
                stock.fundamentals = get_fundamentals(symbol)
                stock.earnings = get_earnings_data(symbol)
                stock.short_data = get_short_data(symbol)
                stock.options = get_options_snapshot(symbol)
                stock.institutional = get_institutional_data(symbol)
                stock.news = get_stock_news(symbol)

            except Exception as e:
                logger.warning("stock_fetch_failed", symbol=symbol, error=str(e))

            return symbol, stock

        with ThreadPoolExecutor(max_workers=min(len(symbols), 6)) as pool:
            results = list(pool.map(lambda s: _fetch_stock(s), symbols))
        for symbol, stock in results:
            snapshot.stocks[symbol] = stock
        snapshot.fetch_times["stocks"] = round(time.monotonic() - t0, 2)

        return snapshot
