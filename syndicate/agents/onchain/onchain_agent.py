"""
On-Chain Analysis Agent.

Analyzes blockchain-level data using DeFiLlama:
- Total Value Locked (TVL) per chain
- TVL dominance and ranking
- TVL trends (1d, 7d changes for top protocols)
- DeFi ecosystem health

For coins that ARE blockchains (ETH, SOL, AVAX, etc.), this agent provides
TVL-based fundamental analysis. For coins that aren't chains (DOGE, PEPE),
it provides market-wide DeFi context.

Data source: DeFiLlama API (free, no auth).
"""

from __future__ import annotations

from typing import Any

from syndicate.agents.base import BaseAgent
from syndicate.data.models import TeamType


def compute_onchain_scores(
    chain_tvl: dict | None,
    defi_summary: dict | None,
    top_protocols: list[dict] | None = None,
    btc_onchain: dict | None = None,
) -> dict[str, Any]:
    """
    Pre-compute on-chain scores from DeFiLlama data.
    All math happens here.
    """
    scores: dict[str, Any] = {}

    # ── 1. CHAIN TVL SCORE (-1 to +1) ──
    # Higher TVL = more capital locked = healthier ecosystem
    if chain_tvl:
        tvl = chain_tvl.get("tvl", 0)
        tvl_rank = chain_tvl.get("tvl_rank", 999)
        tvl_dom = chain_tvl.get("tvl_dominance_pct", 0)

        scores["chain_tvl"] = tvl
        scores["chain_tvl_rank"] = tvl_rank
        scores["chain_tvl_dominance"] = tvl_dom
        scores["has_chain_data"] = True

        # Rank-based score
        if tvl_rank <= 3:
            tvl_signal = 0.7
            scores["tvl_tier"] = "TOP_TIER — Dominant ecosystem"
        elif tvl_rank <= 10:
            tvl_signal = 0.4
            scores["tvl_tier"] = "MAJOR — Established ecosystem"
        elif tvl_rank <= 25:
            tvl_signal = 0.1
            scores["tvl_tier"] = "MID_TIER — Growing ecosystem"
        elif tvl_rank <= 50:
            tvl_signal = -0.1
            scores["tvl_tier"] = "SMALL — Early stage"
        else:
            tvl_signal = -0.3
            scores["tvl_tier"] = "MICRO — Minimal ecosystem"

        scores["tvl_signal"] = round(tvl_signal, 3)
    else:
        scores["has_chain_data"] = False
        scores["tvl_signal"] = 0.0
        scores["tvl_tier"] = "NO_CHAIN_DATA — Not a blockchain"

    # ── 2. DEFI ECOSYSTEM HEALTH (-1 to +1) ──
    if defi_summary:
        total_tvl = defi_summary.get("total_tvl", 0)
        num_chains = defi_summary.get("num_chains", 0)
        top_5_conc = defi_summary.get("top_5_concentration_pct", 0)

        scores["defi_total_tvl"] = total_tvl
        scores["defi_num_chains"] = num_chains
        scores["defi_top5_concentration"] = top_5_conc

        top_5 = defi_summary.get("top_5_chains", [])
        if top_5:
            scores["top_chains"] = [
                f"{c['name']} (${c['tvl']:,.0f}, {c['pct']}%)"
                for c in top_5
            ]

    # ── 3. PROTOCOL TRENDS (-1 to +1) ──
    if top_protocols:
        # Check if TVL is growing or shrinking across top protocols
        growing = 0
        shrinking = 0
        for p in top_protocols[:10]:
            change_1d = p.get("change_1d", 0) or 0
            if change_1d > 1:
                growing += 1
            elif change_1d < -1:
                shrinking += 1

        if growing > shrinking + 3:
            protocol_trend = 0.6
            scores["protocol_trend"] = "STRONG_INFLOW — Capital entering DeFi"
        elif growing > shrinking:
            protocol_trend = 0.3
            scores["protocol_trend"] = "INFLOW — More protocols growing than shrinking"
        elif shrinking > growing + 3:
            protocol_trend = -0.6
            scores["protocol_trend"] = "STRONG_OUTFLOW — Capital leaving DeFi"
        elif shrinking > growing:
            protocol_trend = -0.3
            scores["protocol_trend"] = "OUTFLOW — More protocols shrinking"
        else:
            protocol_trend = 0.0
            scores["protocol_trend"] = "BALANCED — Mixed protocol trends"

        scores["protocol_trend_signal"] = round(protocol_trend, 3)
        scores["protocols_growing"] = growing
        scores["protocols_shrinking"] = shrinking
    else:
        scores["protocol_trend_signal"] = 0.0

    # ── 4. BTC NETWORK HEALTH (real Blockchain.com data) ──
    if btc_onchain:
        scores["btc_network_power_eh"] = btc_onchain.get("network_power_eh", 0)
        scores["btc_network_health_status"] = btc_onchain.get("network_health_status", "UNKNOWN")
        scores["btc_tx_24h"] = btc_onchain.get("n_transactions_24h", 0)
        scores["btc_mempool"] = btc_onchain.get("mempool_count")
        scores["btc_mempool_read"] = btc_onchain.get("mempool_read", "UNKNOWN")
        scores["btc_block_time"] = btc_onchain.get("minutes_between_blocks", 0)
        scores["btc_block_time_read"] = btc_onchain.get("block_time_read", "UNKNOWN")
        scores["btc_est_tx_volume"] = btc_onchain.get("est_tx_volume_usd", 0)
        scores["btc_miners_revenue"] = btc_onchain.get("miners_revenue_usd", 0)
        scores["btc_fees_btc"] = btc_onchain.get("total_fees_btc", 0)

        # Network power signal: growing network power = miners confident = bullish
        hash_eh = btc_onchain.get("network_power_eh", 0)
        if hash_eh > 800:
            scores["network_health_signal"] = 0.5
        elif hash_eh > 500:
            scores["network_health_signal"] = 0.3
        elif hash_eh > 200:
            scores["network_health_signal"] = 0.1
        else:
            scores["network_health_signal"] = -0.3

        scores["has_btc_onchain"] = True
    else:
        scores["has_btc_onchain"] = False
        scores["network_health_signal"] = 0.0

    # ── 5. COMPOSITE ON-CHAIN SCORE ──
    signals = [scores.get("tvl_signal", 0)]
    if "protocol_trend_signal" in scores:
        signals.append(scores["protocol_trend_signal"])
    if scores.get("network_health_signal", 0) != 0:
        signals.append(scores["network_health_signal"])

    composite = sum(signals) / max(len(signals), 1)
    scores["composite_score"] = round(composite, 3)
    scores["composite_label"] = (
        "STRONG_BULLISH" if composite > 0.4 else
        "BULLISH" if composite > 0.15 else
        "NEUTRAL" if composite > -0.15 else
        "BEARISH" if composite > -0.4 else
        "STRONG_BEARISH"
    )

    return scores


class OnChainAgent(BaseAgent):
    """
    On-chain analyst — reads DeFiLlama TVL and protocol data.
    """

    @property
    def team_type(self) -> TeamType:
        return TeamType.ONCHAIN

    @property
    def system_prompt(self) -> str:
        return (
            "You are a senior on-chain analyst at a quantitative crypto hedge fund.\n\n"
            "You read CAPITAL FLOWS using real data: DeFiLlama TVL, Blockchain.com BTC network stats, "
            "whale exchange wallet balances, and protocol trends.\n\n"
            "YOUR TASK: Predict whether on-chain data favors HIGHER or LOWER prices for this asset.\n"
            "You MUST pick BULLISH or BEARISH. There is no neutral option.\n\n"
            "KEY ON-CHAIN CONCEPTS:\n"
            "- Rising TVL = capital entering ecosystem = bullish for chain token.\n"
            "- Falling TVL = capital flight = bearish.\n"
            "- BTC network power at highs = miners confident = network healthy = bullish.\n"
            "- High exchange reserves = selling pressure available. Declining reserves = accumulation.\n"
            "- Protocol trends: growing protocols = healthy ecosystem.\n\n"
            "DIRECTION RULES:\n"
            "- BULLISH if: TVL growing, network power strong, exchange reserves declining (accumulation), "
            "protocols trending positive.\n"
            "- BEARISH if: TVL declining, exchange reserves rising (distribution), "
            "protocols losing capital.\n"
            "- If no chain data (coin is not a blockchain): lean based on overall DeFi ecosystem "
            "health with low conviction.\n\n"
            "CONVICTION SCALE:\n"
            "- 9-10: Strong TVL rank + clear flows + BTC network health all aligned. Rare.\n"
            "- 7-8: Good TVL data with supporting flow signals.\n"
            "- 5-6: Moderate on-chain lean. Some data missing or mixed.\n"
            "- 3-4: Limited data but slight lean visible.\n"
            "- 1-2: Minimal on-chain data. Pick ecosystem direction.\n\n"
            "RULES:\n"
            "- Do NOT invent data. Reference provided scores.\n"
            "- Keep reasoning to 2-3 sentences.\n"
            "- If no chain data, give conviction 1-3."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        """Build prompt with pre-computed on-chain scores + real Blockchain.com data."""
        chain_tvl: dict | None = market_data.get("chain_tvl")
        defi_summary: dict | None = market_data.get("defi_summary")
        top_protocols: list[dict] | None = market_data.get("top_protocols")
        btc_onchain: dict | None = market_data.get("btc_onchain")

        scores = compute_onchain_scores(chain_tvl, defi_summary, top_protocols, btc_onchain)

        prompt = (
            f"Analyze on-chain data for {self.profile.symbol} and produce a trading signal.\n\n"
            f"=== PRE-COMPUTED ON-CHAIN SCORES (Real DeFiLlama Data) ===\n"
            f"COMPOSITE: {scores['composite_score']:+.3f} ({scores['composite_label']})\n\n"
        )

        if scores["has_chain_data"]:
            tvl = scores.get("chain_tvl", 0)
            prompt += (
                f"1. CHAIN TVL: {scores['tvl_signal']:+.3f}\n"
                f"   TVL: ${tvl:,.0f}\n"
                f"   Rank: #{scores.get('chain_tvl_rank', 'N/A')}\n"
                f"   Dominance: {scores.get('chain_tvl_dominance', 0):.1f}%\n"
                f"   Tier: {scores['tvl_tier']}\n\n"
            )
        else:
            prompt += (
                f"1. CHAIN TVL: N/A\n"
                f"   This coin is NOT a blockchain — no direct TVL data.\n"
                f"   Use broader DeFi ecosystem trends for context.\n\n"
            )

        if "defi_total_tvl" in scores:
            prompt += (
                f"2. DEFI ECOSYSTEM\n"
                f"   Total DeFi TVL: ${scores['defi_total_tvl']:,.0f}\n"
                f"   Active Chains: {scores.get('defi_num_chains', 0)}\n"
                f"   Top 5 Concentration: {scores.get('defi_top5_concentration', 0):.1f}%\n"
            )
            if "top_chains" in scores:
                for tc in scores["top_chains"][:5]:
                    prompt += f"     {tc}\n"
            prompt += "\n"

        if "protocol_trend" in scores:
            prompt += (
                f"3. PROTOCOL TRENDS: {scores['protocol_trend_signal']:+.3f}\n"
                f"   {scores['protocol_trend']}\n"
                f"   Growing: {scores.get('protocols_growing', 0)} | "
                f"Shrinking: {scores.get('protocols_shrinking', 0)} (of top 10)\n\n"
            )

        if scores.get("has_btc_onchain"):
            prompt += (
                f"4. BTC NETWORK (Real Blockchain.com Data):\n"
                f"   Network Power: {scores.get('btc_network_power_eh', 0)} EH/s — {scores.get('btc_network_health_status', 'N/A')}\n"
                f"   Transactions 24h: {scores.get('btc_tx_24h', 0):,}\n"
                f"   Block Time: {scores.get('btc_block_time', 0):.1f} min — {scores.get('btc_block_time_read', 'N/A')}\n"
            )
            mempool = scores.get("btc_mempool")
            if mempool is not None:
                prompt += f"   Mempool: {mempool:,} unconfirmed — {scores.get('btc_mempool_read', 'N/A')}\n"
            est_vol = scores.get("btc_est_tx_volume", 0)
            if est_vol:
                prompt += f"   Est. Tx Volume: ${est_vol:,.0f}\n"
            miners = scores.get("btc_miners_revenue", 0)
            if miners:
                prompt += f"   Miner Revenue: ${miners:,.0f}\n"
            prompt += f"   Network Health Signal: {scores.get('network_health_signal', 0):+.3f}\n\n"

        # Whale exchange flows
        whale_flows = market_data.get("whale_flows")
        if whale_flows:
            balances = whale_flows.get("exchange_balances", {})
            total = whale_flows.get("total_exchange_btc", 0)
            n_wallets = whale_flows.get("num_wallets_tracked", 0)
            if balances:
                prompt += (
                    f"5. WHALE EXCHANGE FLOWS ({n_wallets} wallets tracked):\n"
                    f"   Total Exchange BTC: {total:,.2f} BTC\n"
                )
                for name, bal in balances.items():
                    prompt += f"   {name}: {bal:,.2f} BTC\n"
                prompt += (
                    f"   Interpretation: High exchange reserves = selling pressure available. "
                    f"Declining reserves over time = accumulation.\n\n"
                )

        prompt += "Analyze the on-chain data and produce your signal."
        return prompt
