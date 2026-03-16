"""
Stock CEO Agent — Strategic Leadership for equities.

SPY-based regime, GICS sectors, VIX fear gauge, hot sectors.
Same two-pass architecture: PRE-CYCLE directive + POST-CYCLE review.
"""

from __future__ import annotations

from typing import Any

import structlog

from syndicate.agents.base import BaseLLMCaller
from syndicate.config import LLMProvider
from syndicate.data.models import MarketRegime, StrategicDirective, TechnicalIndicators

logger = structlog.get_logger()

# Reuse the same tool schemas from crypto CEO
STRATEGIC_DIRECTIVE_TOOL = {
    "name": "issue_directive",
    "description": "Issue the strategic directive for this stock trading cycle.",
    "input_schema": {
        "type": "object",
        "properties": {
            "regime": {
                "type": "string",
                "enum": ["bull", "bear", "ranging", "crisis"],
            },
            "regime_confidence": {
                "type": "number", "minimum": 0.0, "maximum": 1.0,
            },
            "risk_multiplier": {
                "type": "number", "minimum": 0.1, "maximum": 2.0,
            },
            "sector_weights": {
                "type": "object",
                "description": "Relative weights per GICS sector. 1.0=neutral, >1=overweight. Sectors: Technology, Health Care, Financials, Consumer Discretionary, Communication Services, Industrials, Consumer Staples, Energy, Utilities, Real Estate, Materials.",
            },
            "focus_strategy": {
                "type": "string",
                "description": "One sentence: what types of stocks to hunt this cycle.",
            },
            "emergency_halt": {"type": "boolean"},
            "halt_reason": {"type": "string"},
            "reasoning": {"type": "string"},
        },
        "required": ["regime", "regime_confidence", "risk_multiplier", "sector_weights", "focus_strategy", "emergency_halt", "reasoning"],
    },
}

CEO_REVIEW_TOOL = {
    "name": "ceo_review",
    "description": "Review cycle results and issue feedback for the next cycle.",
    "input_schema": {
        "type": "object",
        "properties": {
            "team_actions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "team": {"type": "string"},
                        "action": {
                            "type": "string",
                            "enum": ["INCREASE_CAPITAL", "MAINTAIN", "REDUCE_CAPITAL", "FIRE", "PROBATION"],
                        },
                        "new_weight": {"type": "number", "minimum": 0.0, "maximum": 2.0},
                        "reason": {"type": "string"},
                    },
                    "required": ["team", "action", "new_weight", "reason"],
                },
            },
            "strategy_adjustment": {"type": "string"},
            "regime_still_valid": {"type": "boolean"},
            "override_action": {
                "type": "string",
                "enum": ["NONE", "CLOSE_ALL_POSITIONS", "REDUCE_EXPOSURE_50", "HALT_NEXT_CYCLE"],
            },
            "override_reason": {"type": "string"},
            "assessment": {"type": "string"},
        },
        "required": ["team_actions", "strategy_adjustment", "regime_still_valid", "override_action", "assessment"],
    },
}


class StockCEOAgent(BaseLLMCaller):
    """Stock CEO agent — strategic leadership for equities."""

    PRE_CYCLE_PROMPT = (
        "You are the CEO of a quantitative STOCK hedge fund.\n\n"
        "Your job is to classify the market regime and set the strategic envelope.\n\n"
        "REGIME CLASSIFICATION (SPY-based):\n"
        "- BULL: SPY above SMA200, RSI > 50, VIX < 20\n"
        "- BEAR: SPY below SMA200, RSI < 50, VIX > 25\n"
        "- RANGING: SPY crossing SMA200, VIX 18-28\n"
        "- CRISIS: VIX > 35, SPY down >5% weekly\n\n"
        "GICS SECTOR WEIGHTS:\n"
        "- Technology: Sensitive to rates. Overweight when rates falling.\n"
        "- Financials: Benefit from rising rates. Overweight in rate-hike cycles.\n"
        "- Energy: Follow oil prices. Overweight when oil rising.\n"
        "- Health Care: Defensive. Overweight in bear/crisis.\n"
        "- Consumer Staples: Defensive. Overweight in bear/crisis.\n"
        "- Utilities: Bond proxies. Overweight when rates falling.\n"
        "- Consumer Discretionary: Cyclical. Overweight in early bull.\n"
        "- Industrials: Cyclical. Overweight in expansion.\n\n"
        "RULES:\n"
        "- Reference provided data only.\n"
        "- Focus strategy: ONE actionable sentence.\n"
        "- Emergency halt for EXTREME events only (VIX > 50, circuit breakers).\n"
    )

    POST_CYCLE_PROMPT = (
        "You are the Stock CEO reviewing this cycle's results.\n\n"
        "You see all team signals, trades, P&L, and team track records.\n\n"
        "YOUR JOB:\n"
        "1. EVALUATE EACH TEAM (6 teams: technical, sentiment, fundamental, macro, institutional, news)\n"
        "2. ADJUST STRATEGY for next cycle\n"
        "3. VALIDATE REGIME call\n"
        "4. STRUCTURAL OVERRIDE if needed\n\n"
        "RULES:\n"
        "- Review EVERY team. Teams: technical, sentiment, fundamental, macro, institutional, news.\n"
        "- With < 20 signals, default to MAINTAIN.\n"
        "- Don't fire teams in first few cycles.\n"
    )

    def direct(
        self,
        spy_indicators: TechnicalIndicators,
        intel: dict,
        portfolio_summary: dict,
        perf_summary: dict,
        last_feedback: dict | None = None,
        experience_summary: str = "",
    ) -> StrategicDirective:
        """PRE-CYCLE: Issue strategic directive."""
        ctx = self._compute_strategic_context(
            spy_indicators, intel, portfolio_summary, perf_summary, last_feedback,
        )
        if experience_summary:
            ctx["experience_summary"] = experience_summary
        prompt = self._build_pre_prompt(ctx)

        try:
            raw = self._call_llm_with_tool(self.PRE_CYCLE_PROMPT, prompt, STRATEGIC_DIRECTIVE_TOOL)
        except Exception as e:
            logger.error("stock_ceo_directive_failed", error=str(e))
            return StrategicDirective(
                regime=MarketRegime.RANGING, regime_confidence=0.5, risk_multiplier=1.0,
                sector_weights={"Technology": 1.0, "Health Care": 1.0, "Financials": 1.0},
                focus_strategy="Balanced approach — CEO directive failed.",
                reasoning=f"Fallback: {str(e)[:60]}",
            )

        return StrategicDirective(
            regime=MarketRegime(raw["regime"]),
            regime_confidence=float(raw["regime_confidence"]),
            risk_multiplier=float(raw["risk_multiplier"]),
            sector_weights=raw.get("sector_weights", {}),
            focus_strategy=raw.get("focus_strategy", ""),
            emergency_halt=raw.get("emergency_halt", False),
            halt_reason=raw.get("halt_reason", ""),
            reasoning=raw.get("reasoning", ""),
        )

    def review(
        self,
        directive: StrategicDirective,
        all_signals: list,
        aggregated_signals: list,
        orders_executed: int,
        portfolio_summary: dict,
        team_stats: dict,
        perf_summary: dict,
    ) -> dict:
        """POST-CYCLE: Review results."""
        ctx = self._compute_review_context(
            directive, all_signals, aggregated_signals,
            orders_executed, portfolio_summary, team_stats, perf_summary,
        )
        prompt = self._build_post_prompt(ctx)

        try:
            return self._call_llm_with_tool(self.POST_CYCLE_PROMPT, prompt, CEO_REVIEW_TOOL)
        except Exception as e:
            logger.error("stock_ceo_review_failed", error=str(e))
            return {
                "team_actions": [],
                "strategy_adjustment": "",
                "regime_still_valid": True,
                "override_action": "NONE",
                "assessment": f"Review failed: {str(e)[:80]}",
            }

    def _compute_strategic_context(
        self, spy_indicators, intel, portfolio_summary, perf_summary, last_feedback,
    ) -> dict[str, Any]:
        ctx: dict[str, Any] = {}
        indices = intel.get("indices")
        if indices:
            ctx["spy_price"] = indices.spy_price or 0
            ctx["spy_change"] = indices.spy_change_pct or 0
            ctx["vix"] = indices.vix or 0
            ctx["qqq_change"] = indices.qqq_change_pct or 0
            if indices.treasury_10y:
                ctx["treasury_10y"] = indices.treasury_10y
            if indices.yield_curve_spread is not None:
                ctx["yield_curve"] = indices.yield_curve_spread

        if spy_indicators:
            if spy_indicators.sma_200:
                spy_price = ctx.get("spy_price", 0)
                if spy_price > 0:
                    ctx["spy_vs_200sma"] = f"{((spy_price - spy_indicators.sma_200) / spy_indicators.sma_200) * 100:+.1f}%"
            if spy_indicators.rsi_14:
                ctx["spy_rsi"] = round(spy_indicators.rsi_14, 1)

        fg = intel.get("cnn_fear_greed", {})
        if fg:
            ctx["cnn_fg"] = fg.get("current_value", 50)
            ctx["cnn_fg_label"] = fg.get("current_label", "?")

        sector_perf = intel.get("sector_performance")
        if sector_perf and sector_perf.hot_sectors:
            ctx["hot_sectors"] = sector_perf.hot_sectors
        if sector_perf and sector_perf.cold_sectors:
            ctx["cold_sectors"] = sector_perf.cold_sectors

        reddit = intel.get("reddit_sentiment")
        if reddit:
            ctx["reddit_sentiment"] = f"{reddit.get('sentiment_ratio', 0.5):.0%} bullish"

        ctx["portfolio_value"] = portfolio_summary.get("total_value", 100_000)
        ctx["portfolio_return"] = portfolio_summary.get("return_pct", 0)
        ctx["open_positions"] = portfolio_summary.get("open_positions", 0)
        ctx["drawdown"] = portfolio_summary.get("drawdown_pct", 0)
        ctx["accuracy"] = round(perf_summary.get("accuracy", 0) * 100, 1)

        if last_feedback:
            ctx["last_strategy_adjustment"] = last_feedback.get("strategy_adjustment", "")
            ctx["last_assessment"] = last_feedback.get("assessment", "")

        return ctx

    def _compute_review_context(
        self, directive, all_signals, aggregated_signals,
        orders_executed, portfolio_summary, team_stats, perf_summary,
    ) -> dict[str, Any]:
        ctx: dict[str, Any] = {}
        ctx["directed_regime"] = directive.regime.value.upper()
        ctx["directed_strategy"] = directive.focus_strategy
        ctx["total_signals"] = len(all_signals)
        ctx["stocks_analyzed"] = len(set(s.symbol for s in all_signals))
        ctx["orders_executed"] = orders_executed
        ctx["aggregated_verdicts"] = [
            {"symbol": a.symbol, "action": a.recommended_action.value,
             "confidence": round(a.aggregated_confidence, 2), "consensus": round(a.consensus_ratio, 2)}
            for a in aggregated_signals
        ]
        ctx["portfolio_value"] = portfolio_summary.get("total_value", 0)
        ctx["portfolio_return"] = portfolio_summary.get("return_pct", 0)
        ctx["drawdown"] = portfolio_summary.get("drawdown_pct", 0)
        ctx["team_stats"] = {
            team: {
                "total": stats.get("total", 0),
                "accuracy": round(stats.get("accuracy", 0) * 100, 1),
            }
            for team, stats in team_stats.items()
        }
        ctx["overall_accuracy"] = round(perf_summary.get("accuracy", 0) * 100, 1)
        return ctx

    def _build_pre_prompt(self, ctx: dict) -> str:
        prompt = "Issue your strategic directive for this stock trading cycle.\n\n"
        prompt += f"=== SPY ===\n"
        prompt += f"Price: ${ctx.get('spy_price', 0):,.2f} | Change: {ctx.get('spy_change', 0):+.2f}%\n"
        if "spy_vs_200sma" in ctx:
            prompt += f"vs SMA200: {ctx['spy_vs_200sma']}\n"
        if "spy_rsi" in ctx:
            prompt += f"RSI: {ctx['spy_rsi']}\n"
        if "vix" in ctx:
            prompt += f"VIX: {ctx['vix']:.1f}\n"

        prompt += "\n=== INTELLIGENCE ===\n"
        if "cnn_fg" in ctx:
            prompt += f"CNN Fear & Greed: {ctx['cnn_fg']}/100 ({ctx.get('cnn_fg_label', '?')})\n"
        if "treasury_10y" in ctx:
            prompt += f"10Y Treasury: {ctx['treasury_10y']:.2f}%\n"
        if "yield_curve" in ctx:
            prompt += f"Yield Curve: {ctx['yield_curve']:+.2f}%\n"
        if "hot_sectors" in ctx:
            prompt += f"Hot Sectors: {', '.join(ctx['hot_sectors'])}\n"
        if "cold_sectors" in ctx:
            prompt += f"Cold Sectors: {', '.join(ctx['cold_sectors'])}\n"
        if "reddit_sentiment" in ctx:
            prompt += f"Reddit: {ctx['reddit_sentiment']}\n"

        prompt += f"\n=== PORTFOLIO ===\n"
        prompt += f"Value: ${ctx['portfolio_value']:,.2f} | Return: {ctx['portfolio_return']:+.2f}%\n"
        prompt += f"Positions: {ctx['open_positions']} | Drawdown: {ctx['drawdown']:.2f}%\n"
        prompt += f"Accuracy: {ctx['accuracy']}%\n"

        if ctx.get("last_strategy_adjustment"):
            prompt += f"\n=== LAST CYCLE FEEDBACK ===\n{ctx['last_strategy_adjustment']}\n"

        if ctx.get("experience_summary"):
            prompt += f"\n=== EXPERIENCE ===\n{ctx['experience_summary']}\n"

        prompt += "\nIssue your directive."
        return prompt

    def _build_post_prompt(self, ctx: dict) -> str:
        prompt = f"Review this cycle's results.\n\n"
        prompt += f"=== DIRECTIVE ===\nRegime: {ctx['directed_regime']} | Strategy: {ctx['directed_strategy']}\n"
        prompt += f"\n=== RESULTS ===\n"
        prompt += f"Stocks: {ctx['stocks_analyzed']} | Signals: {ctx['total_signals']} | Orders: {ctx['orders_executed']}\n"
        prompt += f"Portfolio: ${ctx['portfolio_value']:,.2f} | Return: {ctx['portfolio_return']:+.2f}%\n"

        prompt += f"\n=== VERDICTS ===\n"
        for v in ctx["aggregated_verdicts"]:
            prompt += f"  {v['symbol']}: {v['action']} (conf {v['confidence']:.0%}, consensus {v['consensus']:.0%})\n"

        prompt += f"\n=== TEAM PERFORMANCE ===\n"
        for team, stats in ctx["team_stats"].items():
            prompt += f"  {team}: {stats['accuracy']}% ({stats['total']} signals)\n"

        prompt += "\nReview each team. Set capital allocation."
        return prompt
