"""
Sector performance tracking — GICS sectors via SPDR ETFs.
"""

from __future__ import annotations

import structlog
import yfinance as yf

from stocks.data.models import SectorPerformance

logger = structlog.get_logger()

# GICS Sectors → SPDR ETFs
GICS_SECTOR_ETFS = {
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


def get_sector_performance() -> SectorPerformance:
    """Fetch 1d, 5d, 1m performance for all GICS sector ETFs."""
    result = SectorPerformance()
    hot = []
    cold = []

    for sector, etf in GICS_SECTOR_ETFS.items():
        try:
            ticker = yf.Ticker(etf)
            hist = ticker.history(period="1mo")

            if hist.empty or len(hist) < 2:
                continue

            current = float(hist.iloc[-1]["Close"])

            # 1-day change
            prev_1d = float(hist.iloc[-2]["Close"])
            change_1d = ((current - prev_1d) / prev_1d) * 100

            # 5-day change
            change_5d = 0.0
            if len(hist) >= 6:
                prev_5d = float(hist.iloc[-6]["Close"])
                change_5d = ((current - prev_5d) / prev_5d) * 100

            # 1-month change
            prev_1m = float(hist.iloc[0]["Close"])
            change_1m = ((current - prev_1m) / prev_1m) * 100

            result.sectors[sector] = {
                "etf": etf,
                "price": round(current, 2),
                "change_1d": round(change_1d, 2),
                "change_5d": round(change_5d, 2),
                "change_1m": round(change_1m, 2),
            }

            if change_5d > 2.0:
                hot.append(sector)
            elif change_5d < -2.0:
                cold.append(sector)

        except Exception as e:
            logger.warning("sector_perf_failed", sector=sector, etf=etf, error=str(e))

    result.hot_sectors = hot
    result.cold_sectors = cold
    return result
