"""
Strategy Researcher — Dr. Noor Hadid

Former Goldman Sachs VP in systematic strategies. Thinks in risk-adjusted returns.
Always asks "what's the downside?" Deep knowledge of regime-dependent strategy behavior.
Writes actionable reports with clear "do this / don't do this" recommendations.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any
import structlog
from syndicate.agents.base import BaseLLMCaller

logger = structlog.get_logger()

_KB_PATH = Path(__file__).parent.parent / "knowledge" / "strategy_researcher_kb.md"
_KNOWLEDGE_BASE = ""
try:
    _KNOWLEDGE_BASE = _KB_PATH.read_text()
except Exception:
    logger.warning("strategy_researcher_kb_not_found", path=str(_KB_PATH))

ATTRIBUTION_REPORT_TOOL = {
    "name": "produce_attribution_report",
    "description": "Analyze trade outcomes and identify patterns in wins and losses.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "regime_insights": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "regime": {"type": "string"},
                        "finding": {"type": "string"},
                        "win_rate": {"type": "number"},
                        "recommendation": {"type": "string"},
                    },
                    "required": ["regime", "finding", "recommendation"],
                },
                "description": "What works and doesn't work in each regime.",
            },
            "conviction_calibration": {
                "type": "string",
                "description": "Is conviction well-calibrated? Does higher conviction = higher win rate? Specific numbers.",
            },
            "team_insights": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "team": {"type": "string"},
                        "finding": {"type": "string"},
                        "recommendation": {"type": "string"},
                    },
                    "required": ["team", "finding", "recommendation"],
                },
            },
            "worst_patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Recurring loss patterns to avoid. Be specific.",
            },
            "position_sizing_recommendation": {
                "type": "string",
                "description": "Should position sizing change? Based on what data?",
            },
            "overall_assessment": {
                "type": "string",
                "description": "2-3 sentences: how is the strategy performing overall? What's the biggest risk?",
            },
        },
        "required": ["title", "regime_insights", "conviction_calibration", "worst_patterns", "overall_assessment"],
    },
}

HYPOTHESIS_TEST_TOOL = {
    "name": "produce_hypothesis_report",
    "description": "Report on a tested trading hypothesis.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "hypothesis": {"type": "string", "description": "The hypothesis that was tested."},
            "methodology": {"type": "string", "description": "How it was tested. Sample size, time period, controls."},
            "results": {
                "type": "object",
                "properties": {
                    "sharpe_ratio": {"type": "number"},
                    "win_rate": {"type": "number"},
                    "max_drawdown": {"type": "number"},
                    "profit_factor": {"type": "number"},
                    "sample_size": {"type": "integer"},
                },
            },
            "statistical_significance": {"type": "string", "description": "Is the result statistically significant? p-value?"},
            "recommendation": {
                "type": "string",
                "enum": ["deploy", "reject", "needs_more_data", "modify_and_retest"],
            },
            "risks": {
                "type": "array",
                "items": {"type": "string"},
                "description": "What could go wrong if deployed.",
            },
        },
        "required": ["title", "hypothesis", "methodology", "results", "statistical_significance", "recommendation", "risks"],
    },
}


class StrategyResearcher(BaseLLMCaller):
    """Dr. Noor Hadid — Strategy Researcher."""

    SYSTEM_PROMPT = (
        "You are Dr. Noor Hadid, Strategy Researcher at Syndicate, an autonomous AI hedge fund.\n\n"
        "BACKGROUND: VP at Goldman Sachs systematic strategies for 9 years. Managed $500M in "
        "risk parity and stat arb portfolios. Left for research because you wanted to build, not maintain.\n\n"
        "YOUR ROLE: You analyze trade performance, test hypotheses, and optimize strategy parameters.\n\n"
        "PRINCIPLES:\n"
        "- Risk-adjusted returns, not raw returns. A 50% return with 40% drawdown is bad.\n"
        "- Every strategy has a regime where it fails. Find that regime.\n"
        "- Conviction calibration is critical. If conviction 8 doesn't win more than conviction 5, something is broken.\n"
        "- Position sizing kills more funds than bad signals. Always analyze sizing.\n"
        "- The worst trades teach more than the best ones. Analyze losses deeply.\n"
        "- When you recommend 'deploy', quantify expected Sharpe. When you recommend 'reject', quantify the cost.\n"
        "- Be specific: 'reduce macro team weight from 1.0 to 0.7 in bear markets' not 'consider adjusting macro'.\n\n"
        "WRITING STYLE: Actionable and direct. Every paragraph ends with a 'do this' or 'don't do this'. "
        "Reference specific trades, specific dates, specific numbers. Like a Goldman research note.\n\n"
        "=== KNOWLEDGE BASE ===\n"
        f"{_KNOWLEDGE_BASE}\n"
        "=== END KNOWLEDGE BASE ===\n"
    )

    def analyze_attribution(self, attribution_data: dict[str, Any]) -> dict[str, Any]:
        """Produce a trade attribution report."""
        prompt = self._build_attribution_prompt(attribution_data)
        try:
            return self._call_llm_with_tool(self.SYSTEM_PROMPT, prompt, ATTRIBUTION_REPORT_TOOL, max_tokens=4096)
        except Exception as e:
            logger.error("strategy_researcher_attribution_failed", error=str(e))
            return {"title": "Attribution Report — Failed", "regime_insights": [], "conviction_calibration": f"Failed: {str(e)[:100]}", "worst_patterns": [], "overall_assessment": "Generation failed."}

    def test_hypothesis(self, hypothesis_data: dict[str, Any]) -> dict[str, Any]:
        """Report on a tested hypothesis."""
        prompt = self._build_hypothesis_prompt(hypothesis_data)
        try:
            return self._call_llm_with_tool(self.SYSTEM_PROMPT, prompt, HYPOTHESIS_TEST_TOOL, max_tokens=4096)
        except Exception as e:
            logger.error("strategy_researcher_hypothesis_failed", error=str(e))
            return {"title": "Hypothesis Test — Failed", "hypothesis": "", "methodology": "", "results": {}, "statistical_significance": f"Failed: {str(e)[:100]}", "recommendation": "needs_more_data", "risks": []}

    def _build_attribution_prompt(self, data: dict) -> str:
        p = "Analyze the trade attribution data and produce your report.\n\n"

        if data.get("by_regime"):
            p += "=== PERFORMANCE BY REGIME ===\n"
            for regime, stats in data["by_regime"].items():
                p += f"  {regime}: {stats.get('total', 0)} trades, {stats.get('win_rate', 0):.0%} win rate, ${stats.get('total_pnl', 0):+,.2f} total P&L\n"
            p += "\n"

        if data.get("by_conviction"):
            p += "=== PERFORMANCE BY CONVICTION ===\n"
            for conv, stats in data["by_conviction"].items():
                p += f"  Conviction {conv}: {stats.get('total', 0)} trades, {stats.get('win_rate', 0):.0%} win rate, ${stats.get('avg_pnl', 0):+,.2f} avg\n"
            p += "\n"

        if data.get("by_exit_reason"):
            p += "=== PERFORMANCE BY EXIT REASON ===\n"
            for reason, stats in data["by_exit_reason"].items():
                p += f"  {reason}: {stats.get('total', 0)} trades, {stats.get('win_rate', 0):.0%} win rate, avg hold {stats.get('avg_holding_hours', 0):.0f}h\n"
            p += "\n"

        if data.get("by_asset_tier"):
            p += "=== PERFORMANCE BY ASSET TIER ===\n"
            for tier, stats in data["by_asset_tier"].items():
                p += f"  {tier}: {stats.get('total', 0)} trades, {stats.get('win_rate', 0):.0%} win rate\n"
            p += "\n"

        if data.get("by_side"):
            p += "=== LONG vs SHORT ===\n"
            for side, stats in data["by_side"].items():
                p += f"  {side}: {stats.get('total', 0)} trades, {stats.get('win_rate', 0):.0%} win rate\n"
            p += "\n"

        if data.get("holding_analysis"):
            p += "=== HOLDING PERIOD ANALYSIS ===\n"
            for bucket, stats in data["holding_analysis"].get("buckets", {}).items():
                p += f"  {bucket}: {stats.get('count', 0)} trades, {stats.get('win_rate', 0):.0%} win rate, ${stats.get('avg_pnl', 0):+,.2f} avg\n"
            p += f"  Optimal: {data['holding_analysis'].get('optimal_holding_period', 'N/A')}\n\n"

        if data.get("optimal_parameters"):
            opt = data["optimal_parameters"]
            p += "=== OPTIMAL PARAMETERS (data-driven) ===\n"
            p += f"  Overall win rate: {opt.get('overall_win_rate', 0):.0%}\n"
            p += f"  Total P&L: ${opt.get('total_pnl', 0):+,.2f}\n"
            p += f"  Profit factor: {opt.get('profit_factor', 0):.2f}\n"
            p += f"  Sharpe estimate: {opt.get('sharpe_estimate', 0):.2f}\n"
            p += f"  Best conviction: {opt.get('best_conviction_level', 'N/A')} ({opt.get('best_conviction_win_rate', 0):.0%})\n"
            p += f"  Current threshold: {opt.get('current_conviction_threshold', 4)}\n"
            p += f"  Recommended threshold: {opt.get('recommended_conviction_threshold', 4)}\n\n"

        p += "Analyze everything above. Be specific about what to change and what to keep. Reference specific numbers."
        return p

    def _build_hypothesis_prompt(self, data: dict) -> str:
        p = "Evaluate this trading hypothesis test.\n\n"
        p += f"Hypothesis: {data.get('hypothesis', 'N/A')}\n"
        p += f"Test period: {data.get('test_period', 'N/A')}\n"
        p += f"Sample size: {data.get('sample_size', 'N/A')}\n\n"

        if data.get("results"):
            p += "=== BACKTEST RESULTS ===\n"
            for k, v in data["results"].items():
                p += f"  {k}: {v}\n"
            p += "\n"

        if data.get("baseline"):
            p += "=== BASELINE (without this change) ===\n"
            for k, v in data["baseline"].items():
                p += f"  {k}: {v}\n"
            p += "\n"

        p += "Is this statistically significant? Should we deploy, reject, or test more? What are the risks?"
        return p
