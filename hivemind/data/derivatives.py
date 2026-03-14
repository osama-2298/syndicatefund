"""
Binance Futures derivatives data — free, no auth.

Provides the signals that separate retail traders from real hedge funds:
- Funding rates (who's paying who — longs or shorts?)
- Open interest (how much leverage is in the system?)
- Top trader long/short ratio (what are the whales doing?)
- Taker buy/sell volume (who's aggressive — buyers or sellers?)
- Global long/short ratio (what's the retail crowd doing?)

These are LEADING indicators. They move BEFORE price.
"""

from __future__ import annotations

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

FUTURES_BASE = "https://fapi.binance.com"


class DerivativesClient:
    """Binance Futures public data — derivatives sentiment and positioning."""

    def __init__(self) -> None:
        self._client = httpx.Client(
            base_url=FUTURES_BASE,
            timeout=15.0,
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> DerivativesClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_funding_rate(self, symbol: str, limit: int = 5) -> dict:
        """
        Get recent funding rates. Positive = longs pay shorts (bullish crowd).
        Negative = shorts pay longs (bearish crowd).

        Extremes (>0.05% or <-0.05%) often precede reversals.
        """
        resp = self._client.get(
            "/fapi/v1/fundingRate",
            params={"symbol": symbol, "limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()

        if not data:
            return {"symbol": symbol, "current_rate": 0, "avg_rate": 0, "sentiment": "UNKNOWN"}

        rates = [float(d["fundingRate"]) for d in data]
        current = rates[0]
        avg = sum(rates) / len(rates)

        # Classify
        if current > 0.0005:
            sentiment = "EXTREME_LONG — Longs heavily crowded, reversal risk"
        elif current > 0.0001:
            sentiment = "BULLISH — Longs paying shorts"
        elif current > -0.0001:
            sentiment = "NEUTRAL"
        elif current > -0.0005:
            sentiment = "BEARISH — Shorts paying longs"
        else:
            sentiment = "EXTREME_SHORT — Shorts heavily crowded, squeeze risk"

        return {
            "symbol": symbol,
            "current_rate": round(current, 8),
            "current_rate_pct": round(current * 100, 4),
            "avg_rate": round(avg, 8),
            "avg_rate_pct": round(avg * 100, 4),
            "sentiment": sentiment,
            "rates_history": [round(r, 8) for r in rates],
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_open_interest(self, symbol: str) -> dict:
        """
        Get current open interest (total outstanding futures contracts).
        Rising OI + rising price = strong trend.
        Rising OI + falling price = potential short squeeze.
        Falling OI = positions closing, trend weakening.
        """
        resp = self._client.get(
            "/fapi/v1/openInterest",
            params={"symbol": symbol},
        )
        resp.raise_for_status()
        data = resp.json()

        oi = float(data.get("openInterest", 0))

        return {
            "symbol": symbol,
            "open_interest": round(oi, 4),
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_long_short_ratio(self, symbol: str, period: str = "1h", limit: int = 5) -> dict:
        """
        Top trader long/short ratio — what the whales are doing.
        Ratio > 1 = more top traders long.
        Ratio < 1 = more top traders short.
        """
        resp = self._client.get(
            "/futures/data/topLongShortAccountRatio",
            params={"symbol": symbol, "period": period, "limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()

        if not data:
            return {"symbol": symbol, "ratio": 1.0, "long_pct": 50, "short_pct": 50, "signal": "UNKNOWN"}

        latest = data[0]
        ratio = float(latest.get("longShortRatio", 1.0))
        long_pct = float(latest.get("longAccount", 0.5)) * 100
        short_pct = float(latest.get("shortAccount", 0.5)) * 100

        if ratio > 2.0:
            signal = "EXTREME_LONG — Whales very long, potential top"
        elif ratio > 1.3:
            signal = "BULLISH — Whales favor long"
        elif ratio > 0.7:
            signal = "NEUTRAL"
        elif ratio > 0.5:
            signal = "BEARISH — Whales favor short"
        else:
            signal = "EXTREME_SHORT — Whales very short, squeeze risk"

        return {
            "symbol": symbol,
            "ratio": round(ratio, 3),
            "long_pct": round(long_pct, 1),
            "short_pct": round(short_pct, 1),
            "signal": signal,
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_taker_volume(self, symbol: str, period: str = "1h", limit: int = 5) -> dict:
        """
        Taker buy/sell volume — who's aggressive?
        Ratio > 1 = aggressive buyers dominating (bullish).
        Ratio < 1 = aggressive sellers dominating (bearish).
        This is one of the most responsive leading indicators.
        """
        resp = self._client.get(
            "/futures/data/takerlongshortRatio",
            params={"symbol": symbol, "period": period, "limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()

        if not data:
            return {"symbol": symbol, "buy_sell_ratio": 1.0, "signal": "UNKNOWN"}

        latest = data[0]
        ratio = float(latest.get("buySellRatio", 1.0))
        buy_vol = float(latest.get("buyVol", 0))
        sell_vol = float(latest.get("sellVol", 0))

        if ratio > 1.15:
            signal = "STRONG_BUY_PRESSURE — Aggressive buyers dominating"
        elif ratio > 1.02:
            signal = "MODERATE_BUY_PRESSURE"
        elif ratio > 0.98:
            signal = "BALANCED"
        elif ratio > 0.85:
            signal = "MODERATE_SELL_PRESSURE"
        else:
            signal = "STRONG_SELL_PRESSURE — Aggressive sellers dominating"

        return {
            "symbol": symbol,
            "buy_sell_ratio": round(ratio, 4),
            "buy_volume": round(buy_vol, 2),
            "sell_volume": round(sell_vol, 2),
            "signal": signal,
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_global_long_short(self, symbol: str, period: str = "1h", limit: int = 5) -> dict:
        """
        Global (all accounts) long/short ratio — what retail is doing.
        Compare with top trader ratio to spot smart money divergence.
        """
        resp = self._client.get(
            "/futures/data/globalLongShortAccountRatio",
            params={"symbol": symbol, "period": period, "limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()

        if not data:
            return {"symbol": symbol, "ratio": 1.0, "signal": "UNKNOWN"}

        latest = data[0]
        ratio = float(latest.get("longShortRatio", 1.0))
        long_pct = float(latest.get("longAccount", 0.5)) * 100
        short_pct = float(latest.get("shortAccount", 0.5)) * 100

        return {
            "symbol": symbol,
            "ratio": round(ratio, 3),
            "long_pct": round(long_pct, 1),
            "short_pct": round(short_pct, 1),
        }

    def get_full_derivatives_snapshot(self, symbol: str) -> dict:
        """
        Get ALL derivatives data for a symbol in one call.
        This is the complete derivatives intelligence packet.
        """
        result: dict = {"symbol": symbol}

        try:
            result["funding"] = self.get_funding_rate(symbol)
        except Exception:
            result["funding"] = None

        try:
            result["open_interest"] = self.get_open_interest(symbol)
        except Exception:
            result["open_interest"] = None

        try:
            result["top_trader_ls"] = self.get_long_short_ratio(symbol)
        except Exception:
            result["top_trader_ls"] = None

        try:
            result["taker_volume"] = self.get_taker_volume(symbol)
        except Exception:
            result["taker_volume"] = None

        try:
            result["global_ls"] = self.get_global_long_short(symbol)
        except Exception:
            result["global_ls"] = None

        # Smart money divergence: when top traders and retail disagree
        top_ls = result.get("top_trader_ls")
        global_ls = result.get("global_ls")
        if top_ls and global_ls:
            top_ratio = top_ls.get("ratio", 1.0)
            global_ratio = global_ls.get("ratio", 1.0)
            if top_ratio > 1.2 and global_ratio < 0.8:
                result["smart_money_divergence"] = "WHALES_LONG_RETAIL_SHORT — Potential squeeze up"
            elif top_ratio < 0.8 and global_ratio > 1.2:
                result["smart_money_divergence"] = "WHALES_SHORT_RETAIL_LONG — Potential dump"
            else:
                result["smart_money_divergence"] = "ALIGNED"

        return result
