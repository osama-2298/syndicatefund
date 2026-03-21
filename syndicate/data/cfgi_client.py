"""
CFGI.io Client — Per-coin Crypto Fear & Greed Index.

Replaces the single daily BTC-only Alternative.me F&G with granular
per-coin sentiment updated every 15 minutes for 52+ tokens.

API: https://cfgi.io/api (free tier, no API key required for basic endpoints)

Returns fear/greed values per coin across multiple timeframes:
- 15 minutes, 1 hour, 4 hours, 1 day

This is a direct upgrade: per-coin sentiment at 15-min intervals vs
a single daily BTC number from Alternative.me.
"""

from __future__ import annotations

import structlog
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

CFGI_BASE_URL = "https://cfgi.io/api"

# Map common Binance symbols to CFGI coin identifiers
SYMBOL_TO_CFGI = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
    "SOLUSDT": "solana",
    "BNBUSDT": "binancecoin",
    "XRPUSDT": "ripple",
    "ADAUSDT": "cardano",
    "DOGEUSDT": "dogecoin",
    "AVAXUSDT": "avalanche-2",
    "DOTUSDT": "polkadot",
    "LINKUSDT": "chainlink",
    "UNIUSDT": "uniswap",
    "ATOMUSDT": "cosmos",
    "NEARUSDT": "near",
    "APTUSDT": "aptos",
    "SUIUSDT": "sui",
    "LTCUSDT": "litecoin",
    "AAVEUSDT": "aave",
    "INJUSDT": "injective-protocol",
    "FETUSDT": "fetch-ai",
    "RENDERUSDT": "render-token",
    "PEPEUSDT": "pepe",
    "SHIBUSDT": "shiba-inu",
    "BONKUSDT": "bonk",
}

# Default timeout
TIMEOUT = 10.0


class CFGIClient:
    """Client for the CFGI.io per-coin Fear & Greed API."""

    def __init__(self, base_url: str = CFGI_BASE_URL, timeout: float = TIMEOUT) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, max=5))
    def get_coin_fear_greed(self, symbol: str) -> dict | None:
        """
        Get Fear & Greed index for a specific coin.

        Args:
            symbol: Binance symbol (e.g., "BTCUSDT")

        Returns:
            {
                "coin": "bitcoin",
                "symbol": "BTCUSDT",
                "value_15m": 45,
                "value_1h": 48,
                "value_4h": 52,
                "value_1d": 50,
                "label": "Neutral",
                "source": "cfgi.io"
            }
            or None if unavailable.
        """
        coin_id = SYMBOL_TO_CFGI.get(symbol)
        if not coin_id:
            return None

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.base_url}/{coin_id}")
                if response.status_code != 200:
                    logger.debug("cfgi_request_failed", symbol=symbol, status=response.status_code)
                    return None

                data = response.json()

                # CFGI returns data in various formats — normalize
                if isinstance(data, dict):
                    # Try to extract the fear/greed value
                    value = data.get("now", data.get("value", data.get("fear_greed", 50)))
                    if isinstance(value, dict):
                        value = value.get("value", 50)

                    # Try to get multi-timeframe values
                    value_15m = data.get("15m", data.get("now", value))
                    value_1h = data.get("1h", value)
                    value_4h = data.get("4h", value)
                    value_1d = data.get("1d", data.get("24h", value))

                    # Ensure values are numeric
                    def _to_int(v, default=50):
                        if isinstance(v, dict):
                            v = v.get("value", default)
                        try:
                            return int(float(v))
                        except (ValueError, TypeError):
                            return default

                    v15 = _to_int(value_15m)
                    v1h = _to_int(value_1h)
                    v4h = _to_int(value_4h)
                    v1d = _to_int(value_1d)

                    # Determine label from 4h value (our primary timeframe)
                    primary = v4h
                    if primary <= 10:
                        label = "Extreme Fear"
                    elif primary <= 25:
                        label = "Fear"
                    elif primary <= 45:
                        label = "Mild Fear"
                    elif primary <= 55:
                        label = "Neutral"
                    elif primary <= 75:
                        label = "Greed"
                    elif primary <= 90:
                        label = "High Greed"
                    else:
                        label = "Extreme Greed"

                    return {
                        "coin": coin_id,
                        "symbol": symbol,
                        "value_15m": v15,
                        "value_1h": v1h,
                        "value_4h": v4h,
                        "value_1d": v1d,
                        "label": label,
                        "source": "cfgi.io",
                    }

                return None

        except Exception as e:
            logger.debug("cfgi_error", symbol=symbol, error=str(e))
            return None

    def get_batch_fear_greed(self, symbols: list[str]) -> dict[str, dict]:
        """
        Get Fear & Greed for multiple coins.

        Returns {symbol: fear_greed_data} for each available coin.
        """
        results = {}
        for symbol in symbols:
            fg = self.get_coin_fear_greed(symbol)
            if fg:
                results[symbol] = fg

        if results:
            logger.info(
                "cfgi_batch_complete",
                symbols_requested=len(symbols),
                symbols_returned=len(results),
            )

        return results
