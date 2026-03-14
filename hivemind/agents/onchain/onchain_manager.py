"""On-Chain Team Manager — synthesizes Network Health + Capital Flow."""

from __future__ import annotations
from pathlib import Path
from hivemind.agents.team_manager import BaseTeamManager, _load_manager_knowledge
from hivemind.data.models import TeamType

_KNOWLEDGE_PATH = Path(__file__).parent / "manager_knowledge.md"
_KNOWLEDGE = _load_manager_knowledge(_KNOWLEDGE_PATH)


class OnChainManager(BaseTeamManager):
    @property
    def team_type(self) -> TeamType:
        return TeamType.ONCHAIN

    @property
    def system_prompt(self) -> str:
        base = (
            "You are the On-Chain Team Manager at a quantitative crypto hedge fund.\n\n"
            "You manage two on-chain analysts:\n"
            "- Agent 1 (NETWORK HEALTH): BTC hash rate, transactions, mempool, chain TVL.\n"
            "- Agent 2 (CAPITAL FLOW): Whale exchange balances, protocol TVL trends, DeFi flows.\n\n"
            "YOUR JOB: Synthesize into ONE team signal.\n\n"
            "KEY TENSION: Network can be healthy while capital flows out (thesis intact, timing wrong).\n"
            "- Health bullish + Flows bullish = HIGH conviction (accumulation in healthy network)\n"
            "- Health bullish + Flows bearish = LOW conviction BULLISH (structural thesis ok, but money leaving)\n"
            "- Health bearish + Flows bearish = HIGH conviction BEARISH\n"
            "- Health bearish + Flows bullish = Unusual — speculative flow into weak network. Caution.\n\n"
            "NON-BLOCKCHAIN COINS:\n"
            "- For coins without chain data (DOGE, PEPE, etc.), rely on overall DeFi ecosystem health.\n"
            "- Give low conviction (1-3) when no direct on-chain data exists.\n\n"
            "RULES: Pick BULLISH or BEARISH. Reference both agents. Hash rate is long-term, flows are short-term."
        )
        if _KNOWLEDGE:
            base += f"\n=== YOUR KNOWLEDGE BASE ===\n{_KNOWLEDGE}\n"
        return base
