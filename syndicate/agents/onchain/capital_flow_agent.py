"""Capital Flow Agent — whale flows + DeFi protocol trends. REAL ANALYST."""

from __future__ import annotations
from typing import Any
from syndicate.agents.base import BaseAgent
from syndicate.data.models import TeamType


class CapitalFlowAgent(BaseAgent):
    @property
    def team_type(self) -> TeamType:
        return TeamType.ONCHAIN

    @property
    def system_prompt(self) -> str:
        return (
            "You are a capital flow analyst at a crypto hedge fund. "
            "You track where money is moving: exchange reserves, DeFi protocols, whale wallets.\n\n"
            "ANALYZE the flows — think about what they MEAN for price direction.\n\n"
            "What a great flow analyst considers:\n"
            "- Exchange reserves DIRECTION matters, not absolute level.\n"
            "  OUTFLOW (reserves declining) = accumulation. Whales are pulling BTC off exchanges to hold.\n"
            "  INFLOW (reserves rising) = distribution. Whales are depositing to sell.\n"
            "  STABLE = no signal. Don't invent a trend from a flat number.\n"
            "  FIRST_READING = no prior data. You literally cannot know the direction. Low conviction.\n"
            "- DeFi protocol trends: are protocols GROWING or SHRINKING?\n"
            "  More protocols growing than shrinking = healthy ecosystem = capital entering.\n"
            "- Chain TVL: if this coin IS a blockchain, its TVL tells you ecosystem health.\n\n"
            "NO CHAIN DATA: If this coin has no on-chain footprint, give conviction 1-2.\n"
            "FIRST READING: If whale data has no prior cycle to compare, give conviction 2-3.\n\n"
            "You MUST pick BULLISH or BEARISH."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        whale_flows = market_data.get("whale_flows", {})
        defi_summary = market_data.get("defi_summary", {})
        top_protocols = market_data.get("top_protocols", [])
        has_chain = market_data.get("has_chain_data", False)
        chain_tvl = market_data.get("chain_tvl")
        base = self.profile.symbol.replace("USDT", "")

        prompt = f"Where is capital flowing for {self.profile.symbol}?\n\n"

        # Whale exchange flows
        if whale_flows:
            total = whale_flows.get("total_exchange_btc", 0)
            direction = whale_flows.get("flow_direction", "UNKNOWN")
            delta = whale_flows.get("delta_btc")
            cycles = whale_flows.get("cycles_tracked", 0)

            prompt += "=== WHALE EXCHANGE FLOWS ===\n"
            prompt += f"Exchange BTC Reserves: {total:,.0f} BTC ({whale_flows.get('num_wallets_tracked', 0)} wallets)\n"

            if delta is not None:
                prompt += f"Flow Direction: {direction} ({delta:+,.0f} BTC since last cycle)\n"
                prompt += f"{whale_flows.get('assessment', '')}\n"
            else:
                prompt += f"FIRST READING — no prior cycle to compare. Do NOT infer a trend.\n"

            prompt += f"Cycles tracked: {cycles}\n"

        # Chain TVL
        if has_chain and chain_tvl:
            prompt += f"\n=== {base} CHAIN TVL ===\n"
            prompt += f"TVL: ${chain_tvl.get('tvl', 0):,.0f} (rank #{chain_tvl.get('tvl_rank', 'N/A')})\n"
        elif not has_chain:
            prompt += f"\n** NO CHAIN DATA for {base}. No DeFi TVL tracked. **\n"
            prompt += "Rely on whale flows and general DeFi trends. Low conviction (1-3).\n"

        # DeFi ecosystem
        if defi_summary:
            prompt += f"\n=== DEFI ECOSYSTEM ===\n"
            prompt += f"Total DeFi TVL: ${defi_summary.get('total_tvl', 0):,.0f}\n"
        if top_protocols:
            growing = sum(1 for p in top_protocols[:10] if (p.get("change_1d") or 0) > 1)
            shrinking = sum(1 for p in top_protocols[:10] if (p.get("change_1d") or 0) < -1)
            prompt += f"Protocol Trends: {growing} growing / {shrinking} shrinking (top 10)\n"

        if not whale_flows and not defi_summary and not has_chain:
            prompt += "Limited flow data available. Give conviction 0-1.\n"

        prompt += "\nIs capital flowing in or out? What does the flow pattern tell you? Form your thesis."
        return prompt
