"""
Stock news — Finnhub free tier (60/min) or fallback to Yahoo Finance news.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from stocks.config import stock_settings
from stocks.data.models import NewsItem

logger = structlog.get_logger()


def _fetch_finnhub_news(symbol: str) -> list[NewsItem]:
    """Fetch company news from Finnhub (free tier: 60 calls/min)."""
    api_key = stock_settings.finnhub_api_key
    if not api_key:
        return []

    try:
        from datetime import datetime, timedelta
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        url = "https://finnhub.io/api/v1/company-news"
        params = {
            "symbol": symbol,
            "from": week_ago,
            "to": today,
            "token": api_key,
        }

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            articles = resp.json()

        items = []
        for article in articles[:10]:  # Limit to 10 per stock
            items.append(
                NewsItem(
                    headline=article.get("headline", ""),
                    source=article.get("source", ""),
                    url=article.get("url", ""),
                    published=str(article.get("datetime", "")),
                    symbol=symbol,
                    category=article.get("category", ""),
                )
            )
        return items
    except Exception as e:
        logger.warning("finnhub_news_failed", symbol=symbol, error=str(e))
        return []


def _fetch_yahoo_news(symbol: str) -> list[NewsItem]:
    """Fetch news from Yahoo Finance as fallback."""
    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        news = ticker.news or []

        items = []
        for article in news[:10]:
            items.append(
                NewsItem(
                    headline=article.get("title", ""),
                    source=article.get("publisher", ""),
                    url=article.get("link", ""),
                    published=str(article.get("providerPublishTime", "")),
                    symbol=symbol,
                )
            )
        return items
    except Exception as e:
        logger.warning("yahoo_news_failed", symbol=symbol, error=str(e))
        return []


def get_stock_news(symbol: str) -> list[NewsItem]:
    """Get news for a stock, trying Finnhub first, then Yahoo Finance."""
    items = _fetch_finnhub_news(symbol)
    if not items:
        items = _fetch_yahoo_news(symbol)
    return items


def get_market_news() -> list[NewsItem]:
    """Get general market news."""
    api_key = stock_settings.finnhub_api_key
    if not api_key:
        return _fetch_yahoo_news("SPY")

    try:
        url = "https://finnhub.io/api/v1/news"
        params = {"category": "general", "token": api_key}

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            articles = resp.json()

        items = []
        for article in articles[:15]:
            items.append(
                NewsItem(
                    headline=article.get("headline", ""),
                    source=article.get("source", ""),
                    url=article.get("url", ""),
                    published=str(article.get("datetime", "")),
                    category=article.get("category", ""),
                )
            )
        return items
    except Exception as e:
        logger.warning("market_news_failed", error=str(e))
        return []
