"""
COO Agent — Coin Selection and Agent Assignment.

Scans the entire crypto market and selects the top N coins to analyze.

Selection uses MULTIPLE intelligence sources:
1. Binance 24h stats (volume, volatility, momentum) — opportunity scoring
2. CoinGecko trending — social/search momentum
3. Reddit — what the community is discussing
4. DeFiLlama — where TVL is flowing

The LLM sees all signals and makes the final pick.
"""

from __future__ import annotations

import math
from typing import Any

import structlog

from hivemind.agents.base import BaseLLMCaller
from hivemind.config import LLMProvider
from hivemind.data.models import CoinScore, CoinSelection, MarketRegime

logger = structlog.get_logger()

# Stablecoins and wrapped/leveraged tokens to exclude
EXCLUDED_TOKENS = {
    "USDCUSDT", "BUSDUSDT", "TUSDUSDT", "DAIUSDT", "FDUSDUSDT",
    "USDPUSDT", "USTCUSDT", "EURUSDT", "GBPUSDT", "AEURUSDT",
}

COIN_SELECTION_TOOL = {
    "name": "select_coins",
    "description": (
        "Select which coins the hedge fund should analyze this cycle. "
        "You MUST call this tool with your selection."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "selected_symbols": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The symbols to analyze this cycle (e.g. ['BTCUSDT', 'ETHUSDT']).",
            },
            "reasoning": {
                "type": "string",
                "description": "2-3 sentences on why these coins were selected.",
            },
        },
        "required": ["selected_symbols", "reasoning"],
    },
}


def compute_coin_scores(all_stats: list[dict], max_candidates: int = 30) -> list[CoinScore]:
    """
    Score each coin by opportunity using Binance data.
    Returns top candidates sorted by composite score descending.
    """
    candidates = []
    for stat in all_stats:
        sym = stat["symbol"]
        if sym in EXCLUDED_TOKENS:
            continue
        base = sym.replace("USDT", "")
        if base.endswith("UP") or base.endswith("DOWN") or base.endswith("BEAR") or base.endswith("BULL"):
            continue
        candidates.append(stat)

    if not candidates:
        return []

    max_vol = max(c["quote_volume"] for c in candidates) if candidates else 1

    scored = []
    for stat in candidates:
        symbol = stat["symbol"]
        vol = stat["quote_volume"]
        change = stat["price_change_pct"]
        high = stat["high"]
        low = stat["low"]
        close = stat["close"]

        vol_score = min(1.0, math.log1p(vol) / math.log1p(max_vol)) if max_vol > 0 else 0

        if close > 0:
            daily_range_pct = ((high - low) / close) * 100
        else:
            daily_range_pct = 0

        if 3 <= daily_range_pct <= 8:
            vol_score_adj = 1.0
        elif 1 <= daily_range_pct < 3:
            vol_score_adj = daily_range_pct / 3
        elif 8 < daily_range_pct <= 15:
            vol_score_adj = max(0.3, 1.0 - (daily_range_pct - 8) / 14)
        elif daily_range_pct > 15:
            vol_score_adj = 0.2
        else:
            vol_score_adj = 0.1

        abs_change = abs(change)
        if abs_change > 10:
            momentum_strength = 1.0
        elif abs_change > 5:
            momentum_strength = 0.7
        elif abs_change > 2:
            momentum_strength = 0.4
        elif abs_change > 0.5:
            momentum_strength = 0.2
        else:
            momentum_strength = 0.05

        momentum = momentum_strength if change > 0 else -momentum_strength

        composite = (vol_score * 0.40) + (vol_score_adj * 0.30) + (abs(momentum) * 0.30)

        scored.append(CoinScore(
            symbol=symbol,
            volume_score=round(vol_score, 3),
            volatility_score=round(vol_score_adj, 3),
            momentum_score=round(momentum, 3),
            composite_score=round(composite, 3),
        ))

    scored.sort(key=lambda x: x.composite_score, reverse=True)
    return scored[:max_candidates]


class COOAgent(BaseLLMCaller):
    """
    COO agent — selects which coins to analyze this cycle
    using multiple intelligence sources.
    """

    SYSTEM_PROMPT = (
        "You are the COO of a quantitative crypto hedge fund.\n\n"
        "Your job is to select which coins the fund should analyze this cycle. "
        "You receive data from MULTIPLE sources to make the best picks:\n"
        "1. Binance opportunity scores (volume, volatility, momentum)\n"
        "2. CoinGecko trending coins (what people are searching for)\n"
        "3. Reddit sentiment (what the community is discussing)\n"
        "4. DeFi TVL signals (where capital is flowing)\n\n"
        "SELECTION STRATEGY:\n"
        "- ALWAYS include BTC and ETH — they're our anchors and risk barometers.\n"
        "- Mix large-cap stability with high-opportunity mid-caps.\n"
        "- If a coin is trending on CoinGecko AND has good Binance scores, prioritize it.\n"
        "- If Reddit is discussing a coin with high engagement, it's worth watching.\n"
        "- If a chain is seeing TVL growth, its token deserves attention.\n"
        "- Diversify across sectors: don't pick 5 meme coins or 5 L1s.\n\n"
        "REGIME ADJUSTMENTS:\n"
        "- BULL: More mid/small caps, more momentum plays, 8-10 coins.\n"
        "- RANGING: Focus on volatile names good for mean-reversion, 6-8 coins.\n"
        "- BEAR: Stick to top 10 by market cap, high liquidity, 4-6 coins.\n"
        "- CRISIS: BTC + ETH + maybe 1-2 safe havens. Max 4 coins.\n\n"
        "RULES:\n"
        "- Select from the candidate list only.\n"
        "- Keep reasoning to 2-3 sentences.\n"
        "- In CRISIS, you may select fewer coins than requested."
    )

    def select(
        self,
        all_stats: list[dict],
        regime: MarketRegime,
        max_coins: int = 10,
        extra_intelligence: dict | None = None,
    ) -> CoinSelection:
        """
        Select which coins to analyze this cycle.
        extra_intelligence can include trending, reddit, defi data.
        """
        scored = compute_coin_scores(all_stats)
        if not scored:
            return CoinSelection(
                selected_coins=[],
                scores=[],
                reasoning="No tradeable coins found.",
            )

        prompt = self._build_prompt(scored, regime, max_coins, extra_intelligence)

        try:
            raw = self._call_llm_with_tool(self.SYSTEM_PROMPT, prompt, COIN_SELECTION_TOOL)
        except Exception as e:
            logger.error("coo_coin_selection_failed", error=str(e))
            fallback = [s.symbol for s in scored[:max_coins]]
            if "BTCUSDT" not in fallback and any(s.symbol == "BTCUSDT" for s in scored):
                fallback[-1] = "BTCUSDT"
            return CoinSelection(
                selected_coins=fallback,
                scores=scored[:max_coins],
                reasoning=f"LLM selection failed, using top {max_coins} by composite score.",
            )

        selected = raw["selected_symbols"]
        selected_set = set(selected)
        selected_scores = [s for s in scored if s.symbol in selected_set]

        return CoinSelection(
            selected_coins=selected,
            scores=selected_scores,
            reasoning=raw["reasoning"],
        )

    def _build_prompt(
        self,
        scored: list[CoinScore],
        regime: MarketRegime,
        max_coins: int,
        extra: dict | None = None,
    ) -> str:
        prompt = (
            f"Select {max_coins} coins for this cycle.\n\n"
            f"CURRENT REGIME: {regime.value.upper()}\n\n"
        )

        # ── Source 1: Binance opportunity scores ──
        prompt += (
            f"=== BINANCE OPPORTUNITY SCORES (top 25) ===\n"
            f"{'#':<4} {'Symbol':<12} {'Score':>7} {'Volume':>7} "
            f"{'Volat':>7} {'Mom':>7}\n"
            f"{'─' * 48}\n"
        )

        for i, coin in enumerate(scored[:25], 1):
            mom_sign = "+" if coin.momentum_score > 0 else ""
            prompt += (
                f"{i:<4} {coin.symbol:<12} {coin.composite_score:>7.3f} "
                f"{coin.volume_score:>7.3f} {coin.volatility_score:>7.3f} "
                f"{mom_sign}{coin.momentum_score:>6.3f}\n"
            )

        # ── Source 2: CoinGecko trending ──
        if extra and extra.get("trending"):
            trending = extra["trending"]
            prompt += f"\n=== COINGECKO TRENDING (social/search momentum) ===\n"
            for i, t in enumerate(trending[:10], 1):
                name = t.get("name", "?")
                sym = t.get("symbol", "?")
                rank = t.get("market_cap_rank", "?")
                change = t.get("price_change_24h_pct", 0)
                change_str = f"{change:+.1f}%" if isinstance(change, (int, float)) else "?"
                prompt += f"  {i}. {name} ({sym}) — rank #{rank}, 24h {change_str}\n"

        # ── Source 3: Reddit sentiment ──
        if extra and extra.get("reddit_sentiment"):
            rs = extra["reddit_sentiment"]
            ratio = rs.get("sentiment_ratio", 0.5)
            engagement = rs.get("engagement_level", "?")
            top_posts = rs.get("top_posts", [])
            prompt += (
                f"\n=== REDDIT SENTIMENT (r/bitcoin + r/cryptocurrency) ===\n"
                f"  Sentiment: {ratio:.0%} bullish | Engagement: {engagement}\n"
            )
            if top_posts:
                prompt += "  Hot topics:\n"
                for p in top_posts[:3]:
                    prompt += f"    - \"{p['title']}\" ({p['score']} upvotes)\n"

        # ── Source 4: DeFi TVL signals ──
        if extra and extra.get("defi_summary"):
            ds = extra["defi_summary"]
            top5 = ds.get("top_5_chains", [])
            if top5:
                prompt += f"\n=== DEFI TVL — WHERE CAPITAL IS FLOWING ===\n"
                for c in top5:
                    prompt += f"  {c['name']}: ${c['tvl']:,.0f} ({c['pct']}%)\n"

        # ── Source 5: Fear & Greed ──
        if extra and extra.get("fear_greed"):
            fg = extra["fear_greed"]
            prompt += (
                f"\n=== MARKET FEAR & GREED ===\n"
                f"  Current: {fg['current_value']}/100 ({fg['current_label']})\n"
                f"  Trend: {fg.get('trend', '?')}\n"
            )

        # ── CEO Strategic Directive ──
        if extra and extra.get("ceo_focus_strategy"):
            prompt += f"\n=== CEO DIRECTIVE ===\n"
            prompt += f"  Strategy: {extra['ceo_focus_strategy']}\n"
            weights = extra.get("ceo_sector_weights", {})
            if weights:
                parts = []
                for sector, w in sorted(weights.items(), key=lambda x: -x[1]):
                    if w >= 1.3:
                        parts.append(f"{sector} OVERWEIGHT({w:.1f}x)")
                    elif w <= 0.5:
                        parts.append(f"{sector} UNDERWEIGHT({w:.1f}x)")
                    elif w == 0:
                        parts.append(f"{sector} AVOID")
                prompt += f"  Sector Weights: {', '.join(parts)}\n"
            prompt += "  Follow the CEO's directive when selecting coins.\n"

        prompt += (
            f"\nSelect {max_coins} symbols. Use ALL the intelligence above. "
            f"Always include BTC + ETH. Diversify sectors. "
            f"Prioritize coins that appear in MULTIPLE sources and align with the CEO's strategy."
        )
        return prompt
