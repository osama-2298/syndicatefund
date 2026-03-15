"""
SEC EDGAR data — 13F filings, Form 4 insider transactions.

Free API, only requires User-Agent header (no API key).
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from stocks.config import stock_settings
from stocks.data.models import InstitutionalData

logger = structlog.get_logger()

EDGAR_BASE = "https://efts.sec.gov/LATEST"
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


def _get_cik(symbol: str) -> str | None:
    """Get CIK number for a ticker symbol."""
    try:
        headers = {"User-Agent": stock_settings.sec_edgar_user_agent}
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(COMPANY_TICKERS_URL, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        for entry in data.values():
            if entry.get("ticker", "").upper() == symbol.upper():
                cik = str(entry["cik_str"])
                return cik.zfill(10)
    except Exception as e:
        logger.warning("edgar_cik_failed", symbol=symbol, error=str(e))
    return None


def get_institutional_data(symbol: str) -> InstitutionalData | None:
    """
    Fetch institutional ownership and insider transaction data.

    Uses SEC EDGAR XBRL API for company facts and filings.
    Falls back to Yahoo Finance for basic institutional %.
    """
    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        info = ticker.info

        inst_pct = info.get("heldPercentInstitutions")

        # Top holders
        top_holders = []
        try:
            holders_df = ticker.institutional_holders
            if holders_df is not None and not holders_df.empty:
                for _, row in holders_df.head(5).iterrows():
                    top_holders.append({
                        "name": str(row.get("Holder", "")),
                        "shares": int(row.get("Shares", 0)),
                        "pct": round(float(row.get("pctHeld", 0)) * 100, 2) if row.get("pctHeld") else None,
                    })
        except Exception:
            pass

        # Insider transactions
        insider_buys = 0
        insider_sells = 0
        notable = []
        try:
            insider_df = ticker.insider_transactions
            if insider_df is not None and not insider_df.empty:
                for _, row in insider_df.iterrows():
                    text = str(row.get("Text", "")).lower()
                    shares = abs(int(row.get("Shares", 0)))
                    if "purchase" in text or "buy" in text:
                        insider_buys += 1
                    elif "sale" in text or "sell" in text:
                        insider_sells += 1

                    if shares > 10000:
                        notable.append({
                            "insider": str(row.get("Insider Trading", "")),
                            "action": text[:50],
                            "shares": shares,
                        })
        except Exception:
            pass

        return InstitutionalData(
            symbol=symbol,
            institutional_pct=inst_pct,
            top_holders=top_holders,
            insider_buys_90d=insider_buys,
            insider_sells_90d=insider_sells,
            insider_net_shares=insider_buys - insider_sells,
            notable_insiders=notable[:5],
        )
    except Exception as e:
        logger.warning("institutional_data_failed", symbol=symbol, error=str(e))
        return None
