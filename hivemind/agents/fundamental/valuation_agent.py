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
            "You evaluate crypto VALUATION: market cap, FDV/MCap, supply ratio, ATH distance.\n"
            "You MUST pick BULLISH or BEARISH. Conviction 0 if no CoinGecko data.\n\n"
            "QUANTITATIVE DECISION RULES:\n"
            "- ATH distance > -80% (deep discount) AND supply > 70% circulating → BULLISH conviction 8-9\n"
            "- ATH distance -50% to -80% AND supply > 50% → BULLISH conviction 6-7\n"
            "- ATH distance -20% to -50% → conviction 4-5 BULLISH\n"
            "- ATH distance > -10% (near ATH) → conviction 4-5 BEARISH (extended)\n"
            "- ATH distance > -10% AND FDV/MCap > 2.0 → BEARISH conviction 6-7 (dilution risk)\n\n"
            "DILUTION MODIFIERS:\n"
            "- FDV/MCap < 1.3 → low dilution, add +1 conviction if BULLISH\n"
            "- FDV/MCap 1.3-2.5 → moderate dilution, no modifier\n"
            "- FDV/MCap > 2.5 → high dilution risk, add +1 conviction if BEARISH\n"
            "- Supply < 50% circulating → severe unlock risk, add +1 BEARISH\n\n"
            "NO DATA: If no CoinGecko data shown, give conviction 0.\n"
            "RULES: State ATH distance %, FDV/MCap ratio, supply %. 2 sentences max."
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

        if not coingecko:
            prompt += "\n** NO COINGECKO DATA AVAILABLE. Give conviction 0. **\n"

        prompt += "\nPredict valuation direction."
        return prompt
