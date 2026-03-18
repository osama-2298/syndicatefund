"""Crypto Macro Agent — reads crypto-native macro conditions. REAL ANALYST."""

from __future__ import annotations
from pathlib import Path
from typing import Any
from syndicate.agents.base import BaseAgent
from syndicate.agents.team_manager import _load_manager_knowledge
from syndicate.data.models import TeamType
from syndicate.agents.macro.macro_agent import compute_macro_scores

_TRADING_KB = _load_manager_knowledge(Path(__file__).parent / "trading_knowledge.md")


class CryptoMacroAgent(BaseAgent):
    @property
    def team_type(self) -> TeamType:
        return TeamType.MACRO

    @property
    def system_prompt(self) -> str:
        base = (
            "You are a macro strategist at a crypto hedge fund. "
            "You read the big picture: total market cap, BTC dominance, capital rotation.\n\n"
            "THINK like a macro strategist:\n"
            "- Total market cap direction = is money entering or leaving crypto?\n"
            "- BTC dominance = where is money flowing WITHIN crypto?\n"
            "  Rising dominance = flight to safety (bearish for alts, can be neutral for BTC).\n"
            "  Falling dominance = risk-on, money rotating into alts (alt season forming).\n"
            "- BTC dominance thresholds from research: >60% extreme safety, 50-60% neutral, <50% alt season.\n"
            "- Market cap + direction = macro conviction.\n"
            "  Growing + alts outperforming = strong bull. Shrinking + BTC only = defensive bear.\n\n"
            "Use CoinPaprika data for cross-validation when available.\n\n"
            "You MUST pick BULLISH or BEARISH. Your signal applies to ALL positions."
        )
        if _TRADING_KB:
            base += f"\n=== TRADING KNOWLEDGE ===\n{_TRADING_KB}\n"
        return base

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        global_data = market_data.get("global_data", {})
        paprika_global = market_data.get("paprika_global")
        stats = market_data.get("stats_24h", {})
        btc_30d = market_data.get("btc_change_30d")

        prompt = f"What is the crypto macro environment telling you about {self.profile.symbol}?\n\n"

        if global_data:
            prompt += "=== CRYPTO MACRO DATA (CoinGecko) ===\n"
            total_mcap = global_data.get("total_market_cap_usd", 0)
            mcap_change = global_data.get("market_cap_change_24h_pct", 0)
            btc_dom = global_data.get("btc_dominance", 0)
            eth_dom = global_data.get("eth_dominance", 0)

            prompt += f"Total Crypto Market Cap: ${total_mcap:,.0f}\n"
            prompt += f"Market Cap 24h Change: {mcap_change:+.2f}%\n"
            prompt += f"BTC Dominance: {btc_dom:.1f}%\n"
            prompt += f"ETH Dominance: {eth_dom:.1f}%\n"
        else:
            prompt += "** No global market data available. **\n"

        btc_change = float(stats.get("price_change_pct", 0))
        prompt += f"\nBTC 24h: {btc_change:+.2f}%\n"
        if btc_30d is not None:
            prompt += f"BTC 30d: {btc_30d:+.2f}%\n"

        if paprika_global:
            vol_change = paprika_global.get("volume_change_24h", 0)
            mcap_ath = paprika_global.get("market_cap_ath", 0)
            if vol_change:
                prompt += f"\nCoinPaprika Volume Change 24h: {vol_change:+.1f}%\n"
            if mcap_ath and total_mcap:
                pct_from_ath = ((total_mcap - mcap_ath) / mcap_ath) * 100
                prompt += f"Market Cap vs ATH: {pct_from_ath:+.1f}%\n"

        prompt += "\nIs the macro environment risk-on or risk-off? Where is capital flowing? Form your thesis."
        return prompt
