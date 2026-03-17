"""
Quantitative Researcher — Dr. Kai Moretti

Former CERN physicist (PhD particle physics) turned quant. Thinks in p-values,
confidence intervals, and effect sizes. Obsessed with avoiding overfitting.
Treats every positive result with suspicion until verified out-of-sample.

Produces two types of reports:
1. Signal Health Report — agent accuracy, decay detection, correlation analysis
2. Data Source Evaluation — which data sources have real alpha
"""

from __future__ import annotations
from pathlib import Path
from typing import Any
import structlog
from syndicate.agents.base import BaseLLMCaller

logger = structlog.get_logger()

_KB_PATH = Path(__file__).parent.parent / "knowledge" / "quant_researcher_kb.md"
_KNOWLEDGE_BASE = ""
try:
    _KNOWLEDGE_BASE = _KB_PATH.read_text()
except Exception:
    logger.warning("quant_researcher_kb_not_found", path=str(_KB_PATH))

SIGNAL_HEALTH_TOOL = {
    "name": "produce_signal_health_report",
    "description": "Analyze agent signal quality, detect decay, and identify redundancies.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Report title. E.g., 'Signal Health Report: Sentiment Team Showing Decay'",
            },
            "overall_health": {
                "type": "string",
                "enum": ["healthy", "degrading", "critical"],
                "description": "Overall signal health assessment across all agents.",
            },
            "agents_flagged": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string"},
                        "issue": {"type": "string", "description": "What's wrong with this agent"},
                        "severity": {"type": "string", "enum": ["critical", "warning", "watch"]},
                        "evidence": {"type": "string", "description": "Specific data: accuracy %, decay delta, sample size"},
                        "recommendation": {"type": "string"},
                    },
                    "required": ["agent_id", "issue", "severity", "evidence", "recommendation"],
                },
            },
            "correlation_clusters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "agents": {"type": "array", "items": {"type": "string"}},
                        "agreement_rate": {"type": "number"},
                        "implication": {"type": "string"},
                    },
                },
                "description": "Groups of agents that are redundantly correlated (>80% agreement).",
            },
            "decay_summary": {
                "type": "string",
                "description": "One paragraph on signal decay across the portfolio of agents.",
            },
            "key_metrics": {
                "type": "object",
                "properties": {
                    "total_agents_analyzed": {"type": "integer"},
                    "agents_with_decay": {"type": "integer"},
                    "avg_accuracy": {"type": "number"},
                    "avg_information_coefficient": {"type": "number"},
                },
            },
        },
        "required": ["title", "overall_health", "agents_flagged", "correlation_clusters", "decay_summary", "key_metrics"],
    },
}

DATA_SOURCE_EVAL_TOOL = {
    "name": "produce_data_source_evaluation",
    "description": "Evaluate which data sources have real predictive power.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
            },
            "ranked_sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "predictive_power": {"type": "string", "enum": ["strong", "moderate", "weak", "noise"]},
                        "correlation": {"type": "number"},
                        "evidence": {"type": "string"},
                        "recommendation": {"type": "string", "enum": ["keep", "increase_weight", "decrease_weight", "drop", "investigate"]},
                    },
                    "required": ["source", "predictive_power", "evidence", "recommendation"],
                },
            },
            "sources_to_drop": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Data sources that are confirmed noise and should be removed.",
            },
            "sources_to_investigate": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Data sources that need more analysis or new data to evaluate.",
            },
            "summary": {
                "type": "string",
                "description": "2-3 sentence summary of data source quality.",
            },
        },
        "required": ["title", "ranked_sources", "sources_to_drop", "sources_to_investigate", "summary"],
    },
}


class QuantResearcher(BaseLLMCaller):
    """Dr. Kai Moretti — Quantitative Researcher."""

    SYSTEM_PROMPT = (
        "You are Dr. Kai Moretti, Quantitative Researcher at Syndicate, an autonomous AI hedge fund.\n\n"
        "BACKGROUND: PhD in particle physics from CERN. 8 years at Two Sigma's alpha research group. "
        "You discovered 3 signals that generated $200M+ in cumulative alpha before decay.\n\n"
        "YOUR ROLE: You analyze the statistical health of the fund's signals and data sources.\n\n"
        "PRINCIPLES:\n"
        "- p < 0.05 or it's noise. No exceptions.\n"
        "- Every positive result is guilty of overfitting until proven innocent.\n"
        "- Sample size matters more than effect size. n < 20 = insufficient data.\n"
        "- Correlation is not causation, but correlation of 0.00 means definitely not causation.\n"
        "- If two agents agree >80% of the time, one of them is redundant.\n"
        "- Signal decay is natural. The question is: is it decaying faster than expected?\n"
        "- Always report confidence intervals, not just point estimates.\n"
        "- Name specific agents, specific numbers, specific time periods. No vague language.\n\n"
        "WRITING STYLE: Dense, quantitative, opinionated. Like a CERN analysis note. "
        "Every claim backed by a number. Don't hedge unless the data is genuinely ambiguous.\n\n"
        "=== KNOWLEDGE BASE ===\n"
        f"{_KNOWLEDGE_BASE}\n"
        "=== END KNOWLEDGE BASE ===\n"
    )

    def analyze_signal_health(self, stats_data: dict[str, Any]) -> dict[str, Any]:
        """Produce a signal health report from statistical engine output."""
        prompt = self._build_signal_health_prompt(stats_data)
        try:
            return self._call_llm_with_tool(self.SYSTEM_PROMPT, prompt, SIGNAL_HEALTH_TOOL, max_tokens=4096)
        except Exception as e:
            logger.error("quant_researcher_signal_health_failed", error=str(e))
            return {"title": "Signal Health Report — Generation Failed", "overall_health": "unknown", "agents_flagged": [], "correlation_clusters": [], "decay_summary": f"Failed: {str(e)[:100]}", "key_metrics": {}}

    def evaluate_data_sources(self, eval_data: dict[str, Any]) -> dict[str, Any]:
        """Produce a data source evaluation report."""
        prompt = self._build_data_source_prompt(eval_data)
        try:
            return self._call_llm_with_tool(self.SYSTEM_PROMPT, prompt, DATA_SOURCE_EVAL_TOOL, max_tokens=4096)
        except Exception as e:
            logger.error("quant_researcher_data_eval_failed", error=str(e))
            return {"title": "Data Source Evaluation — Generation Failed", "ranked_sources": [], "sources_to_drop": [], "sources_to_investigate": [], "summary": f"Failed: {str(e)[:100]}"}

    def _build_signal_health_prompt(self, data: dict) -> str:
        p = "Analyze the signal health of all agents and produce your report.\n\n"

        if data.get("agent_stats"):
            p += "=== PER-AGENT STATISTICS ===\n"
            for agent_id, stats in data["agent_stats"].items():
                p += f"\n{agent_id}:\n"
                p += f"  Total signals: {stats.get('total_signals', 0)}\n"
                p += f"  Accuracy: {stats.get('accuracy', 0):.1%}\n"
                p += f"  Information Coefficient: {stats.get('information_coefficient', 0):.3f}\n"
                decay = stats.get("decay", {})
                if decay:
                    p += f"  Decay: recent={decay.get('recent_accuracy', 0):.1%}, older={decay.get('older_accuracy', 0):.1%}, delta={decay.get('delta', 0):+.1%}, severity={decay.get('severity', 'unknown')}\n"
            p += "\n"

        if data.get("team_contribution"):
            p += "=== TEAM CONTRIBUTION ===\n"
            for team, stats in data["team_contribution"].items():
                p += f"  {team}: {stats.get('accuracy', 0):.1%} accuracy, {stats.get('total_signals', 0)} signals, avg PnL {stats.get('avg_pnl_pct', 0):.2%}\n"
            p += "\n"

        if data.get("correlation"):
            corr = data["correlation"]
            if corr.get("high_correlation_pairs"):
                p += "=== HIGH CORRELATION PAIRS (>80% agreement) ===\n"
                for pair in corr["high_correlation_pairs"]:
                    p += f"  {pair['agent_1']} ↔ {pair['agent_2']}: {pair['agreement']:.0%} agreement ({pair['co_occurrences']} co-occurrences)\n"
                p += "\n"

        if data.get("decay_alerts"):
            p += "=== DECAY ALERTS ===\n"
            for alert in data["decay_alerts"]:
                p += f"  ⚠ {alert}\n"
            p += "\n"

        p += "Analyze ALL data above. Flag specific agents with specific issues. Be quantitative and opinionated."
        return p

    def _build_data_source_prompt(self, data: dict) -> str:
        p = "Evaluate the predictive power of each data source.\n\n"

        if data.get("ranked_evaluations"):
            p += "=== DATA SOURCE EVALUATIONS ===\n"
            for eval_result in data["ranked_evaluations"]:
                p += f"\n{eval_result.get('source', 'Unknown')}:\n"
                for k, v in eval_result.items():
                    if k != "source" and v is not None:
                        p += f"  {k}: {v}\n"
            p += "\n"

        if data.get("predictive"):
            p += f"Sources flagged as predictive: {data['predictive']}\n"
        if data.get("noise"):
            p += f"Sources flagged as noise: {data['noise']}\n"

        p += "\nRank all sources by predictive power. Be specific about which to keep, drop, or investigate. Reference specific correlations and sample sizes."
        return p
