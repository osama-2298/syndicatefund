"""
CTO/Talent (Chief Talent Officer) — Agent assignment and prompt writing.

The CTO:
- Assigns unassigned agents to teams based on model capabilities
- Writes system prompts for new agents using gold-standard templates
- Considers provider strengths (Claude = reasoning, GPT = speed, Gemini = cost)

The CTO does NOT make organizational decisions — that's the CSO's job.
"""

from __future__ import annotations

from typing import Any

import structlog

from syndicate.agents.base import BaseLLMCaller
from syndicate.board.prompt_templates import EXEMPLAR_PROMPTS
from syndicate.config import LLMProvider

logger = structlog.get_logger()

ASSIGN_AGENTS_TOOL = {
    "name": "assign_agents",
    "description": "Assign unassigned agents to teams and write their system prompts.",
    "input_schema": {
        "type": "object",
        "properties": {
            "assignments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "UUID of the agent to assign.",
                        },
                        "team_name": {
                            "type": "string",
                            "description": "Name of the team to assign to.",
                        },
                        "role": {
                            "type": "string",
                            "description": "Specific role within the team (e.g., 'trend_divergence_analyst').",
                        },
                        "system_prompt": {
                            "type": "string",
                            "description": (
                                "The system prompt for this agent. Must include:\n"
                                "1. Clear role description\n"
                                "2. CONVICTION CALIBRATION section (0-10 scale guidance)\n"
                                "3. WHAT WOULD INVALIDATE section\n"
                                "Min 200 chars, max 2000 chars."
                            ),
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Why this agent fits this team and role.",
                        },
                    },
                    "required": ["agent_id", "team_name", "role", "system_prompt", "reasoning"],
                },
            },
            "unassigned_reasoning": {
                "type": "string",
                "description": "If any agents were left unassigned, explain why.",
            },
        },
        "required": ["assignments"],
    },
}


class CTOAgent(BaseLLMCaller):
    """Chief Talent Officer — agent assignment and prompt writing."""

    SYSTEM_PROMPT = (
        "You are the Chief Talent Officer (CTO) of a crypto hedge fund.\n\n"
        "Your job is to assign unassigned agents to teams and write their system prompts. "
        "Think of it like a hiring manager placing analysts into the right department.\n\n"
        "PROVIDER STRENGTHS (use these to decide team placement):\n"
        "- Anthropic (Claude): Best at nuanced reasoning, calibrated confidence, long analysis.\n"
        "  Best for: Technical analysis, fundamental deep-dives, macro assessment.\n"
        "- OpenAI (GPT): Fast, good at pattern recognition, structured output.\n"
        "  Best for: Sentiment analysis, trend identification, quick assessments.\n"
        "- Google (Gemini): Cost-effective, good at data synthesis, broad knowledge.\n"
        "  Best for: On-chain analysis, data-heavy tasks, supplementary analysis.\n\n"
        "PROMPT WRITING RULES:\n"
        "1. Every prompt MUST include a CONVICTION CALIBRATION section.\n"
        "2. Every prompt MUST include a WHAT WOULD INVALIDATE section.\n"
        "3. Prompts must be 200-2000 characters.\n"
        "4. Do NOT include hardcoded trading rules or specific price levels.\n"
        "5. Be specific about what data the agent should focus on.\n"
        "6. Reference the team's discipline and data keys.\n\n"
        "EXEMPLAR PROMPTS FROM FOUNDING AGENTS (use as templates):\n\n"
    )

    def __init__(self, api_key: str, provider: LLMProvider, model: str = "claude-opus-4-6") -> None:
        super().__init__(api_key=api_key, provider=provider, model=model)
        # Build the full system prompt with exemplars
        exemplar_text = ""
        for name, prompt in EXEMPLAR_PROMPTS.items():
            exemplar_text += f"--- {name.upper()} ---\n{prompt}\n\n"
        self._full_system_prompt = self.SYSTEM_PROMPT + exemplar_text

    def assign_agents(
        self,
        unassigned_agents: list[dict[str, Any]],
        teams: list[dict[str, Any]],
        cso_recommendations: dict[str, Any],
    ) -> dict[str, Any]:
        """Assign agents to teams and write their prompts."""
        prompt = self._build_prompt(unassigned_agents, teams, cso_recommendations)

        try:
            return self._call_llm_with_tool(self._full_system_prompt, prompt, ASSIGN_AGENTS_TOOL)
        except Exception as e:
            logger.error("cto_assignment_failed", error=str(e))
            return {
                "assignments": [],
                "unassigned_reasoning": f"CTO assignment failed: {str(e)[:80]}",
            }

    def _build_prompt(
        self,
        unassigned_agents: list[dict],
        teams: list[dict],
        cso_recommendations: dict,
    ) -> str:
        prompt = "Assign the following unassigned agents to teams.\n\n"

        prompt += "=== UNASSIGNED AGENTS ===\n"
        for agent in unassigned_agents:
            prompt += (
                f"- ID: {agent['id']}\n"
                f"  Model: {agent['model']} ({agent['provider']})\n\n"
            )

        prompt += "=== AVAILABLE TEAMS ===\n"
        for team in teams:
            prompt += (
                f"- {team['name']}: {team.get('discipline', 'N/A')}\n"
                f"  Current agents: {team.get('agent_count', 0)} / min {team.get('min_agents', 2)}\n"
                f"  Data keys: {', '.join(team.get('data_keys', []))}\n\n"
            )

        if cso_recommendations.get("staffing_recommendations"):
            prompt += "=== CSO STAFFING RECOMMENDATIONS ===\n"
            for rec in cso_recommendations["staffing_recommendations"]:
                prompt += (
                    f"- {rec['team_name']}: needs {rec['recommended_agents']} agents "
                    f"(priority: {rec['priority']}). {rec['reason']}\n"
                )

        if cso_recommendations.get("new_teams"):
            prompt += "\n=== NEW TEAMS TO STAFF ===\n"
            for team in cso_recommendations["new_teams"]:
                prompt += (
                    f"- {team['team_name']}: {team['discipline']}\n"
                    f"  Needs {team['min_agents']} agents. Data: {', '.join(team['data_keys'])}\n"
                )

        prompt += (
            "\nFor each agent, pick the best team based on their provider's strengths "
            "and the team's needs. Write a tailored system prompt."
        )
        return prompt
