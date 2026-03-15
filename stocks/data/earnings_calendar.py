"""
Earnings calendar — upcoming earnings, blackout detection, historical surprises.

Wraps yahoo_finance earnings data with batch processing and blackout logic.
"""

from __future__ import annotations

import structlog

from stocks.config import stock_settings
from stocks.data.yahoo_finance import get_earnings_data
from stocks.data.models import EarningsData

logger = structlog.get_logger()


def check_earnings_blackout(symbols: list[str]) -> dict[str, EarningsData]:
    """
    Check earnings blackout for multiple stocks.
    Returns a dict of symbol -> EarningsData.
    """
    results = {}
    blackout_days = stock_settings.earnings_blackout_days

    for symbol in symbols:
        try:
            data = get_earnings_data(symbol, blackout_days=blackout_days)
            if data:
                results[symbol] = data
                if data.in_blackout:
                    logger.info(
                        "earnings_blackout",
                        symbol=symbol,
                        days_to_earnings=data.days_to_earnings,
                    )
        except Exception as e:
            logger.warning("earnings_check_failed", symbol=symbol, error=str(e))

    return results


def get_upcoming_earnings(symbols: list[str], within_days: int = 14) -> list[dict]:
    """Get stocks with earnings within N days."""
    upcoming = []
    for symbol in symbols:
        try:
            data = get_earnings_data(symbol)
            if data and data.days_to_earnings is not None and 0 <= data.days_to_earnings <= within_days:
                upcoming.append({
                    "symbol": symbol,
                    "date": data.next_earnings_date,
                    "days_away": data.days_to_earnings,
                    "in_blackout": data.in_blackout,
                    "avg_surprise": data.avg_surprise_pct,
                    "beat_rate": data.beat_rate,
                })
        except Exception:
            pass

    upcoming.sort(key=lambda x: x["days_away"])
    return upcoming
