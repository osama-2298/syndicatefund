"""
CoinPaprika API client — free, no auth.

Provides unique data not available from CoinGecko:
- Beta values (volatility relative to market)
- 15-minute and 30-minute price changes (faster granularity)
- Market cap ATH data
- Independent cross-validation of CoinGecko data
"""

from __future__ import annotations

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

BASE_URL = "https://api.coinpaprika.com/v1"

# Binance symbol → CoinPaprika ID
SYMBOL_TO_PAPRIKA: dict[str, str] = {
    "BTC": "btc-bitcoin", "ETH": "eth-ethereum", "SOL": "sol-solana",
    "BNB": "bnb-binance-coin", "XRP": "xrp-xrp", "ADA": "ada-cardano",
    "DOGE": "doge-dogecoin", "AVAX": "avax-avalanche", "DOT": "dot-polkadot",
    "LINK": "link-chainlink", "UNI": "uni-uniswap", "ATOM": "atom-cosmos",
    "NEAR": "near-near-protocol", "SUI": "sui-sui", "OP": "op-optimism",
    "ARB": "arb-arbitrum", "AAVE": "aave-aave", "FET": "fet-fetch-ai",
    "RENDER": "rndr-render-token", "TAO": "tao-bittensor",
    "ALGO": "algo-algorand", "XLM": "xlm-stellar",
}


class CoinPaprikaClient:
    """Synchronous CoinPaprika API client."""

    def __init__(self) -> None:
        self._client = httpx.Client(
            base_url=BASE_URL,
            timeout=15.0,
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> CoinPaprikaClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_global(self) -> dict:
        """Get global market data with unique fields."""
        resp = self._client.get("/global")
        resp.raise_for_status()
        data = resp.json()

        return {
            "market_cap_usd": data.get("market_cap_usd", 0),
            "volume_24h_usd": data.get("volume_24h_usd", 0),
            "btc_dominance": data.get("bitcoin_dominance_percentage", 0),
            "cryptocurrencies_count": data.get("cryptocurrencies_number", 0),
            "market_cap_ath": data.get("market_cap_ath_value", 0),
            "market_cap_ath_date": data.get("market_cap_ath_date", ""),
            "market_cap_change_24h": data.get("market_cap_change_24h", 0),
            "volume_change_24h": data.get("volume_24h_change_24h", 0),
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_ticker(self, symbol: str) -> dict | None:
        """Get ticker data with unique fields like beta and short-term changes."""
        base = symbol.replace("USDT", "")
        paprika_id = SYMBOL_TO_PAPRIKA.get(base)
        if paprika_id is None:
            return None

        resp = self._client.get(f"/tickers/{paprika_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()

        quotes = data.get("quotes", {}).get("USD", {})

        return {
            "symbol": symbol,
            "name": data.get("name", ""),
            "rank": data.get("rank", 0),
            "beta_value": data.get("beta_value", 0),  # Unique — volatility vs market
            "price_usd": quotes.get("price", 0),
            "volume_24h": quotes.get("volume_24h", 0),
            "market_cap": quotes.get("market_cap", 0),
            "pct_change_15m": quotes.get("percent_change_15m", 0),
            "pct_change_30m": quotes.get("percent_change_30m", 0),
            "pct_change_1h": quotes.get("percent_change_1h", 0),
            "pct_change_6h": quotes.get("percent_change_6h", 0),
            "pct_change_12h": quotes.get("percent_change_12h", 0),
            "pct_change_24h": quotes.get("percent_change_24h", 0),
            "pct_change_7d": quotes.get("percent_change_7d", 0),
            "pct_change_30d": quotes.get("percent_change_30d", 0),
            "ath_price": quotes.get("ath_price", 0),
            "pct_from_ath": quotes.get("percent_from_price_ath", 0),
        }
