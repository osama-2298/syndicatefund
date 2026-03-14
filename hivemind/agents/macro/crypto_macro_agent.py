"""Crypto Macro Agent — reads crypto-native macro conditions."""

from __future__ import annotations
from typing import Any
from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType
from hivemind.agents.macro.macro_agent import compute_macro_scores


class CryptoMacroAgent(BaseAgent):
    @property
    def team_type(self) -> TeamType:
        return TeamType.MACRO

    @property
    def system_prompt(self) -> str:
        return (
            "You read CRYPTO-NATIVE macro: market cap trend, BTC dominance, market direction.\n"
            "You MUST pick BULLISH or BEARISH. Conviction 0 if no global data.\n\n"
            "QUANTITATIVE DECISION RULES:\n"
            "- Market cap 24h > +2% AND BTC dominance stable/falling → BULLISH conviction 7-8\n"
            "- Market cap 24h > 0% AND BTC dom < 55% → BULLISH conviction 5-6 (alt-friendly)\n"
            "- Market cap 24h -1% to +1% → conviction 3-4 in BTC 24h direction\n"
            "- Market cap 24h < -2% AND BTC dominance rising → BEARISH conviction 7-8\n"
            "- Market cap 24h < -5% → BEARISH conviction 8-9\n\n"
            "BTC DOMINANCE RULES:\n"
            "- BTC dom > 60% → BEARISH for alts, add +1 if BEARISH\n"
            "- BTC dom 50-60% → neutral macro\n"
            "- BTC dom < 50% → alt season, add +1 if BULLISH\n"
            "- BTC dom < 40% → extreme alt season, but late cycle risk\n\n"
            "RULES: State market cap % change and BTC dominance. 2 sentences max."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        global_data = market_data.get("global_data", {})
        stats = market_data.get("stats_24h", {})
        btc_30d = market_data.get("btc_change_30d")

        scores = compute_macro_scores(global_data, stats, btc_30d)

        prompt = f"Read crypto macro conditions for {self.profile.symbol}.\n\n"
        prompt += f"COMPOSITE: {scores['composite_score']:+.3f} ({scores['composite_label']})\n"
        prompt += f"Market Cap 24h: {scores['mcap_change_24h']:+.2f}% — {scores['mcap_trend']}\n"
        prompt += f"BTC Dominance: {scores['btc_dominance']:.1f}% — {scores['btc_dom_read']}\n"
        prompt += f"Market Direction: {scores['market_direction']}\n"
        if "macro_30d_read" in scores:
            prompt += f"30d Macro: {scores['macro_30d_read']}\n"

        # CoinPaprika cross-validation
        paprika_global = market_data.get("paprika_global")
        if paprika_global:
            vol_change = paprika_global.get("volume_change_24h", 0)
            mcap_ath = paprika_global.get("market_cap_ath", 0)
            if vol_change:
                prompt += f"\nVolume Change 24h (CoinPaprika): {vol_change:+.1f}%\n"
            if mcap_ath:
                current_mcap = scores.get("total_market_cap_usd", 0)
                if current_mcap and mcap_ath:
                    pct_from_ath = ((current_mcap - mcap_ath) / mcap_ath) * 100
                    prompt += f"Market Cap vs ATH: {pct_from_ath:+.1f}%\n"

        prompt += "\nPredict crypto macro direction."
        return prompt
