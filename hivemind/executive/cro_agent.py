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
        "Your job: SET risk parameters for this cycle. Risk Manager ENFORCES them.\n\n"
        "DATA-BACKED PARAMETERS BY REGIME (from empirical research):\n\n"
        "BULL:\n"
        "  max_position_pct: 0.07-0.10 (7-10%)\n"
        "  max_daily_drawdown_pct: 0.08-0.10 (8-10%, Millennium standard)\n"
        "  max_open_positions: 10-15\n"
        "  min_signal_confidence: 0.45-0.50 (aggressive, momentum works)\n"
        "  min_consensus_ratio: 0.50-0.60 (lower bar, more trades)\n\n"
        "RANGING:\n"
        "  max_position_pct: 0.05-0.07\n"
        "  max_daily_drawdown_pct: 0.05-0.07\n"
        "  max_open_positions: 8-12\n"
        "  min_signal_confidence: 0.50-0.55\n"
        "  min_consensus_ratio: 0.55-0.65\n\n"
        "BEAR:\n"
        "  max_position_pct: 0.03-0.05\n"
        "  max_daily_drawdown_pct: 0.05-0.07 (NOT 2% — too restrictive per research)\n"
        "  max_open_positions: 5-8\n"
        "  min_signal_confidence: 0.50-0.55 (NOT 0.60+ — kills contrarian signals)\n"
        "  min_consensus_ratio: 0.55-0.65 (NOT 0.80 — blocks legitimate disagreement)\n"
        "  NOTE: F&G < 15 = historically 85% win rate buy signal. Do NOT block contrarian trades.\n\n"
        "CRISIS:\n"
        "  max_position_pct: 0.02-0.03\n"
        "  max_daily_drawdown_pct: 0.05\n"
        "  max_open_positions: 3-5\n"
        "  min_signal_confidence: 0.55-0.65\n"
        "  min_consensus_ratio: 0.65-0.75\n"
        "  NOTE: Even in crisis, F&G < 10 has ALWAYS preceded major rallies (COVID: +1,500% 12mo).\n\n"
        "PORTFOLIO-AWARE ADJUSTMENTS:\n"
        "- If drawdown > 5%, tighten position sizes by 50%.\n"
        "- If accuracy < 40% over 20+ trades, raise confidence by 0.05.\n"
        "- If cash < 20%, reduce max positions by 2.\n\n"
        "CRITICAL: Do NOT set consensus above 0.70 in ANY regime. Research shows 60% consensus\n"
        "is the optimal minimum — higher blocks too many valid trades where teams legitimately disagree.\n\n"
        "RULES: Reference provided metrics. 2-3 sentences reasoning."
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

        # Hard caps — clamp LLM outputs to research-backed maximums.
        # The LLM consistently outputs overly conservative thresholds despite
        # prompt guidance. These mechanical caps cannot be overridden.
        regime = directive.regime if hasattr(directive, 'regime') else MarketRegime.RANGING
        limits = self._apply_hard_caps(limits, regime)

        return limits, raw["reasoning"]

    @staticmethod
    def _apply_hard_caps(limits: RiskLimits, regime: MarketRegime) -> RiskLimits:
        """
        Apply hard caps AFTER the LLM returns its values.

        Research-backed maximums per regime — the LLM cannot exceed these.
        This fixes the core problem: LLM consistently sets thresholds too high,
        killing 98.5% of signals before they reach execution.
        """
        caps = {
            MarketRegime.BULL:    {"min_signal_confidence": 0.55, "min_consensus_ratio": 0.55},
            MarketRegime.RANGING: {"min_signal_confidence": 0.55, "min_consensus_ratio": 0.60},
            MarketRegime.BEAR:    {"min_signal_confidence": 0.55, "min_consensus_ratio": 0.60},
            MarketRegime.CRISIS:  {"min_signal_confidence": 0.60, "min_consensus_ratio": 0.65},
        }
        regime_caps = caps.get(regime, caps[MarketRegime.RANGING])

        capped = False
        if limits.min_signal_confidence > regime_caps["min_signal_confidence"]:
            logger.warning(
                "cro_cap_applied",
                field="min_signal_confidence",
                llm_value=limits.min_signal_confidence,
                capped_to=regime_caps["min_signal_confidence"],
                regime=regime.value,
            )
            limits.min_signal_confidence = regime_caps["min_signal_confidence"]
            capped = True

        if limits.min_consensus_ratio > regime_caps["min_consensus_ratio"]:
            logger.warning(
                "cro_cap_applied",
                field="min_consensus_ratio",
                llm_value=limits.min_consensus_ratio,
                capped_to=regime_caps["min_consensus_ratio"],
                regime=regime.value,
            )
            limits.min_consensus_ratio = regime_caps["min_consensus_ratio"]
            capped = True

        if capped:
            logger.info("cro_hard_caps_enforced", regime=regime.value)

        return limits

    def _fallback_rules(self, directive: StrategicDirective | RegimeClassification) -> RiskLimits:
        """Deterministic fallback rules when LLM fails."""
        regime = directive.regime
        # Data-backed fallback parameters (from research/risk_parameters.md)
        presets = {
            MarketRegime.BULL: RiskLimits(
                max_position_pct=0.08, max_daily_drawdown_pct=0.08,
                max_open_positions=12, min_signal_confidence=0.45, min_consensus_ratio=0.50,
            ),
            MarketRegime.RANGING: RiskLimits(
                max_position_pct=0.06, max_daily_drawdown_pct=0.06,
                max_open_positions=10, min_signal_confidence=0.50, min_consensus_ratio=0.55,
            ),
            MarketRegime.BEAR: RiskLimits(
                max_position_pct=0.04, max_daily_drawdown_pct=0.05,
                max_open_positions=7, min_signal_confidence=0.50, min_consensus_ratio=0.55,
            ),
            MarketRegime.CRISIS: RiskLimits(
                max_position_pct=0.03, max_daily_drawdown_pct=0.05,
                max_open_positions=4, min_signal_confidence=0.55, min_consensus_ratio=0.65,
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
            f"=== RESEARCH-BACKED CONSTRAINTS ===\n"
            f"NEVER set min_consensus_ratio above 0.65 — research shows this blocks valid trades.\n"
            f"In BEAR with F&G < 15: contrarian buy signal wins 85% of the time historically.\n"
            f"Bear market drawdown halt: 5-7%, not 2% (too tight, causes premature exit).\n"
            f"Confidence 0.50 in bear still yields 76% accuracy per MDPI study.\n\n"
            f"Set the risk parameters for this cycle."
        )
        return prompt
