"""
Yahoo Finance data source — OHLCV, fundamentals, earnings, options, holders, short interest.

Uses yfinance (free, no API key). Rate-limited but sufficient for 10-20 stocks per cycle.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
import yfinance as yf

from hivemind.data.models import Candle, TechnicalIndicators
from hivemind.data.technical_indicators import compute_indicators
from stocks.data.models import (
    EarningsData,
    OptionsSnapshot,
    ShortSellingData,
    StockFundamentals,
)

logger = structlog.get_logger()


def get_stock_candles(
    symbol: str, period: str = "1y", interval: str = "1d"
) -> list[Candle]:
    """Fetch OHLCV candles from Yahoo Finance."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return []

        candles = []
        for idx, row in df.iterrows():
            candles.append(
                Candle(
                    timestamp=idx.to_pydatetime().replace(tzinfo=timezone.utc),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row["Volume"]),
                )
            )
        return candles
    except Exception as e:
        logger.warning("yahoo_candles_failed", symbol=symbol, error=str(e))
        return []


def get_stock_indicators(symbol: str, period: str = "1y", interval: str = "1d") -> TechnicalIndicators | None:
    """Fetch candles and compute technical indicators."""
    candles = get_stock_candles(symbol, period=period, interval=interval)
    if not candles or len(candles) < 50:
        return None
    return compute_indicators(candles, symbol)


def get_fundamentals(symbol: str) -> StockFundamentals | None:
    """Fetch fundamental data from Yahoo Finance."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        if not info or not info.get("symbol"):
            return None

        return StockFundamentals(
            symbol=symbol,
            market_cap=info.get("marketCap"),
            enterprise_value=info.get("enterpriseValue"),
            pe_trailing=info.get("trailingPE"),
            pe_forward=info.get("forwardPE"),
            peg_ratio=info.get("pegRatio"),
            price_to_sales=info.get("priceToSalesTrailing12Months"),
            price_to_book=info.get("priceToBook"),
            ev_to_ebitda=info.get("enterpriseToEbitda"),
            profit_margin=info.get("profitMargins"),
            operating_margin=info.get("operatingMargins"),
            roe=info.get("returnOnEquity"),
            roa=info.get("returnOnAssets"),
            revenue_growth=info.get("revenueGrowth"),
            earnings_growth=info.get("earningsGrowth"),
            debt_to_equity=info.get("debtToEquity"),
            current_ratio=info.get("currentRatio"),
            free_cash_flow=info.get("freeCashflow"),
            dividend_yield=info.get("dividendYield"),
            payout_ratio=info.get("payoutRatio"),
            ex_dividend_date=str(info.get("exDividendDate", "")) if info.get("exDividendDate") else None,
            sector=info.get("sector", ""),
            industry=info.get("industry", ""),
            gics_sector=info.get("sector", ""),
        )
    except Exception as e:
        logger.warning("yahoo_fundamentals_failed", symbol=symbol, error=str(e))
        return None


def get_earnings_data(symbol: str, blackout_days: int = 3) -> EarningsData | None:
    """Fetch earnings calendar and history."""
    try:
        ticker = yf.Ticker(symbol)

        # Earnings dates
        try:
            earnings_dates = ticker.earnings_dates
        except Exception:
            earnings_dates = None

        next_date = None
        days_to = None
        in_blackout = False

        if earnings_dates is not None and not earnings_dates.empty:
            now = datetime.now(timezone.utc)
            future_dates = [
                d for d in earnings_dates.index
                if d.to_pydatetime().replace(tzinfo=timezone.utc) > now
            ]
            if future_dates:
                next_dt = future_dates[0].to_pydatetime().replace(tzinfo=timezone.utc)
                next_date = next_dt.strftime("%Y-%m-%d")
                days_to = (next_dt - now).days
                in_blackout = 0 <= days_to <= blackout_days

        # Historical earnings surprises
        surprises = []
        try:
            earnings_hist = ticker.earnings_history
            if earnings_hist is not None and not earnings_hist.empty:
                for _, row in earnings_hist.tail(4).iterrows():
                    expected = row.get("epsEstimate") or row.get("epsexpected")
                    actual = row.get("epsActual") or row.get("epsactual")
                    if expected and actual:
                        surprise_pct = ((actual - expected) / abs(expected)) * 100 if expected != 0 else 0
                        surprises.append({
                            "expected_eps": float(expected),
                            "actual_eps": float(actual),
                            "surprise_pct": round(surprise_pct, 1),
                        })
        except Exception:
            pass

        avg_surprise = None
        beat_rate = None
        if surprises:
            avg_surprise = sum(s["surprise_pct"] for s in surprises) / len(surprises)
            beat_rate = sum(1 for s in surprises if s["surprise_pct"] > 0) / len(surprises)

        return EarningsData(
            symbol=symbol,
            next_earnings_date=next_date,
            days_to_earnings=days_to,
            in_blackout=in_blackout,
            last_surprises=surprises,
            avg_surprise_pct=round(avg_surprise, 1) if avg_surprise is not None else None,
            beat_rate=round(beat_rate, 2) if beat_rate is not None else None,
        )
    except Exception as e:
        logger.warning("yahoo_earnings_failed", symbol=symbol, error=str(e))
        return None


def get_short_data(symbol: str) -> ShortSellingData | None:
    """Fetch short interest data from Yahoo Finance."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        short_pct = info.get("shortPercentOfFloat")
        short_ratio = info.get("shortRatio")

        # Estimate squeeze risk
        squeeze_risk = "LOW"
        if short_pct and short_ratio:
            if short_pct > 0.20 and short_ratio > 5:
                squeeze_risk = "HIGH"
            elif short_pct > 0.10 or short_ratio > 3:
                squeeze_risk = "MEDIUM"

        # SSR detection: check if stock dropped >10% from prior close
        ssr_active = False
        try:
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                prev_close = float(hist.iloc[-2]["Close"])
                curr = float(hist.iloc[-1]["Close"])
                if prev_close > 0 and (curr - prev_close) / prev_close < -0.10:
                    ssr_active = True
        except Exception:
            pass

        return ShortSellingData(
            symbol=symbol,
            short_interest_pct=short_pct,
            short_ratio=short_ratio,
            hard_to_borrow=short_pct > 0.25 if short_pct else False,
            ssr_active=ssr_active,
            squeeze_risk=squeeze_risk,
        )
    except Exception as e:
        logger.warning("yahoo_short_data_failed", symbol=symbol, error=str(e))
        return None


def get_options_snapshot(symbol: str) -> OptionsSnapshot | None:
    """Fetch options market summary."""
    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options

        if not expirations:
            return None

        # Use nearest expiration
        chain = ticker.option_chain(expirations[0])
        calls = chain.calls
        puts = chain.puts

        total_call_vol = calls["volume"].sum() if "volume" in calls.columns else 0
        total_put_vol = puts["volume"].sum() if "volume" in puts.columns else 0

        put_call_ratio = None
        if total_call_vol > 0:
            put_call_ratio = total_put_vol / total_call_vol

        # Average IV
        avg_iv = None
        if "impliedVolatility" in calls.columns:
            all_iv = list(calls["impliedVolatility"].dropna()) + list(puts["impliedVolatility"].dropna())
            if all_iv:
                avg_iv = sum(all_iv) / len(all_iv)

        # Unusual activity (volume > 5x open interest)
        unusual_calls = 0
        unusual_puts = 0
        if "volume" in calls.columns and "openInterest" in calls.columns:
            for _, row in calls.iterrows():
                if row.get("volume", 0) and row.get("openInterest", 0):
                    if row["volume"] > 5 * row["openInterest"]:
                        unusual_calls += 1
        if "volume" in puts.columns and "openInterest" in puts.columns:
            for _, row in puts.iterrows():
                if row.get("volume", 0) and row.get("openInterest", 0):
                    if row["volume"] > 5 * row["openInterest"]:
                        unusual_puts += 1

        return OptionsSnapshot(
            symbol=symbol,
            put_call_ratio=round(put_call_ratio, 2) if put_call_ratio else None,
            implied_volatility=round(avg_iv, 4) if avg_iv else None,
            unusual_calls=unusual_calls,
            unusual_puts=unusual_puts,
            unusual_activity_flag=(unusual_calls + unusual_puts) >= 3,
        )
    except Exception as e:
        logger.warning("yahoo_options_failed", symbol=symbol, error=str(e))
        return None


def get_stock_price(symbol: str) -> float:
    """Get current stock price."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist.iloc[-1]["Close"])
    except Exception:
        pass
    return 0.0


def get_stock_stats_24h(symbol: str) -> dict[str, Any]:
    """Get 24h-equivalent stats (1 trading day) for a stock."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")
        if hist.empty:
            return {}

        current = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) >= 2 else current

        close = float(current["Close"])
        prev_close = float(prev["Close"])
        change_pct = ((close - prev_close) / prev_close * 100) if prev_close > 0 else 0

        return {
            "symbol": symbol,
            "close": close,
            "open": float(current["Open"]),
            "high": float(current["High"]),
            "low": float(current["Low"]),
            "volume": float(current["Volume"]),
            "price_change_pct": round(change_pct, 2),
            "prev_close": prev_close,
        }
    except Exception as e:
        logger.warning("yahoo_stats_failed", symbol=symbol, error=str(e))
        return {}
