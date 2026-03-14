"""
CRO Agent — Chief Risk Officer.

Dynamically sets risk rules based on market regime, portfolio state,
and recent performance. The Risk Manager enforces whatever the CRO decides.

Separation of concerns:
- CRO SETS the rules (this file)
- Risk Manager ENFORCES the rules (risk/risk_manager.py)

Follows the pre-compute pattern: Python computes portfolio/market risk metrics,
LLM makes judgment calls on appropriate limits.
"""

from __future__ import annotations

from typing import Any

import structlog

from hivemind.agents.base import BaseLLMCaller
from hivemind.config import LLMProvider
from hivemind.data.models import MarketRegime, PortfolioState, RegimeClassification, RiskLimits, StrategicDirective

logger = structlog.get_logger()

RISK_RULES_TOOL = {
    "name": "set_risk_rules",
    "description": (
        "Set the risk parameters for the current cycle based on market conditions "
        "and portfolio state. You MUST call this tool."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "max_position_pct": {
                "type": "number",
                "minimum": 0.01,
                "maximum": 0.15,
                "description": (
                    "Maximum % of portfolio per position. "
                    "Normal: 0.05 (5%). Conservative: 0.02-0.03. Aggressive: 0.07-0.10."
                ),
            },
            "max_daily_drawdown_pct": {
                "type": "number",
                "minimum": 0.01,
                "maximum": 0.10,
                "description": (
                    "Maximum daily drawdown before halting all trading. "
                    "Normal: 0.03 (3%). Conservative: 0.01-0.02. Aggressive: 0.04-0.05."
                ),
            },
            "max_open_positions": {
                "type": "integer",
                "minimum": 1,
                "maximum": 30,
                "description": (
                    "Maximum number of concurrent positions. "
                    "Normal: 10-15. Conservative: 3-5. Aggressive: 15-25."
                ),
            },
            "min_signal_confidence": {
                "type": "number",
                "minimum": 0.30,
                "maximum": 0.90,
                "description": (
                    "Minimum confidence threshold to accept a signal. "
                    "Normal: 0.50. Conservative: 0.60-0.70. Aggressive: 0.40."
                ),
            },
            "min_consensus_ratio": {
                "type": "number",
                "minimum": 0.20,
                "maximum": 1.0,
                "description": (
                    "Minimum team consensus to accept a signal. "
                    "Normal: 0.50. Conservative: 0.67. Aggressive: 0.33."
                ),
            },
            "reasoning": {
                "type": "string",
                "description": "2-3 sentences explaining your risk posture for this cycle.",
            },
        },
        "required": [
            "max_position_pct",
            "max_daily_drawdown_pct",
            "max_open_positions",
            "min_signal_confidence",
            "min_consensus_ratio",
            "reasoning",
        ],
    },
}


def compute_risk_context(
    directive: StrategicDirective | RegimeClassification,
    portfolio: PortfolioState,
    perf_summary: dict,
) -> dict[str, Any]:
    """
    Pre-compute risk context metrics for the CRO.
    All math happens here. Accepts either StrategicDirective or legacy RegimeClassification.
    """
    ctx: dict[str, Any] = {}

    # Regime — works with both types
    if isinstance(directive, StrategicDirective):
        ctx["regime"] = directive.regime.value.upper()
        ctx["regime_confidence"] = directive.regime_confidence
        ctx["risk_multiplier"] = directive.risk_multiplier
        ctx["ceo_strategy"] = directive.focus_strategy
        ctx["ceo_sector_weights"] = directive.sector_weights
    else:
        ctx["regime"] = directive.regime.value.upper()
        ctx["regime_confidence"] = directive.confidence
        ctx["risk_multiplier"] = directive.risk_multiplier

    # Portfolio state
    ctx["total_value"] = round(portfolio.total_value, 2)
    ctx["cash"] = round(portfolio.cash, 2)
    ctx["cash_pct"] = round((portfolio.cash / max(portfolio.total_value, 1)) * 100, 1)
    ctx["open_positions"] = len(portfolio.positions)
    ctx["drawdown_pct"] = round(portfolio.drawdown_pct * 100, 2)
    ctx["realized_pnl"] = round(portfolio.total_realized_pnl, 2)
    ctx["unrealized_pnl"] = round(portfolio.total_unrealized_pnl, 2)

    # Position concentration
    if portfolio.positions:
        weights = [
            (p.symbol, round((p.notional_value / max(portfolio.total_value, 1)) * 100, 1))
            for p in portfolio.positions
        ]
        weights.sort(key=lambda x: -x[1])
        ctx["top_positions"] = weights[:5]
        ctx["max_position_weight"] = weights[0][1] if weights else 0
    else:
        ctx["top_positions"] = []
        ctx["max_position_weight"] = 0

    # Performance context
    ctx["total_signals_tracked"] = perf_summary.get("total_signals", 0)
    ctx["accuracy"] = round(perf_summary.get("accuracy", 0) * 100, 1)
    ctx["pending_signals"] = perf_summary.get("pending", 0)

    # Risk assessment
    if portfolio.drawdown_pct > 0.02:
        ctx["drawdown_status"] = "WARNING — Approaching drawdown limit"
    elif portfolio.drawdown_pct > 0.01:
        ctx["drawdown_status"] = "ELEVATED — Monitor closely"
    else:
        ctx["drawdown_status"] = "NORMAL"

    # Suggested posture based on regime
    posture_map = {
        "BULL": "AGGRESSIVE",
        "RANGING": "NORMAL",
        "BEAR": "CONSERVATIVE",
        "CRISIS": "DEFENSIVE",
    }
    ctx["suggested_posture"] = posture_map.get(ctx["regime"], "NORMAL")

    return ctx


class CROAgent(BaseLLMCaller):
    """
    CRO agent — dynamically sets risk rules each cycle.
    """

    SYSTEM_PROMPT = (
        "You are the Chief Risk Officer (CRO) of a quantitative crypto hedge fund.\n\n"
        "Your job is to SET the risk parameters for this trading cycle. "
        "The Risk Manager will ENFORCE whatever rules you decide.\n\n"
        "You receive pre-computed metrics about:\n"
        "- Market regime (from the CEO)\n"
        "- Current portfolio state (positions, drawdown, P&L)\n"
        "- Recent performance (signal accuracy)\n\n"
        "RISK POSTURE BY REGIME:\n"
        "- BULL (Aggressive): Larger positions (5-8%), looser confidence (0.40-0.50), "
        "more positions (15-20). Lean into momentum.\n"
        "- RANGING (Normal): Standard positions (4-5%), normal confidence (0.50), "
        "moderate positions (10-15). Balanced approach.\n"
        "- BEAR (Conservative): Smaller positions (2-3%), tighter confidence (0.60-0.70), "
        "fewer positions (5-8). Protect capital.\n"
        "- CRISIS (Defensive): Tiny positions (1-2%), very tight confidence (0.70-0.80), "
        "minimal positions (2-3). Survival mode.\n\n"
        "PORTFOLIO-AWARE ADJUSTMENTS:\n"
        "- If drawdown > 2%, tighten ALL limits regardless of regime.\n"
        "- If accuracy < 40%, raise confidence thresholds (bad signals are getting through).\n"
        "- If cash < 20% of portfolio, reduce max positions and position size.\n"
        "- If any single position > 8% of portfolio, flag concentration risk.\n\n"
        "RULES:\n"
        "- Do NOT invent data. Only reference the provided metrics.\n"
        "- Do NOT do math. All metrics are pre-computed.\n"
        "- Keep reasoning to 2-3 sentences.\n"
        "- When in doubt, be MORE conservative. Capital preservation > returns."
    )

    def set_rules(
        self,
        directive: StrategicDirective | RegimeClassification,
        portfolio: PortfolioState,
        perf_summary: dict,
    ) -> tuple[RiskLimits, str]:
        """
        Set risk rules for the current cycle.
        Returns (RiskLimits, reasoning).
        """
        ctx = compute_risk_context(directive, portfolio, perf_summary)
        prompt = self._build_prompt(ctx)

        try:
            raw = self._call_llm_with_tool(self.SYSTEM_PROMPT, prompt, RISK_RULES_TOOL)
        except Exception as e:
            logger.error("cro_rule_setting_failed", error=str(e))
            return self._fallback_rules(directive), f"LLM failed, using default rules: {str(e)[:60]}"

        limits = RiskLimits(
            max_position_pct=float(raw["max_position_pct"]),
            max_daily_drawdown_pct=float(raw["max_daily_drawdown_pct"]),
            max_open_positions=int(raw["max_open_positions"]),
            min_signal_confidence=float(raw["min_signal_confidence"]),
            min_consensus_ratio=float(raw["min_consensus_ratio"]),
        )
        return limits, raw["reasoning"]

    def _fallback_rules(self, directive: StrategicDirective | RegimeClassification) -> RiskLimits:
        """Deterministic fallback rules when LLM fails."""
        regime = directive.regime
        presets = {
            MarketRegime.BULL: RiskLimits(
                max_position_pct=0.06, max_daily_drawdown_pct=0.04,
                max_open_positions=15, min_signal_confidence=0.45, min_consensus_ratio=0.40,
            ),
            MarketRegime.RANGING: RiskLimits(
                max_position_pct=0.05, max_daily_drawdown_pct=0.03,
                max_open_positions=10, min_signal_confidence=0.50, min_consensus_ratio=0.50,
            ),
            MarketRegime.BEAR: RiskLimits(
                max_position_pct=0.03, max_daily_drawdown_pct=0.02,
                max_open_positions=6, min_signal_confidence=0.60, min_consensus_ratio=0.60,
            ),
            MarketRegime.CRISIS: RiskLimits(
                max_position_pct=0.02, max_daily_drawdown_pct=0.01,
                max_open_positions=3, min_signal_confidence=0.75, min_consensus_ratio=0.67,
            ),
        }
        return presets.get(regime, RiskLimits())

    def _build_prompt(self, ctx: dict) -> str:
        prompt = (
            f"Set risk rules for this trading cycle.\n\n"
            f"=== MARKET REGIME ===\n"
            f"Regime: {ctx['regime']} (confidence: {ctx['regime_confidence']:.0%})\n"
            f"CEO Risk Multiplier: {ctx['risk_multiplier']:.1f}x\n"
            f"Suggested Posture: {ctx['suggested_posture']}\n"
        )
        if "ceo_strategy" in ctx:
            prompt += f"CEO Strategy: {ctx['ceo_strategy']}\n"
        prompt += (
            f"\n"
            f"=== PORTFOLIO STATE ===\n"
            f"Total Value: ${ctx['total_value']:,.2f}\n"
            f"Cash: ${ctx['cash']:,.2f} ({ctx['cash_pct']}%)\n"
            f"Open Positions: {ctx['open_positions']}\n"
            f"Drawdown: {ctx['drawdown_pct']}% — {ctx['drawdown_status']}\n"
            f"Realized P&L: ${ctx['realized_pnl']:+,.2f}\n"
            f"Unrealized P&L: ${ctx['unrealized_pnl']:+,.2f}\n"
        )

        if ctx["top_positions"]:
            prompt += f"\nTop Position Weights:\n"
            for sym, w in ctx["top_positions"]:
                prompt += f"  {sym}: {w}%\n"
            prompt += f"Max Single Position: {ctx['max_position_weight']}%\n"

        prompt += (
            f"\n=== PERFORMANCE ===\n"
            f"Total Signals Tracked: {ctx['total_signals_tracked']}\n"
            f"Accuracy: {ctx['accuracy']}%\n"
            f"Pending Evaluation: {ctx['pending_signals']}\n\n"
            f"Set the risk parameters for this cycle."
        )
        return prompt
