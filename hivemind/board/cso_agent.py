"""
CSO (Chief Strategy Officer) — Organizational structure and team management.

The CSO decides:
- Whether new teams should be created
- Whether existing teams should be dissolved
- Coverage gaps in the analysis pipeline
- Staffing recommendations for teams

The CSO does NOT assign individual agents or write prompts — that's the CTO's job.
"""

from __future__ import annotations

from typing import Any

import structlog

from hivemind.agents.base import BaseLLMCaller
from hivemind.config import LLMProvider

logger = structlog.get_logger()

PROPOSE_TEAM_TOOL = {
    "name": "organizational_decisions",
    "description": "Propose organizational changes: new teams, team dissolution, staffing recommendations.",
    "input_schema": {
        "type": "object",
        "properties": {
            "new_teams": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "team_name": {
                            "type": "string",
                            "description": "Short, descriptive name (e.g., 'regulatory_risk', 'defi_yield').",
                        },
                        "discipline": {
                            "type": "string",
                            "description": "What this team analyzes. 2-3 sentences.",
                        },
                        "data_keys": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of data slice keys from the data registry.",
                        },
                        "min_agents": {
                            "type": "integer",
                            "minimum": 2,
                            "maximum": 7,
                        },
                        "activation_mode": {
                            "type": "string",
                            "enum": ["always", "conditional"],
                        },
                        "activation_condition": {
                            "type": "string",
                            "description": "For conditional teams: when should this team activate?",
                        },
                        "justification": {
                            "type": "string",
                            "description": "Why this team is needed. Reference coverage gaps.",
                        },
                    },
                    "required": ["team_name", "discipline", "data_keys", "min_agents",
                                 "activation_mode", "justification"],
                },
                "description": "New teams to create. Empty list if no new teams needed.",
            },
            "dissolve_teams": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "team_name": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["team_name", "reason"],
                },
                "description": "Teams to dissolve. Cannot dissolve system teams.",
            },
            "staffing_recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "team_name": {"type": "string"},
                        "current_agents": {"type": "integer"},
                        "recommended_agents": {"type": "integer"},
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                        },
                        "reason": {"type": "string"},
                    },
                    "required": ["team_name", "recommended_agents", "priority", "reason"],
                },
                "description": "Staffing level recommendations for existing teams.",
            },
            "overall_assessment": {
                "type": "string",
                "description": "2-3 sentences: organizational health and strategic gaps.",
            },
        },
        "required": ["new_teams", "dissolve_teams", "staffing_recommendations",
                     "overall_assessment"],
    },
}


class CSOAgent(BaseLLMCaller):
    """Chief Strategy Officer — organizational structure decisions."""

    SYSTEM_PROMPT = (
        "You are the Chief Strategy Officer (CSO) of a crypto hedge fund.\n\n"
        "Your role is to design the organizational structure — which analysis teams exist, "
        "what they cover, and how they're staffed. You think in terms of COVERAGE GAPS and "
        "ANALYTICAL DIVERSITY.\n\n"
        "SYSTEM TEAMS (CANNOT be dissolved or modified):\n"
        "- technical: Chart patterns, indicators, multi-timeframe analysis\n"
        "- sentiment: Social media, Fear & Greed, crowd psychology\n"
        "- fundamental: Valuation, tokenomics, competitive analysis\n"
        "- macro: Global crypto markets, BTC dominance, Fed policy\n"
        "- onchain: Network health, whale flows, DeFi TVL\n\n"
        "AVAILABLE DATA KEYS for new teams:\n"
        "indicators_4h, indicators_1h, indicators_1d, indicators_1w, "
        "price_history_4h, price_history_1d, stats_24h, order_book, derivatives, "
        "fear_greed, reddit_sentiment, reddit_coin_sentiment, trending, "
        "coingecko_coin, smart_money, global_data, btc_onchain, defi_summary, "
        "top_protocols, whale_flows, prediction_markets, paprika_global, "
        "paprika_coin, chain_tvl, indicators\n\n"
        "CONSTRAINTS:\n"
        "- New teams must have at least min_agents unassigned agents available\n"
        "- New teams start as 'provisional' — evaluated after 10 cycles\n"
        "- Only propose teams that would genuinely improve signal quality\n"
        "- Don't propose teams that duplicate existing coverage\n"
        "- Consider the current market regime when proposing conditional teams\n"
    )

    def review_organization(
        self,
        teams: list[dict[str, Any]],
        unassigned_agent_count: int,
        regime: str,
        team_performance: dict[str, dict],
    ) -> dict[str, Any]:
        """Review organizational structure and propose changes."""
        prompt = self._build_prompt(teams, unassigned_agent_count, regime, team_performance)

        try:
            return self._call_llm_with_tool(self.SYSTEM_PROMPT, prompt, PROPOSE_TEAM_TOOL)
        except Exception as e:
            logger.error("cso_review_failed", error=str(e))
            return {
                "new_teams": [],
                "dissolve_teams": [],
                "staffing_recommendations": [],
                "overall_assessment": f"CSO review failed: {str(e)[:80]}",
            }

    def _build_prompt(
        self,
        teams: list[dict],
        unassigned_agents: int,
        regime: str,
        team_performance: dict,
    ) -> str:
        prompt = "Review the organizational structure and make recommendations.\n\n"

        prompt += f"=== CURRENT REGIME ===\n{regime.upper()}\n\n"
        prompt += f"=== UNASSIGNED AGENTS AVAILABLE ===\n{unassigned_agents}\n\n"

        prompt += "=== CURRENT TEAMS ===\n"
        for team in teams:
            system_tag = " [SYSTEM]" if team.get("is_system") else " [PROVISIONAL]"
            prompt += (
                f"- {team['name']}{system_tag}: {team.get('agent_count', 0)} agents, "
                f"weight {team.get('weight', 1.0):.1f}\n"
                f"  Discipline: {team.get('discipline', 'N/A')}\n"
            )

        if team_performance:
            prompt += "\n=== TEAM PERFORMANCE ===\n"
            for team_name, perf in team_performance.items():
                prompt += (
                    f"- {team_name}: {perf.get('accuracy', 0):.0%} accuracy "
                    f"({perf.get('total', 0)} signals)\n"
                )

        prompt += (
            "\nAssess the organization. Propose new teams ONLY if there are clear "
            "coverage gaps AND unassigned agents to staff them."
        )
        return prompt
