"""
CPO (Chief Performance Officer) — Agent performance monitoring.

The CPO:
- Reviews agent accuracy across cycles
- Flags underperformers for probation (< 30% accuracy over 20+ signals)
- Fires agents on probation that don't improve
- Recommends capacity reallocation

Founding agents are IMMUNE — CPO cannot fire or probate them.
"""

from __future__ import annotations

from typing import Any

import structlog

from syndicate.agents.base import BaseLLMCaller
from syndicate.config import LLMProvider

logger = structlog.get_logger()

PERFORMANCE_REVIEW_TOOL = {
    "name": "performance_review",
    "description": "Review agent performance and make probation/firing decisions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "probation_decisions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string"},
                        "action": {
                            "type": "string",
                            "enum": ["probation", "fire", "redeem"],
                            "description": (
                                "probation: Put on 10-cycle watch. "
                                "fire: Remove from active duty (was on probation, didn't improve). "
                                "redeem: Remove from probation (improved above 35%)."
                            ),
                        },
                        "reasoning": {"type": "string"},
                    },
                    "required": ["agent_id", "action", "reasoning"],
                },
            },
            "reallocation_suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string"},
                        "from_team": {"type": "string"},
                        "to_team": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["agent_id", "from_team", "to_team", "reason"],
                },
                "description": "Agents that might perform better in a different team.",
            },
            "overall_assessment": {
                "type": "string",
                "description": "2-3 sentences: overall talent quality and recommendations.",
            },
        },
        "required": ["probation_decisions", "reallocation_suggestions", "overall_assessment"],
    },
}

# Thresholds
PROBATION_ACCURACY_THRESHOLD = 0.30  # Below this → probation
PROBATION_MIN_SIGNALS = 20  # Need this many signals before judging
REDEMPTION_ACCURACY_THRESHOLD = 0.35  # Above this → redeemed from probation
FIRE_ACCURACY_THRESHOLD = 0.30  # Still below this after probation → fired
PROBATION_CYCLES = 10  # Number of cycles on probation before firing decision


class CPOAgent(BaseLLMCaller):
    """Chief Performance Officer — agent performance monitoring."""

    SYSTEM_PROMPT = (
        "You are the Chief Performance Officer (CPO) of a crypto hedge fund.\n\n"
        "Your job is to monitor agent performance and make probation/firing decisions. "
        "Think of it like a sports team manager reviewing player stats.\n\n"
        "RULES:\n"
        "1. FOUNDING agents (status='founding') are IMMUNE — you cannot fire or probate them.\n"
        "2. Need at least 20 evaluated signals before judging accuracy.\n"
        "3. Below 30% accuracy over 20+ signals → PROBATION.\n"
        "4. After 10 probation cycles, if still below 30% → FIRE.\n"
        "5. If probation agent improves above 35% → REDEEM.\n"
        "6. Consider the team context — a bad agent in a good team vs a good agent in a bad team.\n"
        "7. Don't fire too aggressively — losing agents reduces diversity.\n\n"
        "PERFORMANCE CONTEXT:\n"
        "- 50% accuracy is random (coin flip). Anything above is alpha.\n"
        "- 30-40% is concerning but may just be a bad market period.\n"
        "- Below 30% sustained over 20+ signals is genuinely destructive.\n"
        "- Consider cost — expensive models with bad accuracy are worse than cheap ones.\n"
    )

    def review_performance(
        self,
        agents: list[dict[str, Any]],
        team_performance: dict[str, dict],
    ) -> dict[str, Any]:
        """Review all agents and make probation/firing decisions."""
        prompt = self._build_prompt(agents, team_performance)

        try:
            return self._call_llm_with_tool(self.SYSTEM_PROMPT, prompt, PERFORMANCE_REVIEW_TOOL)
        except Exception as e:
            logger.error("cpo_review_failed", error=str(e))
            return {
                "probation_decisions": [],
                "reallocation_suggestions": [],
                "overall_assessment": f"CPO review failed: {str(e)[:80]}",
            }

    def _build_prompt(
        self,
        agents: list[dict],
        team_performance: dict,
    ) -> str:
        prompt = "Review agent performance and make decisions.\n\n"

        prompt += "=== AGENTS ===\n"
        for agent in agents:
            accuracy = (
                f"{agent['correct_signals'] / agent['total_signals']:.0%}"
                if agent['total_signals'] > 0
                else "N/A"
            )
            status_tag = f" [{agent['status'].upper()}]" if agent['status'] != 'active' else ""
            founding_tag = " [FOUNDING - IMMUNE]" if agent['status'] == 'founding' else ""
            prompt += (
                f"- {agent['id']}{status_tag}{founding_tag}\n"
                f"  Team: {agent.get('team_name', 'unassigned')} | "
                f"Model: {agent['model']} ({agent['provider']})\n"
                f"  Signals: {agent['total_signals']} | "
                f"Correct: {agent['correct_signals']} | "
                f"Accuracy: {accuracy}\n"
                f"  Cost: ${float(agent.get('total_cost_usd', 0)):.2f}\n\n"
            )

        if team_performance:
            prompt += "=== TEAM PERFORMANCE ===\n"
            for team, perf in team_performance.items():
                prompt += (
                    f"- {team}: {perf.get('accuracy', 0):.0%} accuracy "
                    f"({perf.get('total', 0)} signals)\n"
                )

        prompt += (
            "\nReview each non-founding agent with 20+ signals. "
            "Flag underperformers for probation. Fire probation agents that haven't improved. "
            "Suggest team reallocations if an agent's skills don't match their team."
        )
        return prompt
