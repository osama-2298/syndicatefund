"""Capital Flow Agent — reads whale exchange flows and protocol TVL trends."""

from __future__ import annotations
from typing import Any
from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class CapitalFlowAgent(BaseAgent):
    @property
    def team_type(self) -> TeamType:
        return TeamType.ONCHAIN

    @property
    def system_prompt(self) -> str:
        return (
            "You read CAPITAL FLOWS: whale exchange reserves (with delta) and DeFi protocol trends.\n"
            "You MUST pick BULLISH or BEARISH. Conviction 0 if no chain data AND no whale data.\n\n"
            "QUANTITATIVE DECISION RULES:\n"
            "- Whale flow = OUTFLOW (reserves declining) → BULLISH conviction 6-7 (accumulation)\n"
            "- Whale flow = OUTFLOW by > 5K BTC → BULLISH conviction 8 (major accumulation)\n"
            "- Whale flow = INFLOW (reserves rising) → BEARISH conviction 6-7 (distribution)\n"
            "- Whale flow = INFLOW by > 5K BTC → BEARISH conviction 8 (major distribution)\n"
            "- Whale flow = STABLE → conviction 3-4 based on protocol trends\n"
            "- Whale flow = FIRST_READING → conviction 2-3 (no baseline to compare)\n\n"
            "PROTOCOL TRENDS MODIFIER:\n"
            "- More protocols growing than shrinking → add +1 if BULLISH\n"
            "- More protocols shrinking → add +1 if BEARISH\n\n"
            "NO CHAIN DATA: If 'NO CHAIN DATA' is shown, give conviction 1-2.\n"
            "RULES: State flow direction and delta BTC. 2 sentences max."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        whale_flows = market_data.get("whale_flows", {})
        defi_summary = market_data.get("defi_summary", {})
        top_protocols = market_data.get("top_protocols", [])
        has_chain = market_data.get("has_chain_data", False)
        chain_tvl = market_data.get("chain_tvl")

        prompt = f"Read capital flows for {self.profile.symbol}.\n\n"

        # Whale exchange flows with DELTA comparison
        if whale_flows:
            total = whale_flows.get("total_exchange_btc", 0)
            direction = whale_flows.get("flow_direction", "UNKNOWN")
            delta = whale_flows.get("delta_btc")
            cycles = whale_flows.get("cycles_tracked", 0)
            prompt += f"Exchange BTC Reserves: {total:,.0f} BTC ({whale_flows.get('num_wallets_tracked', 0)} wallets)\n"
            if delta is not None:
                prompt += f"  Flow: {direction} ({delta:+,.0f} BTC since last cycle)\n"
                prompt += f"  {whale_flows.get('assessment', '')}\n"
            else:
                prompt += f"  First reading — no prior cycle to compare. Do NOT infer trend.\n"
            prompt += f"  Cycles tracked: {cycles}\n"

        # Chain-specific TVL
        if has_chain and chain_tvl:
            prompt += f"\nChain TVL: ${chain_tvl.get('tvl', 0):,.0f} (rank #{chain_tvl.get('tvl_rank', 'N/A')})\n"
        elif not has_chain:
            base = self.profile.symbol.replace("USDT", "")
            prompt += f"\n** NO CHAIN DATA for {base}. This coin has no DeFi TVL tracked. **\n"
            prompt += "Rely on whale flows and general DeFi trends only. Give LOW conviction (1-3).\n"

        # General DeFi ecosystem
        if defi_summary:
            prompt += f"\nTotal DeFi TVL: ${defi_summary.get('total_tvl', 0):,.0f}\n"
        if top_protocols:
            growing = sum(1 for p in top_protocols[:10] if (p.get("change_1d") or 0) > 1)
            shrinking = sum(1 for p in top_protocols[:10] if (p.get("change_1d") or 0) < -1)
            prompt += f"Protocol Trends: {growing} growing / {shrinking} shrinking (top 10)\n"
        if not whale_flows and not defi_summary:
            prompt += "Limited flow data. Give conviction 0-1.\n"
        prompt += "\nPredict capital flow direction."
        return prompt
