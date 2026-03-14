"""
Technical Signal Agent — analyzes the 4-HOUR (4H) timeframe.
Answers: "Is there a tradable setup right now?"

This is Screen 2 of Elder's Triple Screen: THE WAVE.
It identifies setups within the trend — pullbacks, breakouts, divergences.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType, TechnicalIndicators
from hivemind.agents.technical.technical_agent import compute_technical_scores


class TechnicalSignalAgent(BaseAgent):
    """4-Hour (4H) signal analysis — the primary trading timeframe."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.TECHNICAL

    @property
    def system_prompt(self) -> str:
        return (
            "You are the SIGNAL analyst. You read the 4-HOUR (4H) chart — the trading timeframe.\n"
            "You MUST pick BULLISH or BEARISH. Conviction 0 only if data is truly unavailable.\n\n"
            "QUANTITATIVE DECISION RULES:\n"
            "- If composite > 0.4 AND volume_ratio > 1.3 AND RSI 40-70 → conviction 8-9\n"
            "- If composite > 0.15 AND 2+ sub-scores positive → conviction 6-7\n"
            "- If composite 0.0-0.15 → conviction 4-5 in the composite direction\n"
            "- If composite -0.15 to 0.0 → conviction 4-5 BEARISH\n"
            "- If composite < -0.15 AND 2+ sub-scores negative → conviction 6-7 BEARISH\n"
            "- If composite < -0.4 AND volume confirms → conviction 8-9 BEARISH\n\n"
            "DERIVATIVES MODIFIERS:\n"
            "- Funding rate > +0.05% → add +1 conviction if BEARISH (longs overcrowded)\n"
            "- Funding rate < -0.05% → add +1 conviction if BULLISH (shorts overcrowded)\n"
            "- Taker buy/sell > 1.1 → add +1 if BULLISH\n"
            "- Taker buy/sell < 0.9 → add +1 if BEARISH\n"
            "- Order book bid_ratio > 0.6 → add +1 if BULLISH\n\n"
            "RULES: Reference specific composite score and derivatives values. 2 sentences max."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        indicators = market_data.get("indicators")
        stats = market_data.get("stats_24h", {})

        if indicators is None:
            return f"No 4H indicators for {self.profile.symbol}."

        scores = compute_technical_scores(indicators, stats)
        price = scores["current_price"]

        prompt = (
            f"Identify if there is a tradable setup for {self.profile.symbol} on the 4H chart.\n\n"
            f"=== 4H TECHNICAL SCORES ===\n"
            f"Price: ${price:,.2f}\n"
            f"COMPOSITE: {scores['composite_score']:+.3f} ({scores['composite_label']})\n"
            f"Trend: {scores['trend_score']:+.3f} | Momentum: {scores['momentum_score']:+.3f} | Volume: {scores['volume_score']:+.3f}\n"
        )
        if "rsi" in scores:
            prompt += f"RSI(14): {scores['rsi']:.1f} [{scores.get('rsi_zone', '')}]\n"
        if "macd_crossover" in scores:
            prompt += f"MACD: {scores['macd_crossover']}\n"
        if "bb_zone" in scores:
            prompt += f"BB Zone: {scores['bb_zone']}\n"

        order_book = market_data.get("order_book")
        if order_book:
            prompt += f"\nOrder Book: {order_book['pressure']} (bid ratio: {order_book['bid_ratio']:.3f})\n"

        derivatives = market_data.get("derivatives")
        if derivatives:
            funding = derivatives.get("funding", {})
            taker = derivatives.get("taker_volume", {})
            if funding:
                prompt += f"Funding: {funding.get('current_rate_pct', 0):+.4f}% — {funding.get('sentiment', '')}\n"
            if taker:
                prompt += f"Taker: {taker.get('buy_sell_ratio', 1):.3f} — {taker.get('signal', '')}\n"

        prompt += f"\nIdentify the setup and predict direction."
        return prompt
