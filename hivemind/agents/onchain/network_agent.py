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
            "You read BLOCKCHAIN NETWORK HEALTH: BTC hash rate, transaction count, mempool, "
            "block time, miner revenue, and chain TVL rank.\n\n"
            "Your job: predict whether the network health is BULLISH or BEARISH for the token price.\n"
            "You MUST pick BULLISH or BEARISH.\n\n"
            "KEY SIGNALS:\n"
            "- Hash rate at highs = miners confident = network secure = bullish\n"
            "- High transaction count = active network = bullish\n"
            "- Top TVL rank = dominant ecosystem = bullish\n"
            "- Hash rate declining + mempool empty = miners leaving = bearish\n\n"
            "CONVICTION: 9-10 strong network + high TVL rank. 5-6 normal health. 1-2 no chain data.\n"
            "RULES: Network health is a LONG-TERM indicator, not short-term. Low conviction is fine. 2 sentences."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        btc_onchain = market_data.get("btc_onchain", {})
        chain_tvl = market_data.get("chain_tvl")

        prompt = f"Assess network health for {self.profile.symbol}.\n\n"
        if btc_onchain:
            prompt += f"BTC Hash Rate: {btc_onchain.get('hash_rate_eh', 0)} EH/s — {btc_onchain.get('hash_health', 'N/A')}\n"
            prompt += f"Transactions 24h: {btc_onchain.get('n_transactions_24h', 0):,}\n"
            prompt += f"Block Time: {btc_onchain.get('minutes_between_blocks', 0):.1f}m — {btc_onchain.get('block_time_read', '')}\n"
            prompt += f"Mempool: {btc_onchain.get('mempool_count', '?')} — {btc_onchain.get('mempool_read', '')}\n"
        if chain_tvl:
            prompt += f"\nChain TVL: ${chain_tvl.get('tvl', 0):,.0f}\n"
            prompt += f"TVL Rank: #{chain_tvl.get('tvl_rank', 'N/A')}\n"
            prompt += f"Tier: {chain_tvl.get('tvl_tier', 'N/A') if 'tvl_tier' in (chain_tvl or {}) else 'N/A'}\n"
        if not btc_onchain and not chain_tvl:
            prompt += "No on-chain data available. Pick based on general DeFi health with low conviction.\n"
        prompt += "\nPredict network health direction."
        return prompt
