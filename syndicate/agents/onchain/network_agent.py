"""Network Health Agent — blockchain fundamentals. REAL ANALYST."""

from __future__ import annotations
from typing import Any
from syndicate.agents.base import BaseAgent
from syndicate.data.models import TeamType


class NetworkHealthAgent(BaseAgent):
    @property
    def team_type(self) -> TeamType:
        return TeamType.ONCHAIN

    @property
    def system_prompt(self) -> str:
        return (
            "You are a blockchain network analyst at a crypto hedge fund. "
            "You read on-chain fundamentals: network power, transaction volume, mempool, block times, TVL.\n\n"
            "ANALYZE the data — think about what it MEANS, not just what the numbers are.\n\n"
            "What a great on-chain analyst considers:\n"
            "- Network power is a LONG-TERM confidence indicator. Miners invest millions in hardware.\n"
            "  Rising network power = miners believe in the asset's future. This is the strongest on-chain signal.\n"
            "  Current BTC network power > 700 EH/s is at or near all-time highs.\n"
            "- Transaction count = network usage. More transactions = more demand.\n"
            "- Mempool = immediate demand pressure. Congested = high demand. Empty = quiet.\n"
            "- Block time = network health. ~10 min for BTC is normal.\n"
            "- Chain TVL (if available) = how much capital is deployed in this chain's DeFi ecosystem.\n"
            "  Top 5 TVL chains are the dominant ecosystems. Below rank 25 = minor.\n\n"
            "IMPORTANT: Network health is a SLOW signal. It changes over weeks, not hours.\n"
            "High conviction (7+) requires STRONG on-chain data. Low conviction is normal.\n"
            "NO CHAIN DATA: If this coin has no on-chain metrics, give conviction 1-2 at most.\n\n"
            "You MUST pick BULLISH or BEARISH."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        btc_onchain = market_data.get("btc_onchain", {})
        chain_tvl = market_data.get("chain_tvl")
        has_chain = market_data.get("has_chain_data", False)
        base = self.profile.symbol.replace("USDT", "")

        prompt = f"Assess the network health behind {self.profile.symbol}.\n\n"

        if btc_onchain:
            if base == "BTC":
                prompt += "=== BTC NETWORK DATA (direct on-chain) ===\n"
            else:
                prompt += "=== BTC NETWORK (market proxy — not specific to this coin) ===\n"
            prompt += f"Network Power: {btc_onchain.get('network_power_eh', 0)} EH/s — {btc_onchain.get('network_health_status', 'N/A')}\n"
            prompt += f"Transactions 24h: {btc_onchain.get('n_transactions_24h', 0):,}\n"
            prompt += f"Block Time: {btc_onchain.get('minutes_between_blocks', 0):.1f} min — {btc_onchain.get('block_time_read', '')}\n"
            mempool = btc_onchain.get('mempool_count')
            if mempool is not None:
                prompt += f"Mempool: {mempool:,} unconfirmed txs — {btc_onchain.get('mempool_read', '')}\n"
            est_vol = btc_onchain.get("est_tx_volume_usd", 0)
            if est_vol:
                prompt += f"Est. Tx Volume: ${est_vol:,.0f}\n"
            miners = btc_onchain.get("miners_revenue_usd", 0)
            if miners:
                prompt += f"Miner Revenue: ${miners:,.0f}\n"

        if has_chain and chain_tvl:
            prompt += f"\n=== {base} CHAIN TVL ===\n"
            prompt += f"TVL: ${chain_tvl.get('tvl', 0):,.0f}\n"
            prompt += f"Rank: #{chain_tvl.get('tvl_rank', 'N/A')}\n"
            dom = chain_tvl.get('tvl_dominance_pct', 0)
            if dom:
                prompt += f"Dominance: {dom:.1f}% of total DeFi TVL\n"
        elif not has_chain:
            prompt += f"\n** NO CHAIN DATA for {base}. This coin does not have DeFi TVL tracked. **\n"
            prompt += "Give LOW conviction (1-2). Do not invent chain metrics.\n"

        if not btc_onchain and not has_chain:
            prompt += "No on-chain data available at all. Give conviction 0.\n"

        prompt += "\nWhat does the network health tell you? Is this a healthy, growing ecosystem? Form your thesis."
        return prompt
