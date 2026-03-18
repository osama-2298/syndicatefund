"""
Multi-exchange funding rate comparison — the edge that makes carry arb work.

Fetches current funding rates from 4 exchanges (all free, no auth):
  - Binance Futures (existing)
  - OKX Perpetual Swaps
  - Bybit Linear Perpetuals
  - Bitget USDT Futures

When exchange A pays +0.03% and exchange B charges -0.01%, there's a
0.04% carry spread every 8 hours. At 3x daily that's ~44% annualized.
Even conservative spreads of 0.01% = ~11% annualized with near-zero directional risk.

All endpoints are public, no API keys required.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


# ── Symbol mapping per exchange ──
# Each exchange uses different naming conventions for perpetual contracts.

BINANCE_SYMBOLS: dict[str, str] = {
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT", "BNB": "BNBUSDT",
    "XRP": "XRPUSDT", "DOGE": "DOGEUSDT", "ADA": "ADAUSDT", "AVAX": "AVAXUSDT",
    "LINK": "LINKUSDT", "DOT": "DOTUSDT", "UNI": "UNIUSDT", "NEAR": "NEARUSDT",
    "APT": "APTUSDT", "SUI": "SUIUSDT", "ARB": "ARBUSDT", "OP": "OPUSDT",
    "PEPE": "PEPEUSDT", "WIF": "WIFUSDT", "BONK": "BONKUSDT", "AAVE": "AAVEUSDT",
    "INJ": "INJUSDT", "SEI": "SEIUSDT", "FET": "FETUSDT", "RENDER": "RENDERUSDT",
}

OKX_SYMBOLS: dict[str, str] = {
    "BTC": "BTC-USDT-SWAP", "ETH": "ETH-USDT-SWAP", "SOL": "SOL-USDT-SWAP",
    "BNB": "BNB-USDT-SWAP", "XRP": "XRP-USDT-SWAP", "DOGE": "DOGE-USDT-SWAP",
    "ADA": "ADA-USDT-SWAP", "AVAX": "AVAX-USDT-SWAP", "LINK": "LINK-USDT-SWAP",
    "DOT": "DOT-USDT-SWAP", "UNI": "UNI-USDT-SWAP", "NEAR": "NEAR-USDT-SWAP",
    "APT": "APT-USDT-SWAP", "SUI": "SUI-USDT-SWAP", "ARB": "ARB-USDT-SWAP",
    "OP": "OP-USDT-SWAP", "PEPE": "PEPE-USDT-SWAP", "WIF": "WIF-USDT-SWAP",
    "AAVE": "AAVE-USDT-SWAP", "INJ": "INJ-USDT-SWAP", "SEI": "SEI-USDT-SWAP",
    "FET": "FET-USDT-SWAP", "RENDER": "RENDER-USDT-SWAP",
}

BYBIT_SYMBOLS: dict[str, str] = {
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT", "BNB": "BNBUSDT",
    "XRP": "XRPUSDT", "DOGE": "DOGEUSDT", "ADA": "ADAUSDT", "AVAX": "AVAXUSDT",
    "LINK": "LINKUSDT", "DOT": "DOTUSDT", "UNI": "UNIUSDT", "NEAR": "NEARUSDT",
    "APT": "APTUSDT", "SUI": "SUIUSDT", "ARB": "ARBUSDT", "OP": "OPUSDT",
    "PEPE": "PEPEUSDT", "WIF": "WIFUSDT", "BONK": "BONKUSDT", "AAVE": "AAVEUSDT",
    "INJ": "INJUSDT", "SEI": "SEIUSDT", "FET": "FETUSDT", "RENDER": "RENDERUSDT",
}

BITGET_SYMBOLS: dict[str, str] = {
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT", "BNB": "BNBUSDT",
    "XRP": "XRPUSDT", "DOGE": "DOGEUSDT", "ADA": "ADAUSDT", "AVAX": "AVAXUSDT",
    "LINK": "LINKUSDT", "DOT": "DOTUSDT", "UNI": "UNIUSDT", "NEAR": "NEARUSDT",
    "APT": "APTUSDT", "SUI": "SUIUSDT", "ARB": "ARBUSDT", "OP": "OPUSDT",
    "PEPE": "PEPEUSDT", "WIF": "WIFUSDT", "AAVE": "AAVEUSDT", "INJ": "INJUSDT",
    "SEI": "SEIUSDT", "FET": "FETUSDT", "RENDER": "RENDERUSDT",
}


class MultiExchangeRates:
    """Fetch and compare funding rates across 4 major exchanges."""

    def __init__(self) -> None:
        self._client = httpx.Client(timeout=15.0, headers={"Accept": "application/json"})

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> MultiExchangeRates:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # ── Individual exchange fetchers ──

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, max=5))
    def _fetch_binance(self, symbol: str) -> float | None:
        """Fetch current funding rate from Binance Futures."""
        binance_sym = BINANCE_SYMBOLS.get(symbol)
        if not binance_sym:
            return None
        try:
            resp = self._client.get(
                "https://fapi.binance.com/fapi/v1/premiumIndex",
                params={"symbol": binance_sym},
            )
            resp.raise_for_status()
            data = resp.json()
            return float(data.get("lastFundingRate", 0))
        except Exception as e:
            logger.debug("binance_funding_rate_error", symbol=symbol, error=str(e))
            return None

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, max=5))
    def _fetch_okx(self, symbol: str) -> float | None:
        """Fetch current funding rate from OKX."""
        okx_sym = OKX_SYMBOLS.get(symbol)
        if not okx_sym:
            return None
        try:
            resp = self._client.get(
                "https://www.okx.com/api/v5/public/funding-rate",
                params={"instId": okx_sym},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != "0" or not data.get("data"):
                return None
            return float(data["data"][0].get("fundingRate", 0))
        except Exception as e:
            logger.debug("okx_funding_rate_error", symbol=symbol, error=str(e))
            return None

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, max=5))
    def _fetch_bybit(self, symbol: str) -> float | None:
        """Fetch current funding rate from Bybit."""
        bybit_sym = BYBIT_SYMBOLS.get(symbol)
        if not bybit_sym:
            return None
        try:
            resp = self._client.get(
                "https://api.bybit.com/v5/market/tickers",
                params={"category": "linear", "symbol": bybit_sym},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("retCode") != 0 or not data.get("result", {}).get("list"):
                return None
            return float(data["result"]["list"][0].get("fundingRate", 0))
        except Exception as e:
            logger.debug("bybit_funding_rate_error", symbol=symbol, error=str(e))
            return None

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, max=5))
    def _fetch_bitget(self, symbol: str) -> float | None:
        """Fetch current funding rate from Bitget."""
        bitget_sym = BITGET_SYMBOLS.get(symbol)
        if not bitget_sym:
            return None
        try:
            resp = self._client.get(
                "https://api.bitget.com/api/v2/mix/market/current-fund-rate",
                params={"symbol": bitget_sym, "productType": "USDT-FUTURES"},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != "00000" or not data.get("data"):
                return None
            return float(data["data"][0].get("fundingRate", 0))
        except Exception as e:
            logger.debug("bitget_funding_rate_error", symbol=symbol, error=str(e))
            return None

    # ── Cross-exchange comparison ──

    def get_rates_for_symbol(self, symbol: str) -> dict[str, float | None]:
        """Get funding rates from all 4 exchanges for a single symbol.

        Args:
            symbol: Base symbol like "BTC", "ETH", "SOL"

        Returns:
            Dict mapping exchange name to funding rate (decimal).
            None if exchange doesn't support this symbol or API failed.
        """
        return {
            "binance": self._fetch_binance(symbol),
            "okx": self._fetch_okx(symbol),
            "bybit": self._fetch_bybit(symbol),
            "bitget": self._fetch_bitget(symbol),
        }

    def scan_all(self, symbols: list[str] | None = None) -> list[dict[str, Any]]:
        """Scan funding rates across all exchanges for multiple symbols.

        Args:
            symbols: List of base symbols (e.g. ["BTC", "ETH", "SOL"]).
                    Defaults to top 10 by market cap.

        Returns:
            List of comparison dicts sorted by spread (highest first).
        """
        if symbols is None:
            symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK", "SUI"]

        results: list[dict[str, Any]] = []

        for symbol in symbols:
            rates = self.get_rates_for_symbol(symbol)
            time.sleep(0.05)  # Gentle rate limiting

            # Filter out None values
            valid_rates = {ex: r for ex, r in rates.items() if r is not None}

            if len(valid_rates) < 2:
                continue  # Need at least 2 exchanges to compare

            # Find the spread
            max_exchange = max(valid_rates, key=lambda k: valid_rates[k])
            min_exchange = min(valid_rates, key=lambda k: valid_rates[k])
            max_rate = valid_rates[max_exchange]
            min_rate = valid_rates[min_exchange]
            spread = max_rate - min_rate

            # Annualized carry (3 funding periods per day × 365 days)
            annualized_spread_pct = spread * 100 * 3 * 365

            comparison: dict[str, Any] = {
                "symbol": symbol,
                "rates": {ex: round(r * 100, 6) for ex, r in valid_rates.items()},  # as %
                "rates_raw": valid_rates,
                "highest": {"exchange": max_exchange, "rate_pct": round(max_rate * 100, 6)},
                "lowest": {"exchange": min_exchange, "rate_pct": round(min_rate * 100, 6)},
                "spread_pct": round(spread * 100, 6),
                "annualized_spread_pct": round(annualized_spread_pct, 2),
                "exchanges_reporting": len(valid_rates),
                "opportunity": _classify_opportunity(spread),
            }

            # Strategy recommendation
            if spread > 0.0003:  # > 0.03% spread
                comparison["strategy"] = (
                    f"SHORT {symbol} perp on {max_exchange} (paying {max_rate*100:.4f}%), "
                    f"LONG {symbol} perp on {min_exchange} (receiving {abs(min_rate)*100:.4f}%). "
                    f"Collect {spread*100:.4f}% every 8h = {annualized_spread_pct:.1f}% annualized."
                )
            else:
                comparison["strategy"] = "Spread too narrow for profitable carry."

            results.append(comparison)

        # Sort by spread descending (best opportunities first)
        results.sort(key=lambda x: x["spread_pct"], reverse=True)

        return results

    def get_summary(self, symbols: list[str] | None = None) -> dict[str, Any]:
        """Get a high-level summary of cross-exchange funding rate landscape.

        Returns a summary dict with best opportunities, average spreads,
        and exchange-level stats.
        """
        comparisons = self.scan_all(symbols)

        if not comparisons:
            return {
                "status": "no_data",
                "opportunities": [],
                "exchange_stats": {},
            }

        # Find actionable opportunities (spread > 0.01%)
        opportunities = [c for c in comparisons if c["spread_pct"] > 0.01]

        # Exchange-level stats: average rate across all symbols
        exchange_rates: dict[str, list[float]] = {}
        for comp in comparisons:
            for ex, rate_pct in comp["rates"].items():
                exchange_rates.setdefault(ex, []).append(rate_pct)

        exchange_stats = {}
        for ex, rates_list in exchange_rates.items():
            exchange_stats[ex] = {
                "avg_rate_pct": round(sum(rates_list) / len(rates_list), 6),
                "symbols_reporting": len(rates_list),
            }

        return {
            "status": "ok",
            "total_symbols_scanned": len(comparisons),
            "actionable_opportunities": len(opportunities),
            "avg_spread_pct": round(
                sum(c["spread_pct"] for c in comparisons) / len(comparisons), 6
            ),
            "best_opportunity": comparisons[0] if comparisons else None,
            "opportunities": opportunities[:10],  # Top 10
            "exchange_stats": exchange_stats,
            "all_comparisons": comparisons,
        }


def _classify_opportunity(spread: float) -> str:
    """Classify a funding rate spread into opportunity tiers."""
    if spread > 0.001:  # > 0.1%
        return "STRONG — High carry spread, likely profitable after fees"
    elif spread > 0.0005:  # > 0.05%
        return "MODERATE — Decent spread, check fee structure"
    elif spread > 0.0002:  # > 0.02%
        return "WEAK — Marginal after fees, only with low-fee accounts"
    else:
        return "NONE — Spread too narrow"
