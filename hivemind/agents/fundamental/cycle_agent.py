"""Cycle Position Agent — where is this asset in its market cycle? REAL ANALYST."""

from __future__ import annotations
from typing import Any
from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class CyclePositionAgent(BaseAgent):
    @property
    def team_type(self) -> TeamType:
        return TeamType.FUNDAMENTAL

    @property
    def system_prompt(self) -> str:
        return (
            "You are a macro cycle analyst at a crypto hedge fund. "
            "You determine where an asset sits in the Wyckoff market cycle: "
            "accumulation → markup → distribution → markdown.\n\n"
            "ANALYZE the data — don't just check if price is above/below SMA200.\n\n"
            "What a great cycle analyst considers:\n"
            "- Price vs SMA200 tells you the PHASE, not just direction.\n"
            "  +5% above = early markup. +30% above = mid-to-late markup. +50% = distribution risk.\n"
            "  -5% below = early markdown. -30% = deep markdown. -50% = potential capitulation/accumulation.\n"
            "- MA alignment confirms the phase: all aligned up = markup confirmed.\n"
            "- Volume PATTERN matters: rising volume in markup = healthy. Climactic volume at highs = distribution.\n"
            "- Weekly indicators (if available) give the true macro picture.\n"
            "- History: BTC bear markets bottom at -77% to -87% from ATH. Alt bears: -90% to -97%.\n\n"
            "You MUST pick BULLISH or BEARISH.\n"
            "Accumulation/early markup = BULLISH. Distribution/markdown = BEARISH."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        indicators = market_data.get("indicators")
        indicators_1d = market_data.get("indicators_1d")
        indicators_1w = market_data.get("indicators_1w")
        stats = market_data.get("stats_24h", {})
        coingecko = market_data.get("coingecko_coin")

        ind = indicators_1d or indicators
        if ind is None:
            return f"No indicators for {self.profile.symbol}. Give conviction 0."

        price = float(stats.get("close", 0))
        prompt = f"Where is {self.profile.symbol} in its market cycle?\n\n"

        prompt += "=== CYCLE INDICATORS ===\n"
        # SMA200 relationship (the key cycle indicator)
        if ind.sma_200 and price:
            pct = ((price - ind.sma_200) / ind.sma_200) * 100
            prompt += f"Price vs SMA200: {pct:+.1f}% (${price:,.2f} vs ${ind.sma_200:,.2f})\n"
        elif ind.sma_50 and price:
            pct50 = ((price - ind.sma_50) / ind.sma_50) * 100
            prompt += f"Price vs SMA50: {pct50:+.1f}% (SMA200 not available)\n"

        # MA alignment
        if ind.sma_20 and ind.sma_50:
            prompt += f"SMA20: ${ind.sma_20:,.2f} | SMA50: ${ind.sma_50:,.2f}"
            if ind.sma_200:
                prompt += f" | SMA200: ${ind.sma_200:,.2f}"
            prompt += "\n"

        # Volume and RSI for cycle context
        if ind.rsi_14 is not None:
            prompt += f"RSI(14): {ind.rsi_14:.1f}\n"
        if ind.volume_ratio is not None:
            prompt += f"Volume: {ind.volume_ratio:.2f}x average\n"

        # Weekly data for macro cycle
        if indicators_1w:
            prompt += f"\nWEEKLY CONTEXT:\n"
            if indicators_1w.sma_50 and indicators_1w.sma_200:
                prompt += f"  Weekly SMA50: ${indicators_1w.sma_50:,.2f} | SMA200: ${indicators_1w.sma_200:,.2f}\n"
                if indicators_1w.sma_50 > indicators_1w.sma_200:
                    prompt += f"  Weekly MAs: BULLISH alignment (macro uptrend)\n"
                else:
                    prompt += f"  Weekly MAs: BEARISH alignment (macro downtrend)\n"
            if indicators_1w.rsi_14:
                prompt += f"  Weekly RSI: {indicators_1w.rsi_14:.1f}\n"

        # ATH context from CoinGecko
        if coingecko:
            ath_dist = coingecko.get("ath_distance_pct", 0)
            prompt += f"\nATH Distance: {ath_dist:+.1f}%\n"
            changes = coingecko.get("price_changes", {})
            if changes.get("30d"):
                prompt += f"30-day change: {changes['30d']:+.1f}%\n"
            if changes.get("200d"):
                prompt += f"200-day change: {changes['200d']:+.1f}%\n"

        prompt += "\nWhat phase is this asset in? Accumulation, markup, distribution, or markdown? Why?"
        return prompt
