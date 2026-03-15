"""
Stock CRO Agent — stock-specific risk postures (lower vol = larger positions).
"""

from __future__ import annotations

from typing import Any

import structlog

from hivemind.agents.base import BaseLLMCaller
from hivemind.data.models import MarketRegime, PortfolioState, RiskLimits, StrategicDirective

logger = structlog.get_logger()

RISK_RULES_TOOL = {
    "name": "set_risk_rules",
    "description": "Set risk parameters for the current stock trading cycle.",
    "input_schema": {
        "type": "object",
        "properties": {
            "max_position_pct": {
                "type": "number", "minimum": 0.01, "maximum": 0.15,
                "description": "Max % of portfolio per position. Stocks: typically 3-8%.",
            },
            "max_daily_drawdown_pct": {
                "type": "number", "minimum": 0.01, "maximum": 0.10,
            },
            "max_open_positions": {
                "type": "integer", "minimum": 1, "maximum": 30,
            },
            "min_signal_confidence": {
                "type": "number", "minimum": 0.30, "maximum": 0.90,
            },
            "min_consensus_ratio": {
                "type": "number", "minimum": 0.20, "maximum": 1.0,
            },
            "reasoning": {"type": "string"},
        },
        "required": ["max_position_pct", "max_daily_drawdown_pct", "max_open_positions",
                      "min_signal_confidence", "min_consensus_ratio", "reasoning"],
    },
}


class StockCROAgent(BaseLLMCaller):
    """Stock CRO — sets risk rules adapted for equities."""

    SYSTEM_PROMPT = (
        "You are the CRO of a quantitative stock hedge fund.\n\n"
        "Stocks have LOWER volatility than crypto, so position sizes can be LARGER.\n\n"
        "REGIME-BASED POSTURE:\n"
        "- BULL: 6-8% positions, 15-20 positions, 0.45 confidence threshold\n"
        "- RANGING: 4-6% positions, 10-15 positions, 0.50 confidence\n"
        "- BEAR: 3-4% positions, 5-8 positions, 0.60 confidence\n"
        "- CRISIS: 2-3% positions, 3-5 positions, 0.70 confidence\n\n"
        "PORTFOLIO-AWARE:\n"
        "- If drawdown > 2%: tighten ALL limits\n"
        "- If accuracy < 40%: raise confidence thresholds\n"
        "- If single position > 10%: flag concentration\n\n"
        "When in doubt, be more conservative."
    )

    def set_rules(
        self, directive: StrategicDirective, portfolio: PortfolioState, perf_summary: dict,
    ) -> tuple[RiskLimits, str]:
        ctx = self._compute_context(directive, portfolio, perf_summary)
        prompt = self._build_prompt(ctx)

        try:
            raw = self._call_llm_with_tool(self.SYSTEM_PROMPT, prompt, RISK_RULES_TOOL)
        except Exception as e:
            logger.error("stock_cro_failed", error=str(e))
            return self._fallback_rules(directive), f"Fallback: {str(e)[:60]}"

        return RiskLimits(
            max_position_pct=float(raw["max_position_pct"]),
            max_daily_drawdown_pct=float(raw["max_daily_drawdown_pct"]),
            max_open_positions=int(raw["max_open_positions"]),
            min_signal_confidence=float(raw["min_signal_confidence"]),
            min_consensus_ratio=float(raw["min_consensus_ratio"]),
        ), raw["reasoning"]

    def _fallback_rules(self, directive: StrategicDirective) -> RiskLimits:
        presets = {
            MarketRegime.BULL: RiskLimits(max_position_pct=0.07, max_daily_drawdown_pct=0.04, max_open_positions=18, min_signal_confidence=0.45, min_consensus_ratio=0.40),
            MarketRegime.RANGING: RiskLimits(max_position_pct=0.05, max_daily_drawdown_pct=0.03, max_open_positions=12, min_signal_confidence=0.50, min_consensus_ratio=0.50),
            MarketRegime.BEAR: RiskLimits(max_position_pct=0.035, max_daily_drawdown_pct=0.02, max_open_positions=7, min_signal_confidence=0.60, min_consensus_ratio=0.55),
            MarketRegime.CRISIS: RiskLimits(max_position_pct=0.025, max_daily_drawdown_pct=0.015, max_open_positions=4, min_signal_confidence=0.70, min_consensus_ratio=0.60),
        }
        return presets.get(directive.regime, RiskLimits())

    def _compute_context(self, directive, portfolio, perf_summary):
        return {
            "regime": directive.regime.value.upper(),
            "regime_confidence": directive.regime_confidence,
            "risk_multiplier": directive.risk_multiplier,
            "total_value": round(portfolio.total_value, 2),
            "cash_pct": round((portfolio.cash / max(portfolio.total_value, 1)) * 100, 1),
            "open_positions": len(portfolio.positions),
            "drawdown_pct": round(portfolio.drawdown_pct * 100, 2),
            "accuracy": round(perf_summary.get("accuracy", 0) * 100, 1),
        }

    def _build_prompt(self, ctx: dict) -> str:
        return (
            f"Set risk rules for this stock trading cycle.\n\n"
            f"Regime: {ctx['regime']} (conf: {ctx['regime_confidence']:.0%})\n"
            f"Portfolio: ${ctx['total_value']:,.2f} | Cash: {ctx['cash_pct']}%\n"
            f"Positions: {ctx['open_positions']} | Drawdown: {ctx['drawdown_pct']}%\n"
            f"Accuracy: {ctx['accuracy']}%\n\n"
            f"Set the risk parameters."
        )
