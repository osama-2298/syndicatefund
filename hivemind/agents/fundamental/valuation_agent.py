"""Valuation Agent — is this asset cheap or expensive relative to fundamentals?"""

from __future__ import annotations
from typing import Any
from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class ValuationAgent(BaseAgent):
    @property
    def team_type(self) -> TeamType:
        return TeamType.FUNDAMENTAL

    @property
    def system_prompt(self) -> str:
        return (
            "You evaluate crypto VALUATION: market cap rank, FDV/MCap dilution risk, "
            "supply ratio, ATH/ATL distance, and CoinPaprika beta.\n\n"
            "Your job: predict whether this asset is UNDERVALUED (bullish) or OVERVALUED (bearish).\n"
            "You MUST pick BULLISH or BEARISH.\n\n"
            "VALUATION RULES:\n"
            "- >50% below ATH + low dilution risk = lean BULLISH\n"
            "- Near ATH + high FDV/MCap = lean BEARISH\n"
            "- High supply ratio (>90% circulating) = less dilution risk = bullish factor\n"
            "- Low supply ratio (<50%) = major unlock risk = bearish factor\n\n"
            "CONVICTION: 9-10 clear mispricing. 5-6 moderate. 1-2 fairly valued.\n"
            "RULES: Reference specific valuation metrics. 2 sentences."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        coingecko = market_data.get("coingecko_coin", {})
        paprika = market_data.get("paprika_coin", {})
        stats = market_data.get("stats_24h", {})

        prompt = f"Evaluate the valuation of {self.profile.symbol}.\n\n"
        if coingecko:
            prompt += f"Market Cap Rank: #{coingecko.get('market_cap_rank', '?')}\n"
            mcap = coingecko.get("market_cap_usd", 0)
            fdv = coingecko.get("fully_diluted_valuation_usd", 0)
            if mcap and fdv:
                prompt += f"Market Cap: ${mcap:,.0f} | FDV: ${fdv:,.0f} | FDV/MCap: {fdv/mcap:.2f}x\n"
            circ = coingecko.get("circulating_supply")
            total = coingecko.get("total_supply")
            if circ and total and total > 0:
                prompt += f"Supply: {circ/total*100:.1f}% circulating\n"
            prompt += f"ATH Distance: {coingecko.get('ath_distance_pct', 0):+.1f}%\n"
            changes = coingecko.get("price_changes", {})
            if changes:
                prompt += f"Price Changes: {' | '.join(f'{k}: {v:+.1f}%' for k, v in changes.items())}\n"
        if paprika:
            prompt += f"Beta: {paprika.get('beta_value', 0):.3f}\n"
        prompt += "\nPredict valuation direction."
        return prompt
