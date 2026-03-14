"""
Data Layer — The single source of truth for all market data.

ARCHITECTURE:
  9 Data Sources → DataLayer.fetch_all() → MarketSnapshot → team-specific slices

  Each agent team gets ONLY the data relevant to its discipline:
    Technical  ← Binance candles + indicators + order book + derivatives (funding, OI, taker flow)
    Sentiment  ← Reddit (10 subs) + Fear&Greed + CoinGecko trending + smart money divergence
    Fundamental← CoinGecko per-coin + CoinPaprika (beta, multi-timeframe) + market cap data
    Macro      ← CoinGecko global + CoinPaprika global + BTC dominance + market cap ATH distance
    On-Chain   ← Blockchain.com (BTC network) + DeFiLlama (TVL, protocols)

  Agents NEVER see data outside their discipline.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from hivemind.data.binance_client import BinanceClient
from hivemind.data.blockchain import get_btc_onchain_stats
from hivemind.data.coingecko import CoinGeckoClient
from hivemind.data.coinpaprika import CoinPaprikaClient
from hivemind.data.defi_llama import DeFiLlamaClient
from hivemind.data.derivatives import DerivativesClient
from hivemind.data.models import TechnicalIndicators
from hivemind.data.polymarket import PolymarketClient
from hivemind.data.whales import WhaleTracker
from hivemind.data.technical_indicators import compute_indicators, format_price_history

logger = structlog.get_logger()


class CoinData:
    """All raw data for a single coin, organized by source and timeframe."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.current_price: float = 0.0

        # From Binance — multi-timeframe candle data
        self.stats_24h: dict = {}
        self.indicators_1h: TechnicalIndicators | None = None
        self.indicators_4h: TechnicalIndicators | None = None  # Primary timeframe
        self.indicators_1d: TechnicalIndicators | None = None
        self.indicators_1w: TechnicalIndicators | None = None
        self.price_history_4h: str = ""
        self.price_history_1d: str = ""

        # From CoinGecko
        self.coingecko: dict | None = None

        # From Binance order book
        self.order_book: dict | None = None

        # From Binance Futures (derivatives)
        self.derivatives: dict | None = None

        # From CoinPaprika
        self.paprika: dict | None = None

        # From DeFiLlama
        self.chain_tvl: dict | None = None

    @property
    def indicators(self) -> TechnicalIndicators | None:
        """Backward compat — returns the primary (4h) indicators."""
        return self.indicators_4h

        # From CoinPaprika
        self.paprika: dict | None = None

        # From DeFiLlama
        self.chain_tvl: dict | None = None


class MarketSnapshot:
    """
    Complete market snapshot — everything all agents need for one cycle.
    Fetched once, then sliced per-team per-coin.
    """

    def __init__(self) -> None:
        self.coins: dict[str, CoinData] = {}

        # Global data by source
        self.fear_greed: dict | None = None
        self.reddit_sentiment: dict | None = None
        self.global_market: dict = {}
        self.trending_coins: list[dict] = []
        self.btc_onchain: dict | None = None
        self.defi_summary: dict | None = None
        self.top_protocols: list[dict] = []
        self.btc_change_30d: float | None = None
        self.paprika_global: dict | None = None
        self.prediction_markets: dict | None = None  # Polymarket (Fed, crypto, economy)
        self.whale_flows: dict | None = None  # Exchange wallet balances

        # Metadata
        self.fetch_times: dict[str, float] = {}
        self.errors: list[str] = []

    # ─── Team-Specific Data Packets ───
    # Each method returns ONLY the data that team needs.
    # This is the contract between the data layer and the analysis layer.

    def for_technical(self, symbol: str) -> dict[str, Any]:
        """Technical team sees: multi-timeframe indicators (1D/4H/1H), order book, derivatives."""
        coin = self.coins.get(symbol)
        if coin is None:
            return {}
        return {
            "indicators": coin.indicators_4h,  # Primary (4H)
            "indicators_1h": coin.indicators_1h,  # Entry timing
            "indicators_1d": coin.indicators_1d,  # Trend direction
            "price_history": coin.price_history_4h,
            "stats_24h": coin.stats_24h,
            "order_book": coin.order_book,
            "derivatives": coin.derivatives,
        }

    def for_sentiment(self, symbol: str) -> dict[str, Any]:
        """Sentiment team sees: Reddit, Fear&Greed, trending, smart money signals, crowd positioning."""
        coin = self.coins.get(symbol)
        if coin is None:
            return {}
        # Extract smart money divergence if available
        smart_money = None
        if coin.derivatives:
            smart_money = coin.derivatives.get("smart_money_divergence")
            funding = coin.derivatives.get("funding")
            if funding:
                smart_money = {
                    "divergence": coin.derivatives.get("smart_money_divergence", "ALIGNED"),
                    "funding_sentiment": funding.get("sentiment", "UNKNOWN"),
                    "funding_rate_pct": funding.get("current_rate_pct", 0),
                }
        return {
            "fear_greed": self.fear_greed,
            "reddit_sentiment": self.reddit_sentiment,
            "trending": self.trending_coins,
            "coingecko_coin": coin.coingecko,
            "smart_money": smart_money,
            "indicators": coin.indicators,
            "stats_24h": coin.stats_24h,
        }

    def for_fundamental(self, symbol: str) -> dict[str, Any]:
        """Fundamental team sees: CoinGecko + CoinPaprika + weekly/daily indicators for cycle."""
        coin = self.coins.get(symbol)
        if coin is None:
            return {}
        return {
            "coingecko_coin": coin.coingecko,
            "paprika_coin": coin.paprika,
            "indicators": coin.indicators_4h,
            "indicators_1d": coin.indicators_1d,  # Cycle position
            "indicators_1w": coin.indicators_1w,  # Macro cycle
            "stats_24h": coin.stats_24h,
        }

    def for_macro(self, symbol: str) -> dict[str, Any]:
        """Macro team sees: global markets + prediction markets (Fed, recession) + BTC derivatives."""
        coin = self.coins.get(symbol)
        if coin is None:
            return {}
        btc_derivatives = None
        btc_coin = self.coins.get("BTCUSDT")
        if btc_coin and btc_coin.derivatives:
            btc_derivatives = btc_coin.derivatives
        return {
            "global_data": self.global_market,
            "paprika_global": self.paprika_global,
            "btc_change_30d": self.btc_change_30d,
            "btc_derivatives": btc_derivatives,
            "prediction_markets": self.prediction_markets,
            "stats_24h": coin.stats_24h,
        }

    def for_onchain(self, symbol: str) -> dict[str, Any]:
        """On-Chain team sees: BTC network + DeFiLlama TVL + whale exchange flows."""
        coin = self.coins.get(symbol)
        if coin is None:
            return {}
        return {
            "btc_onchain": self.btc_onchain,
            "chain_tvl": coin.chain_tvl,
            "defi_summary": self.defi_summary,
            "top_protocols": self.top_protocols,
            "whale_flows": self.whale_flows,
        }

    def for_coo(self) -> dict[str, Any]:
        """COO sees: everything needed to pick which coins to analyze."""
        return {
            "trending": self.trending_coins,
            "fear_greed": self.fear_greed,
            "reddit_sentiment": self.reddit_sentiment,
            "defi_summary": self.defi_summary,
        }


class DataLayer:
    """
    Fetches all data from all sources in one coordinated pass.
    Returns a MarketSnapshot that gets sliced per-team.
    """

    def __init__(self) -> None:
        self.binance = BinanceClient()
        self._gecko: CoinGeckoClient | None = None
        self._llama: DeFiLlamaClient | None = None

    def close(self) -> None:
        self.binance.close()
        if self._gecko:
            self._gecko.close()
        if self._llama:
            self._llama.close()

    def __enter__(self) -> DataLayer:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def fetch_all(
        self,
        symbols: list[str],
    ) -> MarketSnapshot:
        """
        Fetch per-coin data at multiple timeframes + all enrichment sources.
        Timeframes: 1H, 4H (primary), 1D, 1W — each team gets its relevant slice.
        """
        snapshot = MarketSnapshot()

        # ── 1. Binance: multi-timeframe candles + indicators per coin ──
        t0 = time.monotonic()
        for symbol in symbols:
            coin = CoinData(symbol)
            try:
                # 24h stats (always needed)
                coin.stats_24h = self.binance.get_24h_stats(symbol=symbol)
                coin.current_price = float(coin.stats_24h["close"])

                # Primary timeframe: 4H (200 candles = ~33 days)
                candles_4h = self.binance.get_klines(symbol=symbol, interval="4h", limit=200)
                coin.indicators_4h = compute_indicators(candles_4h, symbol)
                coin.price_history_4h = format_price_history(candles_4h, last_n=20)

                # Entry timeframe: 1H (100 candles = ~4 days)
                try:
                    candles_1h = self.binance.get_klines(symbol=symbol, interval="1h", limit=100)
                    coin.indicators_1h = compute_indicators(candles_1h, symbol)
                except Exception:
                    pass

                # Trend timeframe: 1D (200 candles = ~200 days)
                try:
                    candles_1d = self.binance.get_klines(symbol=symbol, interval="1d", limit=200)
                    coin.indicators_1d = compute_indicators(candles_1d, symbol)
                    coin.price_history_1d = format_price_history(candles_1d, last_n=20)
                except Exception:
                    pass

                # Macro timeframe: 1W (100 candles = ~2 years)
                try:
                    candles_1w = self.binance.get_klines(symbol=symbol, interval="1w", limit=100)
                    coin.indicators_1w = compute_indicators(candles_1w, symbol)
                except Exception:
                    pass

            except Exception as e:
                snapshot.errors.append(f"Binance {symbol}: {str(e)[:60]}")

            # Order book depth
            try:
                coin.order_book = self.binance.get_order_book(symbol=symbol, limit=20)
            except Exception:
                pass

            snapshot.coins[symbol] = coin
        snapshot.fetch_times["binance"] = round(time.monotonic() - t0, 2)

        # ── 2. CoinGecko per-coin enrichment ──
        t0 = time.monotonic()
        self._gecko = CoinGeckoClient()
        try:
            for symbol in symbols:
                try:
                    coin_data = self._gecko.get_coin(symbol)
                    if coin_data:
                        snapshot.coins[symbol].coingecko = coin_data
                        if symbol == "BTCUSDT":
                            changes = coin_data.get("price_changes", {})
                            snapshot.btc_change_30d = changes.get("30d")
                except Exception:
                    pass
        except Exception as e:
            snapshot.errors.append(f"CoinGecko: {str(e)[:60]}")
        finally:
            self._gecko.close()
        snapshot.fetch_times["coingecko"] = round(time.monotonic() - t0, 2)

        # ── 3. Blockchain.com: BTC on-chain stats ──
        t0 = time.monotonic()
        try:
            snapshot.btc_onchain = get_btc_onchain_stats()
        except Exception as e:
            snapshot.errors.append(f"Blockchain.com: {str(e)[:60]}")
        snapshot.fetch_times["blockchain"] = round(time.monotonic() - t0, 2)

        # ── 4. DeFiLlama: per-chain TVL + protocol trends ──
        t0 = time.monotonic()
        self._llama = DeFiLlamaClient()
        try:
            if not snapshot.defi_summary:
                snapshot.defi_summary = self._llama.get_defi_summary()
            snapshot.top_protocols = self._llama.get_top_protocols(limit=15)

            for symbol in symbols:
                tvl_data = self._llama.get_chain_tvl(symbol)
                if tvl_data:
                    snapshot.coins[symbol].chain_tvl = tvl_data
        except Exception as e:
            snapshot.errors.append(f"DeFiLlama: {str(e)[:60]}")
        finally:
            self._llama.close()
        snapshot.fetch_times["defillama"] = round(time.monotonic() - t0, 2)

        # ── 5. Binance Futures: derivatives data (funding, OI, taker flow) ──
        t0 = time.monotonic()
        deriv = DerivativesClient()
        try:
            for symbol in symbols:
                try:
                    snapshot.coins[symbol].derivatives = deriv.get_full_derivatives_snapshot(symbol)
                except Exception:
                    pass  # Not all coins have futures
        except Exception as e:
            snapshot.errors.append(f"Derivatives: {str(e)[:60]}")
        finally:
            deriv.close()
        snapshot.fetch_times["derivatives"] = round(time.monotonic() - t0, 2)

        # ── 6. CoinPaprika: beta values, short-term changes, global macro ──
        t0 = time.monotonic()
        paprika = CoinPaprikaClient()
        try:
            snapshot.paprika_global = paprika.get_global()
            for symbol in symbols:
                try:
                    ticker = paprika.get_ticker(symbol)
                    if ticker:
                        snapshot.coins[symbol].paprika = ticker
                except Exception:
                    pass
        except Exception as e:
            snapshot.errors.append(f"CoinPaprika: {str(e)[:60]}")
        finally:
            paprika.close()
        snapshot.fetch_times["coinpaprika"] = round(time.monotonic() - t0, 2)

        # ── 7. Polymarket: prediction market probabilities ──
        t0 = time.monotonic()
        poly = PolymarketClient()
        try:
            snapshot.prediction_markets = poly.get_all_relevant_markets()
        except Exception as e:
            snapshot.errors.append(f"Polymarket: {str(e)[:60]}")
        finally:
            poly.close()
        snapshot.fetch_times["polymarket"] = round(time.monotonic() - t0, 2)

        # ── 8. Whale tracking: exchange BTC flows ──
        t0 = time.monotonic()
        whales = WhaleTracker()
        try:
            snapshot.whale_flows = whales.get_exchange_flows()
        except Exception as e:
            snapshot.errors.append(f"Whales: {str(e)[:60]}")
        finally:
            whales.close()
        snapshot.fetch_times["whales"] = round(time.monotonic() - t0, 2)

        return snapshot
