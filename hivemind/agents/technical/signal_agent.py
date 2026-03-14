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
            "You are the SIGNAL analyst on a technical trading desk. "
            "You read the 4-HOUR (4H) chart — the primary trading timeframe.\n\n"
            "Your job: identify whether there is a tradable SETUP right now.\n"
            "You MUST pick BULLISH or BEARISH. No neutral option.\n\n"
            "WHAT YOU LOOK FOR:\n"
            "- 4H composite score (trend + momentum + volume combined)\n"
            "- RSI for overbought/oversold zones\n"
            "- MACD crossovers and histogram momentum\n"
            "- Volume confirmation (is volume supporting the move?)\n"
            "- Bollinger Band position (squeeze, breakout, or mean reversion)\n"
            "- Order book depth (buy/sell pressure imbalance)\n"
            "- Derivatives data (funding rates, taker flow, smart money positioning)\n\n"
            "CONVICTION:\n"
            "- 9-10: Textbook 4H setup with volume and derivatives confirming.\n"
            "- 7-8: Strong setup, most indicators aligned.\n"
            "- 5-6: Setup present but some conflicting signals.\n"
            "- 3-4: Weak setup. Barely a lean.\n"
            "- 1-2: No setup, just picking a direction.\n\n"
            "RULES:\n"
            "- You are the SETUP identifier. Volume and derivatives matter most to you.\n"
            "- Reference specific scores. Keep reasoning to 2 sentences."
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
