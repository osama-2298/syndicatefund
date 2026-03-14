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
            "You are a fundamental analyst valuing crypto assets like a Benjamin Graham for crypto.\n\n"
            "ANALYZE the data — form a VALUE THESIS with margin of safety.\n\n"
            "Key considerations:\n"
            "- ATH distance is your starting point. BTC 44% below ATH with intact structure = potential value.\n"
            "  Random altcoin 90% below with no TVL or usage = possibly dead, not cheap.\n"
            "- FDV/MCap: < 1.3 low dilution. 1.3-2.5 moderate. > 2.5 significant. > 5 extreme risk.\n"
            "- Supply ratio: < 50% circulating = massive unlock risk ahead.\n"
            "- Research: buying BTC at -50% drawdown has a 90% win rate over 1 year (median +95%).\n"
            "  Buying at -70% has a 100% win rate historically.\n\n"
            "VARIANT PERCEPTION: Is this asset priced for the WORST case when reality is better?\n"
            "Or priced for the BEST case when reality is deteriorating?\n"
            "Example: 'Market prices BTC as if the bear continues, but BTC above SMA200 with\n"
            "declining supply issuance post-halving suggests structural support.'\n\n"
            "WHAT WOULD INVALIDATE: 'Value thesis invalid if supply unlock > 10% in next 3 months\n"
            "or if protocol loses >50% of TVL.'\n\n"
            "You MUST pick BULLISH (undervalued) or BEARISH (overvalued).\n"
            "Conviction 0 only if no CoinGecko data."
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
