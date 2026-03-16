"""
Market indices and macro indicators — SPY, QQQ, VIX, DXY, yields, commodities, breadth.

All from Yahoo Finance (free).
"""

from __future__ import annotations

import structlog
import yfinance as yf

from stocks.data.models import MarketIndicesSnapshot

logger = structlog.get_logger()

# Yahoo Finance tickers for indices and macro indicators
INDEX_TICKERS = {
    "spy": "SPY",
    "qqq": "QQQ",
    "iwm": "IWM",
    "vix": "^VIX",
    "treasury_2y": "^IRX",   # 13-week T-bill as proxy
    "treasury_10y": "^TNX",
    "dxy": "DX-Y.NYB",
    "oil": "CL=F",
    "gold": "GC=F",
}


def get_market_indices() -> MarketIndicesSnapshot:
    """Fetch all market indices and macro indicators."""
    snapshot = MarketIndicesSnapshot()

    for key, ticker_sym in INDEX_TICKERS.items():
        try:
            ticker = yf.Ticker(ticker_sym)
            hist = ticker.history(period="5d")
            if hist.empty:
                continue

            current = float(hist.iloc[-1]["Close"])
            prev = float(hist.iloc[-2]["Close"]) if len(hist) >= 2 else current
            change = ((current - prev) / prev * 100) if prev > 0 else 0

            if key == "spy":
                snapshot.spy_price = current
                snapshot.spy_change_pct = round(change, 2)
            elif key == "qqq":
                snapshot.qqq_price = current
                snapshot.qqq_change_pct = round(change, 2)
            elif key == "iwm":
                snapshot.iwm_price = current
                snapshot.iwm_change_pct = round(change, 2)
            elif key == "vix":
                snapshot.vix = current
                snapshot.vix_change = round(change, 2)
            elif key == "treasury_2y":
                snapshot.treasury_2y = current
            elif key == "treasury_10y":
                snapshot.treasury_10y = current
            elif key == "dxy":
                snapshot.dxy = current
            elif key == "oil":
                snapshot.oil_price = current
            elif key == "gold":
                snapshot.gold_price = current
        except Exception as e:
            logger.warning("index_fetch_failed", ticker=key, error=str(e))

    # Yield curve spread
    if snapshot.treasury_10y and snapshot.treasury_2y:
        snapshot.yield_curve_spread = round(snapshot.treasury_10y - snapshot.treasury_2y, 2)

    return snapshot


def get_cnn_fear_greed() -> dict:
    """
    Fetch CNN Fear & Greed Index.
    Uses the public API endpoint.
    """
    import httpx

    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers={"User-Agent": "Syndicate/1.0"})
            resp.raise_for_status()
            data = resp.json()

        fg = data.get("fear_and_greed", {})
        score = fg.get("score", 50)
        rating = fg.get("rating", "Neutral")

        return {
            "current_value": round(score),
            "current_label": rating,
        }
    except Exception as e:
        logger.warning("cnn_fg_failed", error=str(e))
        return {}
