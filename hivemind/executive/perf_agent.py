"""
Performance Agent — Evaluates agents and recommends fire/promote/rebalance.

Runs after each cycle. Reviews signal accuracy per team and per agent,
and makes personnel decisions:
- FIRE:    Remove underperformers (accuracy < 30% over 20+ signals)
- PROMOTE: Increase weight of consistent performers (accuracy > 65% over 20+ signals)
- REBALANCE: Adjust team weights in the aggregator

The Performance Tracker (evaluation/performance_tracker.py) collects the DATA.
This agent makes DECISIONS based on that data.

Follows the pre-compute pattern.
"""

from __future__ import annotations

from typing import Any

import structlog

from hivemind.agents.base import BaseLLMCaller
from hivemind.config import LLMProvider

logger = structlog.get_logger()

PERF_REVIEW_TOOL = {
    "name": "performance_review",
    "description": (
        "Review agent/team performance and recommend actions. "
        "You MUST call this tool with your review."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "actions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Team name or agent ID being acted on.",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["FIRE", "PROMOTE", "WARN", "NO_ACTION"],
                            "description": (
                                "FIRE = remove from rotation. "
                                "PROMOTE = increase weight. "
                                "WARN = flag for monitoring. "
                                "NO_ACTION = performing adequately."
                            ),
                        },
                        "reason": {
                            "type": "string",
                            "description": "Brief explanation for this action.",
                        },
                    },
                    "required": ["target", "action", "reason"],
                },
                "description": "List of actions for each team/agent reviewed.",
            },
            "overall_assessment": {
                "type": "string",
                "description": "2-3 sentence summary of fund performance and recommendations.",
            },
        },
        "required": ["actions", "overall_assessment"],
    },
}


class PerformanceReview:
    """Result of a performance evaluation cycle."""

    def __init__(self, actions: list[dict], overall_assessment: str) -> None:
        self.actions = actions
        self.overall_assessment = overall_assessment

    @property
    def fires(self) -> list[dict]:
        return [a for a in self.actions if a["action"] == "FIRE"]

    @property
    def promotions(self) -> list[dict]:
        return [a for a in self.actions if a["action"] == "PROMOTE"]

    @property
    def warnings(self) -> list[dict]:
        return [a for a in self.actions if a["action"] == "WARN"]


def compute_perf_context(
    team_stats: dict[str, dict],
    overall_summary: dict,
    portfolio_return_pct: float,
) -> dict[str, Any]:
    """
    Pre-compute performance context for the Perf Agent.
    All math happens here.
    """
    ctx: dict[str, Any] = {}

    ctx["portfolio_return_pct"] = round(portfolio_return_pct, 2)
    ctx["total_signals"] = overall_summary.get("total_signals", 0)
    ctx["overall_accuracy"] = round(overall_summary.get("accuracy", 0) * 100, 1)
    ctx["correct"] = overall_summary.get("correct", 0)
    ctx["incorrect"] = overall_summary.get("incorrect", 0)
    ctx["pending"] = overall_summary.get("pending", 0)

    # Per-team breakdown
    teams = []
    for team_name, stats in team_stats.items():
        total = stats.get("total", 0)
        correct = stats.get("correct", 0)
        incorrect = stats.get("incorrect", 0)
        accuracy = round(stats.get("accuracy", 0) * 100, 1)
        pending = stats.get("pending", 0)

        # Auto-classification
        if total >= 20 and accuracy < 30:
            status = "UNDERPERFORMING — Fire candidate"
        elif total >= 20 and accuracy > 65:
            status = "STRONG — Promote candidate"
        elif total >= 10 and accuracy < 40:
            status = "WEAK — Warning"
        elif total < 10:
            status = "INSUFFICIENT DATA"
        else:
            status = "ADEQUATE"

        teams.append({
            "name": team_name,
            "total": total,
            "correct": correct,
            "incorrect": incorrect,
            "accuracy": accuracy,
            "pending": pending,
            "status": status,
        })

    # Sort by accuracy descending
    teams.sort(key=lambda x: -x["accuracy"])
    ctx["teams"] = teams

    return ctx


class PerfAgent(BaseLLMCaller):
    """
    Performance Agent — reviews team/agent performance and recommends actions.
    """

    SYSTEM_PROMPT = (
        "You are the Performance Evaluator of a quantitative crypto hedge fund.\n\n"
        "Your job is to review agent and team performance, and make PERSONNEL DECISIONS:\n"
        "- FIRE: Remove agents/teams with sustained poor accuracy.\n"
        "- PROMOTE: Increase weight of consistently accurate agents/teams.\n"
        "- WARN: Flag agents/teams showing declining performance.\n"
        "- NO_ACTION: Performing within acceptable range.\n\n"
        "DECISION THRESHOLDS:\n"
        "- FIRE: Accuracy < 30% over 20+ evaluated signals. This team is actively losing money.\n"
        "- PROMOTE: Accuracy > 65% over 20+ evaluated signals. This team has a real edge.\n"
        "- WARN: Accuracy 30-40% over 10+ signals. On notice.\n"
        "- NO_ACTION: Accuracy 40-65%, or insufficient data (<10 evaluated signals).\n\n"
        "IMPORTANT CONTEXT:\n"
        "- Do NOT fire teams with < 20 evaluated signals. They need time to prove themselves.\n"
        "- Do NOT promote teams with < 20 evaluated signals. Could be luck.\n"
        "- In early cycles (< 50 total signals), default to NO_ACTION for everyone — "
        "the fund is still calibrating.\n"
        "- Consider the portfolio return alongside individual accuracy. A team with 50% accuracy "
        "but that catches big moves might be more valuable than one with 60% accuracy on small moves.\n\n"
        "RULES:\n"
        "- Do NOT invent data. Only reference the provided metrics.\n"
        "- Do NOT do math. All metrics are pre-computed.\n"
        "- Review EVERY team in the input. Don't skip any.\n"
        "- Keep the overall assessment to 2-3 sentences.\n"
        "- Be fair but decisive. If the numbers say fire, fire."
    )

    def review(
        self,
        team_stats: dict[str, dict],
        overall_summary: dict,
        portfolio_return_pct: float,
    ) -> PerformanceReview:
        """
        Review performance and produce fire/promote/warn recommendations.
        """
        ctx = compute_perf_context(team_stats, overall_summary, portfolio_return_pct)

        # If too few signals, skip LLM call entirely
        if ctx["total_signals"] < 10:
            return PerformanceReview(
                actions=[{"target": t["name"], "action": "NO_ACTION", "reason": "Insufficient data"} for t in ctx["teams"]],
                overall_assessment="Fund is in early calibration phase. Insufficient signal history for meaningful evaluation.",
            )

        prompt = self._build_prompt(ctx)

        try:
            raw = self._call_llm_with_tool(self.SYSTEM_PROMPT, prompt, PERF_REVIEW_TOOL)
        except Exception as e:
            logger.error("perf_agent_review_failed", error=str(e))
            return PerformanceReview(
                actions=[{"target": t["name"], "action": "NO_ACTION", "reason": "Review failed"} for t in ctx["teams"]],
                overall_assessment=f"Performance review failed: {str(e)[:80]}",
            )

        return PerformanceReview(
            actions=raw["actions"],
            overall_assessment=raw["overall_assessment"],
        )

    def _build_prompt(self, ctx: dict) -> str:
        prompt = (
            f"Review fund performance and recommend actions.\n\n"
            f"=== FUND OVERVIEW ===\n"
            f"Portfolio Return: {ctx['portfolio_return_pct']:+.2f}%\n"
            f"Total Signals Tracked: {ctx['total_signals']}\n"
            f"Overall Accuracy: {ctx['overall_accuracy']}% "
            f"({ctx['correct']} correct, {ctx['incorrect']} incorrect, {ctx['pending']} pending)\n\n"
            f"=== TEAM PERFORMANCE ===\n"
        )

        for team in ctx["teams"]:
            prompt += (
                f"\n{team['name'].upper()}:\n"
                f"  Signals: {team['total']} total ({team['correct']}C / {team['incorrect']}I / {team['pending']}P)\n"
                f"  Accuracy: {team['accuracy']}%\n"
                f"  Status: {team['status']}\n"
            )

        prompt += "\nReview each team and recommend actions."
        return prompt
