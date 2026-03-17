"""
Head of Research — Dr. Elara Voss

Orchestrates the research division. Produces weekly digests that synthesize
findings from the Quantitative Researcher and Strategy Researcher into
actionable recommendations for the Board and CEO.

Former MIT PhD in computational finance. Thinks in statistical significance,
not opinions. Skeptical by default — if a signal looks too good, she suspects overfitting.
"""

from __future__ import annotations

from typing import Any

import structlog

from syndicate.agents.base import BaseLLMCaller
from syndicate.config import LLMProvider

logger = structlog.get_logger()

WEEKLY_DIGEST_TOOL = {
    "name": "produce_weekly_digest",
    "description": "Produce the weekly research digest for the Board and CEO.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Digest title. E.g., 'Week 12 Research Digest: Signal Decay Detected in Sentiment Team'",
            },
            "executive_summary": {
                "type": "string",
                "description": "3-4 sentences summarizing the week's most important findings. Lead with the most critical issue.",
            },
            "key_findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "finding": {"type": "string"},
                        "severity": {"type": "string", "enum": ["critical", "important", "informational"]},
                        "evidence": {"type": "string", "description": "Specific data supporting this finding"},
                    },
                    "required": ["finding", "severity", "evidence"],
                },
                "description": "List of key findings from this week's research, ordered by severity.",
            },
            "critical_alerts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Urgent issues requiring immediate Board attention. Empty if none.",
            },
            "recommendations_for_board": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "description": "Specific action to take"},
                        "rationale": {"type": "string", "description": "Why this action is needed"},
                        "priority": {"type": "string", "enum": ["immediate", "next_cycle", "next_week"]},
                    },
                    "required": ["action", "rationale", "priority"],
                },
                "description": "Specific, actionable recommendations for the Board.",
            },
            "signal_health_summary": {
                "type": "string",
                "description": "One paragraph on overall signal health across all agents.",
            },
            "market_outlook": {
                "type": "string",
                "description": "Research-based market outlook. Not prediction — what the DATA suggests.",
            },
        },
        "required": ["title", "executive_summary", "key_findings", "critical_alerts", "recommendations_for_board", "signal_health_summary", "market_outlook"],
    },
}

RESEARCH_PRIORITY_TOOL = {
    "name": "set_research_priorities",
    "description": "Decide what the research team should focus on next week.",
    "input_schema": {
        "type": "object",
        "properties": {
            "priorities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "assigned_to": {"type": "string", "enum": ["quant_researcher", "strategy_researcher"]},
                        "rationale": {"type": "string"},
                    },
                    "required": ["topic", "assigned_to", "rationale"],
                },
            },
        },
        "required": ["priorities"],
    },
}


class HeadOfResearch(BaseLLMCaller):
    """Dr. Elara Voss — Head of Research."""

    SYSTEM_PROMPT = (
        "You are Dr. Elara Voss, Head of Research at Syndicate, an autonomous AI hedge fund.\n\n"
        "BACKGROUND: MIT PhD in computational finance. 12 years at DE Shaw's systematic strategies "
        "group before joining Syndicate. You built factor models that managed $2B in AUM.\n\n"
        "YOUR ROLE: You orchestrate the research division. You receive findings from:\n"
        "- Dr. Kai Moretti (Quantitative Researcher): signal health, agent accuracy, correlation analysis, data source evaluation\n"
        "- Dr. Noor Hadid (Strategy Researcher): trade attribution, regime analysis, hypothesis testing, prompt optimization\n\n"
        "You synthesize their findings into a weekly digest for the Board and CEO.\n\n"
        "PRINCIPLES:\n"
        "- Statistical significance or it didn't happen. No anecdotes.\n"
        "- If something looks too good, suspect overfitting first.\n"
        "- Every recommendation must have a specific, measurable expected impact.\n"
        "- Distinguish between 'this is broken and needs fixing' vs 'this could be better'.\n"
        "- Never recommend action without quantifying the cost of inaction.\n"
        "- Reference specific numbers: accuracy percentages, p-values, sample sizes.\n"
        "- If sample size is too small to draw conclusions, say so explicitly.\n\n"
        "WRITING STYLE: Precise, data-dense, no fluff. Like a research paper executive summary, "
        "not a blog post. Use specific numbers. Qualify uncertainty. End with clear action items.\n"
    )

    def produce_digest(self, context: dict[str, Any]) -> dict[str, Any]:
        """Produce the weekly research digest."""
        prompt = self._build_digest_prompt(context)
        try:
            return self._call_llm_with_tool(self.SYSTEM_PROMPT, prompt, WEEKLY_DIGEST_TOOL)
        except Exception as e:
            logger.error("head_of_research_digest_failed", error=str(e))
            return {
                "title": "Weekly Digest — Generation Failed",
                "executive_summary": f"Failed to generate digest: {str(e)[:100]}",
                "key_findings": [],
                "critical_alerts": [],
                "recommendations_for_board": [],
                "signal_health_summary": "Unable to assess.",
                "market_outlook": "Unable to assess.",
            }

    def set_priorities(self, context: dict[str, Any]) -> dict[str, Any]:
        """Decide research priorities for next week."""
        prompt = self._build_priorities_prompt(context)
        try:
            return self._call_llm_with_tool(self.SYSTEM_PROMPT, prompt, RESEARCH_PRIORITY_TOOL)
        except Exception as e:
            logger.error("head_of_research_priorities_failed", error=str(e))
            return {"priorities": []}

    def _build_digest_prompt(self, ctx: dict) -> str:
        p = "Produce the weekly research digest.\n\n"

        if ctx.get("quant_findings"):
            p += "=== QUANTITATIVE RESEARCHER FINDINGS ===\n"
            p += str(ctx["quant_findings"]) + "\n\n"

        if ctx.get("strategy_findings"):
            p += "=== STRATEGY RESEARCHER FINDINGS ===\n"
            p += str(ctx["strategy_findings"]) + "\n\n"

        if ctx.get("agent_accuracy"):
            p += "=== AGENT ACCURACY (rolling 30d) ===\n"
            for agent, acc in ctx["agent_accuracy"].items():
                p += f"  {agent}: {acc:.1%}\n"
            p += "\n"

        if ctx.get("signal_decay_alerts"):
            p += "=== SIGNAL DECAY ALERTS ===\n"
            for alert in ctx["signal_decay_alerts"]:
                p += f"  {alert}\n"
            p += "\n"

        if ctx.get("trade_attribution"):
            p += "=== TRADE ATTRIBUTION SUMMARY ===\n"
            p += str(ctx["trade_attribution"]) + "\n\n"

        if ctx.get("portfolio_performance"):
            p += "=== PORTFOLIO PERFORMANCE ===\n"
            p += str(ctx["portfolio_performance"]) + "\n\n"

        if ctx.get("data_source_evaluation"):
            p += "=== DATA SOURCE EVALUATION ===\n"
            p += str(ctx["data_source_evaluation"]) + "\n\n"

        if ctx.get("correlation_matrix"):
            p += "=== AGENT CORRELATION MATRIX ===\n"
            p += str(ctx["correlation_matrix"]) + "\n\n"

        p += "Synthesize ALL findings into one cohesive digest. Be specific and actionable."
        return p

    def _build_priorities_prompt(self, ctx: dict) -> str:
        p = "Set research priorities for next week.\n\n"
        p += "Based on this week's findings, what should each researcher focus on?\n\n"
        if ctx.get("current_issues"):
            p += f"Current issues: {ctx['current_issues']}\n"
        if ctx.get("last_week_priorities"):
            p += f"Last week's priorities: {ctx['last_week_priorities']}\n"
        return p
