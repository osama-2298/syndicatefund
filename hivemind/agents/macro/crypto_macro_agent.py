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
            "You read CRYPTO-NATIVE macro conditions: total market cap trend, BTC dominance, "
            "ETH dominance, and overall market direction.\n\n"
            "Your job: is the crypto macro environment RISK-ON or RISK-OFF?\n"
            "You MUST pick BULLISH (risk-on) or BEARISH (risk-off).\n\n"
            "KEY SIGNALS:\n"
            "- Market cap growing → risk-on (bullish)\n"
            "- BTC dominance rising → flight to safety (bearish for alts)\n"
            "- BTC dominance falling → alt season forming (bullish for alts)\n"
            "- BTC leading + alts following = healthy bull\n\n"
            "CONVICTION: 9-10 extreme conditions. 5-6 moderate lean. 1-2 transitional.\n"
            "RULES: Reference BTC dominance and market cap direction. 2 sentences."
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
        prompt += "\nPredict crypto macro direction."
        return prompt
