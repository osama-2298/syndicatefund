"""Network Health Agent — reads BTC network stats and chain TVL."""

from __future__ import annotations
from typing import Any
from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class NetworkHealthAgent(BaseAgent):
    @property
    def team_type(self) -> TeamType:
        return TeamType.ONCHAIN

    @property
    def system_prompt(self) -> str:
        return (
            "You read BLOCKCHAIN NETWORK HEALTH: hash rate, transactions, mempool, TVL rank.\n"
            "You MUST pick BULLISH or BEARISH. Conviction 0 if NO chain data AND NO BTC data.\n\n"
            "QUANTITATIVE DECISION RULES:\n"
            "- Hash rate > 700 EH/s (ATH zone) → BULLISH conviction 6-7\n"
            "- Hash rate 400-700 EH/s → BULLISH conviction 4-5 (healthy)\n"
            "- Hash rate < 400 EH/s → BEARISH conviction 5-6 (miners leaving)\n"
            "- Chain TVL rank #1-3 → add +2 conviction BULLISH\n"
            "- Chain TVL rank #4-10 → add +1 conviction BULLISH\n"
            "- Chain TVL rank > 25 → no modifier (small ecosystem)\n"
            "- NO CHAIN DATA → conviction 1-2 max (only use general BTC health)\n\n"
            "MEMPOOL MODIFIER:\n"
            "- Mempool > 50K (congested) → network busy, add +1 conviction in current direction\n"
            "- Mempool < 2K (quiet) → low activity, reduce conviction by 1\n\n"
            "NOTE: Network health is a SLOW indicator. Don't overweight it for short-term trades.\n"
            "RULES: State hash rate EH/s and TVL rank. 2 sentences max."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        btc_onchain = market_data.get("btc_onchain", {})
        chain_tvl = market_data.get("chain_tvl")
        has_chain = market_data.get("has_chain_data", False)
        base = self.profile.symbol.replace("USDT", "")

        prompt = f"Assess network health for {self.profile.symbol}.\n\n"

        if btc_onchain:
            if base == "BTC":
                prompt += "=== BTC NETWORK (direct on-chain data) ===\n"
            else:
                prompt += "=== BTC NETWORK (market proxy, not specific to this coin) ===\n"
            prompt += f"Hash Rate: {btc_onchain.get('hash_rate_eh', 0)} EH/s — {btc_onchain.get('hash_health', 'N/A')}\n"
            prompt += f"Transactions 24h: {btc_onchain.get('n_transactions_24h', 0):,}\n"
            prompt += f"Block Time: {btc_onchain.get('minutes_between_blocks', 0):.1f}m — {btc_onchain.get('block_time_read', '')}\n"
            mempool = btc_onchain.get('mempool_count')
            if mempool is not None:
                prompt += f"Mempool: {mempool:,} — {btc_onchain.get('mempool_read', '')}\n"

        if has_chain and chain_tvl:
            prompt += f"\n=== {base} CHAIN TVL ===\n"
            prompt += f"TVL: ${chain_tvl.get('tvl', 0):,.0f}\n"
            prompt += f"Rank: #{chain_tvl.get('tvl_rank', 'N/A')}\n"
        elif not has_chain:
            prompt += f"\n** NO CHAIN TVL DATA for {base}. **\n"
            prompt += "This coin does not have a DeFi chain tracked by DeFiLlama.\n"
            prompt += "Give LOW conviction (1-2). Do not invent chain metrics.\n"

        if not btc_onchain and not has_chain:
            prompt += "No on-chain data available. Give conviction 0 (genuinely no edge).\n"

        prompt += "\nPredict network health direction."
        return prompt
