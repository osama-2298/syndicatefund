"""Valuation Agent — is this asset cheap or expensive? REAL ANALYST."""

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
            "You are a fundamental analyst valuing crypto assets. "
            "You assess whether an asset is cheap or expensive based on market cap, "
            "supply dynamics, and distance from ATH/ATL.\n\n"
            "ANALYZE the data — form a value thesis.\n\n"
            "What a great fundamental analyst considers:\n"
            "- Market cap rank: is this a mega-cap (#1-5) or a speculative small-cap?\n"
            "- ATH distance: 80% below ATH could mean deep value OR a dying project.\n"
            "  Context matters: BTC 50% below ATH in a bear = opportunity. Random altcoin 90% below = maybe dead.\n"
            "- FDV/MCap ratio: high FDV means massive supply unlocks ahead = dilution risk.\n"
            "  < 1.3 = low dilution. 1.3-2.5 = moderate. > 2.5 = significant. > 5 = extreme.\n"
            "- Supply: what % is circulating? Less = more unlock risk.\n"
            "- Multi-timeframe price changes (7d, 30d, 200d) = is the trend up or down?\n\n"
            "You MUST pick BULLISH (undervalued) or BEARISH (overvalued).\n"
            "Conviction 0 only if no CoinGecko data available — you cannot value what you cannot see."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        coingecko = market_data.get("coingecko_coin", {})
        paprika = market_data.get("paprika_coin", {})
        stats = market_data.get("stats_24h", {})

        prompt = f"Value {self.profile.symbol} — is it cheap or expensive?\n\n"

        if coingecko:
            prompt += "=== LIVE VALUATION DATA (CoinGecko) ===\n"
            name = coingecko.get("name", self.profile.symbol)
            rank = coingecko.get("market_cap_rank", "?")
            prompt += f"Name: {name} | Rank: #{rank}\n"

            mcap = coingecko.get("market_cap_usd", 0)
            fdv = coingecko.get("fully_diluted_valuation_usd", 0)
            if mcap:
                prompt += f"Market Cap: ${mcap:,.0f}\n"
            if fdv:
                prompt += f"Fully Diluted Val: ${fdv:,.0f}\n"
            if mcap and fdv and mcap > 0:
                ratio = fdv / mcap
                prompt += f"FDV/MCap Ratio: {ratio:.2f}x"
                if ratio > 5:
                    prompt += " — EXTREME dilution risk"
                elif ratio > 2.5:
                    prompt += " — significant dilution"
                elif ratio > 1.3:
                    prompt += " — moderate"
                else:
                    prompt += " — low dilution"
                prompt += "\n"

            circ = coingecko.get("circulating_supply")
            total = coingecko.get("total_supply")
            max_sup = coingecko.get("max_supply")
            if circ and total and total > 0:
                prompt += f"Supply: {circ/total*100:.1f}% circulating"
                if circ/total < 0.5:
                    prompt += " — WARNING: less than half circulating"
                prompt += "\n"
            if max_sup:
                prompt += f"Max Supply: {max_sup:,.0f} (hard cap exists)\n"
            else:
                prompt += f"No hard cap on supply\n"

            ath_dist = coingecko.get("ath_distance_pct", 0)
            prompt += f"\nATH Distance: {ath_dist:+.1f}%\n"

            changes = coingecko.get("price_changes", {})
            if changes:
                prompt += f"\nPrice Performance:\n"
                for period, change in changes.items():
                    if change is not None:
                        prompt += f"  {period}: {change:+.1f}%\n"
        else:
            prompt += "** NO COINGECKO DATA AVAILABLE. Cannot value this asset. Give conviction 0. **\n"

        if paprika:
            beta = paprika.get("beta_value", 0)
            if beta:
                prompt += f"\nBeta (vs market): {beta:.3f}"
                if abs(beta) > 1.5:
                    prompt += " — high volatility relative to market"
                prompt += "\n"

        prompt += "\nIs this asset undervalued or overvalued? Why? What's the risk to your thesis?"
        return prompt
