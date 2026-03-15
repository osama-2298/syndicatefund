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
        self.created_at: float = time.monotonic()  # Snapshot creation time

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
        # Build comprehensive smart money data packet
        smart_money = None
        if coin.derivatives:
            smart_money = {
                "divergence": coin.derivatives.get("smart_money_divergence"),
                "divergence_magnitude": coin.derivatives.get("divergence_magnitude", 0),
            }
            funding = coin.derivatives.get("funding")
            if funding:
                smart_money["funding_sentiment"] = funding.get("sentiment", "UNKNOWN")
                smart_money["funding_rate_pct"] = funding.get("current_rate_pct", 0)
            top_ls = coin.derivatives.get("top_trader_ls")
            if top_ls:
                smart_money["top_trader_ratio"] = top_ls.get("ratio", 1.0)
                smart_money["top_trader_long_pct"] = top_ls.get("long_pct", 50)
                smart_money["top_trader_signal"] = top_ls.get("signal", "UNKNOWN")
            taker = coin.derivatives.get("taker_volume")
            if taker:
                smart_money["taker_buy_sell_ratio"] = taker.get("buy_sell_ratio", 1.0)
                smart_money["taker_signal"] = taker.get("signal", "UNKNOWN")
        # Per-coin Reddit sentiment (more specific than global)
        reddit_coin_sentiment = None
        if self.reddit_sentiment:
            base = symbol.replace("USDT", "")
            cs = self.reddit_sentiment.get("coin_sentiment", {})
            if base in cs:
                reddit_coin_sentiment = cs[base]

        return {
            "fear_greed": self.fear_greed,
            "reddit_sentiment": self.reddit_sentiment,
            "reddit_coin_sentiment": reddit_coin_sentiment,
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
            "has_chain_data": coin.chain_tvl is not None,
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

    # ─── Generic Data Slicing ───

    _DATA_RESOLVERS: dict[str, Any] = {}  # Populated at class level below

    def for_team(self, data_keys: list[str], symbol: str) -> dict[str, Any]:
        """Generic data slicing for any team based on declared data requirements."""
        coin = self.coins.get(symbol)
        if coin is None:
            return {}
        result = {}
        for key in data_keys:
            resolver = self._DATA_RESOLVERS.get(key)
            if resolver:
                try:
                    result[key] = resolver(self, coin, symbol)
                except Exception:
                    result[key] = None
        return result


# Data key registry — maps string keys to data accessors for dynamic team slicing
# Each resolver takes (snapshot, coin, symbol) and returns the data
MarketSnapshot._DATA_RESOLVERS = {
    "indicators_4h": lambda snap, coin, sym: coin.indicators_4h,
    "indicators_1h": lambda snap, coin, sym: coin.indicators_1h,
    "indicators_1d": lambda snap, coin, sym: coin.indicators_1d,
    "indicators_1w": lambda snap, coin, sym: coin.indicators_1w,
    "price_history_4h": lambda snap, coin, sym: coin.price_history_4h,
    "price_history_1d": lambda snap, coin, sym: coin.price_history_1d,
    "stats_24h": lambda snap, coin, sym: coin.stats_24h,
    "order_book": lambda snap, coin, sym: coin.order_book,
    "derivatives": lambda snap, coin, sym: coin.derivatives,
    "fear_greed": lambda snap, coin, sym: snap.fear_greed,
    "reddit_sentiment": lambda snap, coin, sym: snap.reddit_sentiment,
    "reddit_coin_sentiment": lambda snap, coin, sym: (
        snap.reddit_sentiment.get("coin_sentiment", {}).get(sym.replace("USDT", ""))
        if snap.reddit_sentiment else None
    ),
    "trending": lambda snap, coin, sym: snap.trending_coins,
    "coingecko_coin": lambda snap, coin, sym: coin.coingecko,
    "smart_money": lambda snap, coin, sym: (
        {
            "divergence": coin.derivatives.get("smart_money_divergence"),
            "divergence_magnitude": coin.derivatives.get("divergence_magnitude", 0),
            "funding": coin.derivatives.get("funding"),
            "top_trader_ls": coin.derivatives.get("top_trader_ls"),
            "taker_volume": coin.derivatives.get("taker_volume"),
        } if coin.derivatives else None
    ),
    "global_data": lambda snap, coin, sym: snap.global_market,
    "btc_onchain": lambda snap, coin, sym: snap.btc_onchain,
    "defi_summary": lambda snap, coin, sym: snap.defi_summary,
    "top_protocols": lambda snap, coin, sym: snap.top_protocols,
    "whale_flows": lambda snap, coin, sym: snap.whale_flows,
    "prediction_markets": lambda snap, coin, sym: snap.prediction_markets,
    "paprika_global": lambda snap, coin, sym: snap.paprika_global,
    "paprika_coin": lambda snap, coin, sym: coin.paprika,
    "chain_tvl": lambda snap, coin, sym: coin.chain_tvl,
    "indicators": lambda snap, coin, sym: coin.indicators_4h,  # Alias
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

        # ── 1. Binance: multi-timeframe candles + indicators per coin (PARALLEL) ──
        from concurrent.futures import ThreadPoolExecutor

        def _fetch_coin_data(symbol: str) -> tuple[str, CoinData]:
            """Fetch all timeframe data for one coin. Thread-safe — uses its own BinanceClient."""
            client = BinanceClient()
            coin = CoinData(symbol)
            try:
                coin.stats_24h = client.get_24h_stats(symbol=symbol)
                coin.current_price = float(coin.stats_24h["close"])

                # Fetch 4 timeframes (each independent)
                try:
                    c4h = client.get_klines(symbol=symbol, interval="4h", limit=200)
                    coin.indicators_4h = compute_indicators(c4h, symbol)
                    coin.price_history_4h = format_price_history(c4h, last_n=20)
                except Exception:
                    pass
                try:
                    c1h = client.get_klines(symbol=symbol, interval="1h", limit=200)  # 200 for SMA200
                    coin.indicators_1h = compute_indicators(c1h, symbol)
                except Exception:
                    pass
                try:
                    c1d = client.get_klines(symbol=symbol, interval="1d", limit=200)
                    coin.indicators_1d = compute_indicators(c1d, symbol)
                    coin.price_history_1d = format_price_history(c1d, last_n=20)
                except Exception:
                    pass
                try:
                    c1w = client.get_klines(symbol=symbol, interval="1w", limit=200)  # 200 for SMA200 (~4 years)
                    coin.indicators_1w = compute_indicators(c1w, symbol)
                except Exception:
                    pass
                try:
                    coin.order_book = client.get_order_book(symbol=symbol, limit=20)
                except Exception:
                    pass
            except Exception:
                pass
            finally:
                client.close()
            return symbol, coin

        t0 = time.monotonic()
        # Fetch all coins in parallel (each creates its own HTTP client)
        with ThreadPoolExecutor(max_workers=min(len(symbols), 8)) as pool:
            results = list(pool.map(lambda s: _fetch_coin_data(s), symbols))
        for symbol, coin in results:
            snapshot.coins[symbol] = coin
        snapshot.fetch_times["binance"] = round(time.monotonic() - t0, 2)

        # ── 2-8. All enrichment sources IN PARALLEL ──
        # These are all independent of each other. Run them concurrently.
        t0_enrich = time.monotonic()

        def _enrich_coingecko():
            gecko = CoinGeckoClient()
            try:
                # Batch endpoint: ONE call for all coins (replaces N individual calls)
                batch = gecko.get_coins_batch(symbols)
                for sym, data in batch.items():
                    if sym in snapshot.coins:
                        snapshot.coins[sym].coingecko = data
                        if sym == "BTCUSDT":
                            changes = data.get("price_changes", {})
                            snapshot.btc_change_30d = changes.get("30d")
            except Exception as e:
                snapshot.errors.append(f"CoinGecko batch: {str(e)[:60]}")
            finally:
                gecko.close()

        def _enrich_blockchain():
            try:
                snapshot.btc_onchain = get_btc_onchain_stats()
            except Exception as e:
                snapshot.errors.append(f"Blockchain.com: {str(e)[:60]}")

        def _enrich_defillama():
            llama = DeFiLlamaClient()
            try:
                if not snapshot.defi_summary:
                    snapshot.defi_summary = llama.get_defi_summary()
                snapshot.top_protocols = llama.get_top_protocols(limit=15)
                for sym in symbols:
                    tvl = llama.get_chain_tvl(sym)
                    if tvl and sym in snapshot.coins:
                        snapshot.coins[sym].chain_tvl = tvl
            except Exception as e:
                snapshot.errors.append(f"DeFiLlama: {str(e)[:60]}")
            finally:
                llama.close()

        def _enrich_derivatives():
            from hivemind.data.derivatives import has_futures
            deriv = DerivativesClient()
            try:
                for sym in symbols:
                    if sym in snapshot.coins and has_futures(sym):
                        try:
                            snapshot.coins[sym].derivatives = deriv.get_full_derivatives_snapshot(sym)
                        except Exception:
                            pass
                    # Coins without futures: derivatives stays None (set in CoinData.__init__)
            finally:
                deriv.close()

        def _enrich_coinpaprika():
            paprika = CoinPaprikaClient()
            try:
                snapshot.paprika_global = paprika.get_global()
                for sym in symbols:
                    try:
                        ticker = paprika.get_ticker(sym)
                        if ticker and sym in snapshot.coins:
                            snapshot.coins[sym].paprika = ticker
                    except Exception:
                        pass
            finally:
                paprika.close()

        def _enrich_whales():
            wt = WhaleTracker()
            try:
                snapshot.whale_flows = wt.get_exchange_flows()
            except Exception as e:
                snapshot.errors.append(f"Whales: {str(e)[:60]}")
            finally:
                wt.close()

        with ThreadPoolExecutor(max_workers=6) as pool:
            enrichment_futures = [
                pool.submit(_enrich_coingecko),
                pool.submit(_enrich_blockchain),
                pool.submit(_enrich_defillama),
                pool.submit(_enrich_derivatives),
                pool.submit(_enrich_coinpaprika),
                pool.submit(_enrich_whales),
            ]
            # Wait for all to complete
            for fut in enrichment_futures:
                try:
                    fut.result()
                except Exception as e:
                    snapshot.errors.append(f"Enrichment: {str(e)[:60]}")

        snapshot.fetch_times["enrichment"] = round(time.monotonic() - t0_enrich, 2)

        return snapshot
