"""
Quantitative Scoring Engine — Layer 1 of the two-layer signal architecture.

Orchestrates all 5 domain scorers and produces a composite QuantScore
for each symbol. Zero LLM calls. Pure deterministic math.

Domain weights (initial, will be tuned via backtesting):
- Technical: 0.35 (strongest short-term predictive power)
- Sentiment: 0.25 (F&G extremes and funding rate have documented edge)
- Macro: 0.15 (sets the environment, slower-moving)
- On-Chain: 0.15 (leading indicator for medium-term)
- Fundamental: 0.10 (slowest signal, supply dynamics)
"""

from __future__ import annotations

import structlog

from syndicate.data.models import SignalAction  # noqa: F401 — used for documentation
from syndicate.scoring.fundamental_scorer import score_fundamental
from syndicate.scoring.macro_scorer import score_macro
from syndicate.scoring.models import QuantScore
from syndicate.scoring.onchain_scorer import score_onchain
from syndicate.scoring.sentiment_scorer import score_sentiment
from syndicate.scoring.technical_scorer import score_technical

logger = structlog.get_logger()

# Domain weights — initial values, tunable via config or backtest optimization
DEFAULT_WEIGHTS = {
    "technical": 0.35,
    "sentiment": 0.25,
    "macro": 0.15,
    "onchain": 0.15,
    "fundamental": 0.10,
}

# Signal thresholds
BUY_THRESHOLD = 1.0
SELL_THRESHOLD = -0.5

# Confidence mapping
MIN_CONFIDENCE = 0.30
MAX_BUY_CONFIDENCE = 0.90
MAX_SELL_CONFIDENCE = 0.85


class QuantScoringEngine:
    """
    Deterministic scoring engine — zero LLM calls, pure math.

    Produces a QuantScore for each symbol by running 5 domain scorers
    and combining their outputs with configurable weights.
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        buy_threshold: float = BUY_THRESHOLD,
        sell_threshold: float = SELL_THRESHOLD,
    ) -> None:
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def score_all(
        self,
        snapshot: MarketSnapshot,
        symbols: list[str],
        global_data: dict | None = None,
    ) -> dict[str, QuantScore]:
        """
        Score all symbols in parallel (no LLM, pure computation).

        Args:
            snapshot: Full market data snapshot with per-coin data.
            symbols: List of symbols to score.
            global_data: Global market data (F&G, macro, etc.) — shared across all coins.

        Returns:
            {symbol: QuantScore} for each scored symbol.
        """
        global_data = global_data or {}
        results: dict[str, QuantScore] = {}

        # Extract global data once (shared across all coins)
        fear_greed = global_data.get("fear_greed")
        global_macro = global_data.get("global_market")
        defi_data = global_data.get("defi")

        # Compute macro score once (same for all coins in this cycle)
        macro_score_val, macro_components = self._score_macro_global(global_macro)

        for symbol in symbols:
            coin = snapshot.coins.get(symbol)
            if coin is None:
                continue

            try:
                qs = self._score_symbol(
                    symbol=symbol,
                    coin=coin,
                    fear_greed=fear_greed,
                    macro_score_val=macro_score_val,
                    macro_components=macro_components,
                    defi_data=defi_data,
                )
                results[symbol] = qs
            except Exception as e:
                logger.warning("scoring_error", symbol=symbol, error=str(e))
                results[symbol] = QuantScore(symbol=symbol)

        logger.info(
            "quant_scoring_complete",
            symbols_scored=len(results),
            actions={s: qs.action for s, qs in results.items()},
        )

        return results

    def _score_symbol(
        self,
        symbol: str,
        coin,
        fear_greed: dict | None,
        macro_score_val: float,
        macro_components: list,
        defi_data: dict | None,
    ) -> QuantScore:
        """Score a single symbol across all 5 domains."""

        all_components: dict[str, float] = {}

        # ── 1. TECHNICAL ──
        tech_score, tech_comps = score_technical(
            indicators_4h=coin.indicators_4h,
            indicators_1d=coin.indicators_1d,
            current_price=coin.current_price,
        )
        for c in tech_comps:
            all_components[f"tech.{c.name}"] = c.value

        # ── 2. SENTIMENT ──
        # Extract derivatives data from coin
        funding_rate = None
        taker_ratio = None
        top_trader_long_pct = None
        cross_funding = None

        if coin.derivatives:
            funding_rate = coin.derivatives.get("funding_rate")
            taker_ratio = coin.derivatives.get("taker_buy_sell_ratio")
            long_short = coin.derivatives.get("top_trader_long_short_ratio")
            if long_short is not None and long_short > 0:
                top_trader_long_pct = (long_short / (1 + long_short)) * 100

        cross_funding = getattr(coin, "cross_exchange_funding", None) or getattr(coin, "cross_exchange_rates", None)

        sent_score, sent_comps = score_sentiment(
            fear_greed=fear_greed,
            funding_rate=funding_rate,
            cross_exchange_funding=cross_funding,
            taker_buy_sell_ratio=taker_ratio,
            top_trader_long_pct=top_trader_long_pct,
        )
        for c in sent_comps:
            all_components[f"sent.{c.name}"] = c.value

        # ── 3. MACRO (pre-computed, same for all coins) ──
        for c in macro_components:
            all_components[f"macro.{c.name}"] = c.value

        # ── 4. ON-CHAIN ──
        exchange_flow = None
        btc_reserves = None
        btc_reserves_prev = None
        defi_tvl_change = None
        protocols_growing = 0
        protocols_shrinking = 0

        # whale data may be on the snapshot level or coin level depending on pipeline stage
        _whale = getattr(coin, "whale_data", None) or getattr(coin, "whale_flows", None)
        if _whale and isinstance(_whale, dict):
            exchange_flow = _whale.get("flow_direction")
            btc_reserves = _whale.get("total_balance")
            btc_reserves_prev = _whale.get("prev_total_balance")

        if defi_data:
            defi_tvl_change = defi_data.get("tvl_change_24h")
            protocols_growing = defi_data.get("protocols_growing", 0)
            protocols_shrinking = defi_data.get("protocols_shrinking", 0)

        onchain_score, onchain_comps = score_onchain(
            exchange_flow_direction=exchange_flow,
            exchange_btc_reserves=btc_reserves,
            exchange_btc_reserves_prev=btc_reserves_prev,
            defi_tvl_change_24h=defi_tvl_change,
            protocols_growing=protocols_growing,
            protocols_shrinking=protocols_shrinking,
        )
        for c in onchain_comps:
            all_components[f"onchain.{c.name}"] = c.value

        # ── 5. FUNDAMENTAL ──
        market_cap = None
        fdv = None
        circ_supply = None
        max_supply = None
        ath_dist = None
        price_30d = None
        price_200d = None

        # CoinData uses .coingecko (not .coingecko_data)
        cg = getattr(coin, "coingecko", None) or getattr(coin, "coingecko_data", None)
        if cg and isinstance(cg, dict):
            market_cap = cg.get("market_cap")
            fdv = cg.get("fully_diluted_valuation")
            circ_supply = cg.get("circulating_supply")
            max_supply = cg.get("max_supply")
            ath = cg.get("ath")
            if ath and coin.current_price > 0:
                ath_dist = ((coin.current_price - ath) / ath) * 100
            price_30d = cg.get("price_change_percentage_30d_in_currency")
            price_200d = cg.get("price_change_percentage_200d_in_currency")

        fund_score, fund_comps = score_fundamental(
            market_cap=market_cap,
            fully_diluted_valuation=fdv,
            circulating_supply=circ_supply,
            max_supply=max_supply,
            ath_distance_pct=ath_dist,
            price_change_30d=price_30d,
            price_change_200d=price_200d,
        )
        for c in fund_comps:
            all_components[f"fund.{c.name}"] = c.value

        # ── WEIGHTED COMPOSITE ──
        composite = (
            tech_score * self.weights["technical"]
            + sent_score * self.weights["sentiment"]
            + macro_score_val * self.weights["macro"]
            + onchain_score * self.weights["onchain"]
            + fund_score * self.weights["fundamental"]
        )

        # ── DERIVE ACTION + CONFIDENCE ──
        if composite >= self.buy_threshold:
            action = "BUY"
            confidence = min(
                0.50 + (composite - self.buy_threshold) * 0.08,
                MAX_BUY_CONFIDENCE,
            )
        elif composite <= self.sell_threshold:
            action = "SELL"
            confidence = min(
                0.50 + (abs(composite) - abs(self.sell_threshold)) * 0.06,
                MAX_SELL_CONFIDENCE,
            )
        else:
            action = "HOLD"
            confidence = MIN_CONFIDENCE

        # Determine regime from technical indicators
        regime = "unknown"
        if coin.indicators_4h and coin.indicators_4h.adx_14 is not None:
            adx = coin.indicators_4h.adx_14
            if adx > 25:
                regime = "trending"
            elif adx < 20:
                regime = "ranging"
            else:
                regime = "borderline"

        return QuantScore(
            symbol=symbol,
            technical_score=round(tech_score, 4),
            sentiment_score=round(sent_score, 4),
            macro_score=round(macro_score_val, 4),
            onchain_score=round(onchain_score, 4),
            fundamental_score=round(fund_score, 4),
            composite_score=round(composite, 4),
            components=all_components,
            action=action,
            confidence=round(confidence, 4),
            regime=regime,
        )

    def _score_macro_global(self, global_market: dict | None) -> tuple[float, list]:
        """Score global macro environment (computed once per cycle, shared across coins)."""
        if not global_market:
            return 0.0, []

        return score_macro(
            btc_dominance=global_market.get("btc_dominance"),
            btc_dominance_change_24h=global_market.get("btc_dominance_change_24h"),
            total_market_cap=global_market.get("total_market_cap"),
            market_cap_change_24h=global_market.get("market_cap_change_24h"),
            total_volume_24h=global_market.get("total_volume_24h"),
            volume_change_24h=global_market.get("volume_change_24h"),
            btc_price_vs_sma200=global_market.get("btc_price_vs_sma200"),
        )
