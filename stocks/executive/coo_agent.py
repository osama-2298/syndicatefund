"""
Stock COO Agent — Stock selection from universe, sector diversification.
"""

from __future__ import annotations

from typing import Any

import structlog

from syndicate.agents.base import BaseLLMCaller
from syndicate.data.models import MarketRegime
from stocks.data.models import StockScore, StockSelection
from stocks.data.stock_screener import compute_stock_scores

logger = structlog.get_logger()

STOCK_SELECTION_TOOL = {
    "name": "select_stocks",
    "description": "Select which stocks the hedge fund should analyze this cycle.",
    "input_schema": {
        "type": "object",
        "properties": {
            "selected_symbols": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The stock symbols to analyze (e.g. ['AAPL', 'MSFT'])",
            },
            "reasoning": {
                "type": "string",
                "description": "2-3 sentences on why these stocks were selected.",
            },
        },
        "required": ["selected_symbols", "reasoning"],
    },
}


class StockCOOAgent(BaseLLMCaller):
    """COO agent — selects stocks from universe for analysis."""

    SYSTEM_PROMPT = (
        "You are the COO of a quantitative stock hedge fund.\n\n"
        "Your job is to select which stocks to analyze this cycle from the scored candidates.\n\n"
        "SELECTION STRATEGY:\n"
        "- Include at least 1-2 mega caps (AAPL, MSFT, NVDA) as anchors.\n"
        "- Mix sectors for diversification (don't pick 5 tech stocks).\n"
        "- Prefer stocks with higher composite scores.\n"
        "- If CEO says overweight a sector, include more from that sector.\n"
        "- If Reddit/news is buzzing about a stock with good scores, include it.\n\n"
        "REGIME ADJUSTMENTS:\n"
        "- BULL: More growth/momentum plays, 8-10 stocks.\n"
        "- RANGING: Balanced mix, 6-8 stocks.\n"
        "- BEAR: Large caps, defensives, 4-6 stocks.\n"
        "- CRISIS: Mega caps only, 3-4 stocks.\n\n"
        "Select from the candidate list only."
    )

    def select(
        self,
        all_stats: list[dict],
        regime: MarketRegime,
        max_stocks: int = 10,
        extra_intelligence: dict | None = None,
    ) -> StockSelection:
        scored = compute_stock_scores(all_stats)
        if not scored:
            return StockSelection(selected_stocks=[], scores=[], reasoning="No tradeable stocks found.")

        prompt = self._build_prompt(scored, regime, max_stocks, extra_intelligence)

        try:
            raw = self._call_llm_with_tool(self.SYSTEM_PROMPT, prompt, STOCK_SELECTION_TOOL)
        except Exception as e:
            logger.error("stock_coo_selection_failed", error=str(e))
            fallback = [s.symbol for s in scored[:max_stocks]]
            return StockSelection(
                selected_stocks=fallback, scores=scored[:max_stocks],
                reasoning=f"LLM failed, using top {max_stocks} by score.",
            )

        selected = raw["selected_symbols"]
        selected_set = set(selected)
        selected_scores = [s for s in scored if s.symbol in selected_set]

        return StockSelection(
            selected_stocks=selected,
            scores=selected_scores,
            reasoning=raw["reasoning"],
        )

    def _build_prompt(self, scored: list[StockScore], regime: MarketRegime, max_stocks: int, extra: dict | None) -> str:
        prompt = f"Select {max_stocks} stocks for this cycle.\n\nREGIME: {regime.value.upper()}\n\n"

        prompt += f"=== STOCK SCORES (top 25) ===\n"
        prompt += f"{'#':<4} {'Symbol':<8} {'Score':>7} {'Vol':>7} {'Volat':>7} {'Mom':>7}\n"
        for i, s in enumerate(scored[:25], 1):
            prompt += f"{i:<4} {s.symbol:<8} {s.composite_score:>7.3f} {s.volume_score:>7.3f} {s.volatility_score:>7.3f} {s.momentum_score:>+7.3f}\n"

        if extra:
            if extra.get("reddit_sentiment"):
                rs = extra["reddit_sentiment"]
                mentions = rs.get("stock_mentions", {})
                if mentions:
                    prompt += f"\n=== REDDIT HOT STOCKS ===\n"
                    for ticker, count in list(mentions.items())[:10]:
                        prompt += f"  {ticker}: {count} mentions\n"

            if extra.get("ceo_focus_strategy"):
                prompt += f"\n=== CEO DIRECTIVE ===\n  Strategy: {extra['ceo_focus_strategy']}\n"

            if extra.get("ceo_sector_weights"):
                weights = extra["ceo_sector_weights"]
                overweight = [f"{s} ({w:.1f}x)" for s, w in weights.items() if w > 1.2]
                if overweight:
                    prompt += f"  Overweight: {', '.join(overweight)}\n"

        prompt += f"\nSelect {max_stocks} symbols. Diversify sectors."
        return prompt
