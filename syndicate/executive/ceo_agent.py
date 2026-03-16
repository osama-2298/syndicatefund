"""
CEO Agent — Strategic Leadership.

Equipped with deep crypto market knowledge (2012-2026) and cycle-to-cycle memory.
Modeled after real hedge fund CEOs (Griffin/Citadel, Simons/RenTech, Dalio/Bridgewater):

The CEO is NOT an operator. The CEO is an allocator, constraint-setter,
talent-evaluator, and exception-handler.

The CEO appears TWICE in the pipeline:

  PRE-CYCLE (open):
    - Sees: intelligence data, portfolio state, last cycle's feedback
    - Sets: regime, risk envelope, sector allocation, strategic focus
    - Can: issue emergency halt

  POST-CYCLE (close):
    - Sees: all aggregated signals, trade decisions, P&L, team performance
    - Does: evaluate teams (fire/promote/reallocate capital)
    - Does: set strategic feedback that persists to the NEXT cycle
    - Can: override structural decisions (pull capital, change limits)

"Capital allocation IS the feedback mechanism" — Citadel model.
"""

from __future__ import annotations

from typing import Any

import structlog

from pathlib import Path

from syndicate.agents.base import BaseLLMCaller
from syndicate.config import LLMProvider
from syndicate.data.models import MarketRegime, StrategicDirective, TechnicalIndicators

logger = structlog.get_logger()

# Load the CEO's knowledge base — multiple layers of expertise
_KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
_KNOWLEDGE_BASE_PATH = Path(__file__).parent / "ceo_knowledge_base.md"


def _load_knowledge_base() -> str:
    """
    Load ALL layers of CEO institutional knowledge.
    Extracts the most decision-relevant content from each layer.
    """
    sections = []

    # ── Layer 1: Market cycles and playbook (original knowledge base) ──
    if _KNOWLEDGE_BASE_PATH.exists():
        full_text = _KNOWLEDGE_BASE_PATH.read_text()

        # Key lessons (compact)
        lessons = []
        for line in full_text.split("\n"):
            if line.startswith("**Key Lesson:**"):
                lessons.append(line.replace("**Key Lesson:**", "").strip())
        if lessons:
            sections.append("LESSONS FROM CRYPTO HISTORY:\n" + "\n".join(f"- {l}" for l in lessons))

        # Halving table
        if "## Halving Date Reference Table" in full_text and "## Price Performance" in full_text:
            start = full_text.index("## Halving Date Reference Table")
            end = full_text.index("## Price Performance Around Halvings")
            sections.append(full_text[start:end].strip())

        # F&G history (compact)
        if "SECTION 3: FEAR & GREED INDEX" in full_text:
            start = full_text.index("SECTION 3: FEAR & GREED INDEX")
            end_marker = "SECTION 4:"
            end = full_text.index(end_marker) if end_marker in full_text else start + 3000
            chunk = full_text[start:end].strip()
            sections.append(chunk[:1500] + "\n..." if len(chunk) > 1500 else chunk)

        # BTC Dominance patterns
        if "SECTION 4: BTC DOMINANCE" in full_text:
            start = full_text.index("SECTION 4: BTC DOMINANCE")
            end_marker = "SECTION 5:"
            end = full_text.index(end_marker) if end_marker in full_text else start + 2000
            chunk = full_text[start:end].strip()
            sections.append(chunk[:1200] + "\n..." if len(chunk) > 1200 else chunk)

        # Operational Playbook
        if "SECTION 9: OPERATIONAL PLAYBOOK" in full_text:
            start = full_text.index("SECTION 9: OPERATIONAL PLAYBOOK")
            sections.append(full_text[start:].strip())

    # ── Layers 2-6: Knowledge directory files ──
    if _KNOWLEDGE_DIR.exists():
        knowledge_files = sorted(_KNOWLEDGE_DIR.glob("*.md"))

        for kf in knowledge_files:
            try:
                content = kf.read_text()
                # Extract the most actionable content — look for rules, patterns, guidelines
                # Strategy: take headers + any line starting with - or * or numbered (the rules)
                extracted = []
                filename = kf.stem.replace("_", " ").title()
                extracted.append(f"\n--- {filename.upper()} ---")

                lines = content.split("\n")
                in_relevant = False
                chars_added = 0
                max_chars = 4000  # Cap per file to keep total manageable

                for line in lines:
                    stripped = line.strip()
                    # Always include headers
                    if stripped.startswith("#"):
                        extracted.append(stripped)
                        in_relevant = True
                        continue
                    # Include rule/pattern lines
                    if stripped.startswith(("- ", "* ", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")):
                        if chars_added < max_chars:
                            extracted.append(stripped)
                            chars_added += len(stripped)
                    # Include bold key points
                    elif stripped.startswith("**") and stripped.endswith("**"):
                        if chars_added < max_chars:
                            extracted.append(stripped)
                            chars_added += len(stripped)

                if len(extracted) > 1:  # More than just the header
                    sections.append("\n".join(extracted))
            except Exception:
                continue

    return "\n\n".join(sections)


_CEO_KNOWLEDGE = _load_knowledge_base()

# ═══════════════════════════════════════
#  PRE-CYCLE: Strategic Directive
# ═══════════════════════════════════════

STRATEGIC_DIRECTIVE_TOOL = {
    "name": "issue_directive",
    "description": "Issue the strategic directive for this trading cycle.",
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
                "description": "BULL: 1.1-1.3. RANGING: 0.8-1.0. BEAR: 0.5-0.7. CRISIS: 0.2-0.4.",
            },
            "sector_weights": {
                "type": "object",
                "description": "Relative weights per sector. 1.0=neutral, >1=overweight, <1=underweight, 0=avoid. Sectors: L1s, DeFi, L2s, Memes, AI, Infra.",
            },
            "focus_strategy": {
                "type": "string",
                "description": "One sentence: what types of coins to hunt this cycle.",
            },
            "emergency_halt": {
                "type": "boolean",
                "description": "True ONLY for black swan events.",
            },
            "halt_reason": {"type": "string"},
            "reasoning": {
                "type": "string",
                "description": "3-4 sentences: strategic thesis for this cycle.",
            },
        },
        "required": ["regime", "regime_confidence", "risk_multiplier", "sector_weights", "focus_strategy", "emergency_halt", "reasoning"],
    },
}

# ═══════════════════════════════════════
#  POST-CYCLE: Review & Feedback
# ═══════════════════════════════════════

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
                            "description": "Capital allocation decision for this team.",
                        },
                        "new_weight": {
                            "type": "number", "minimum": 0.0, "maximum": 2.0,
                            "description": "New weight multiplier in signal aggregator. 1.0=normal, 0=fired.",
                        },
                        "reason": {"type": "string"},
                    },
                    "required": ["team", "action", "new_weight", "reason"],
                },
            },
            "strategy_adjustment": {
                "type": "string",
                "description": "What to change in the strategy for NEXT cycle. Empty if no change.",
            },
            "regime_still_valid": {
                "type": "boolean",
                "description": "Is the pre-cycle regime assessment still correct based on results?",
            },
            "override_action": {
                "type": "string",
                "enum": ["NONE", "CLOSE_ALL_POSITIONS", "REDUCE_EXPOSURE_50", "HALT_NEXT_CYCLE"],
                "description": "Structural override. NONE for normal operation.",
            },
            "override_reason": {"type": "string"},
            "assessment": {
                "type": "string",
                "description": "3-4 sentences: how did the cycle go, what did we learn, what changes.",
            },
        },
        "required": ["team_actions", "strategy_adjustment", "regime_still_valid", "override_action", "assessment"],
    },
}


def compute_strategic_context(
    btc_indicators: TechnicalIndicators,
    btc_stats_24h: dict,
    intel: dict,
    portfolio_summary: dict,
    perf_summary: dict,
    last_feedback: dict | None = None,
) -> dict[str, Any]:
    """Pre-compute the full strategic picture for the CEO pre-cycle directive."""
    ctx: dict[str, Any] = {}
    current_price = float(btc_stats_24h.get("close", 0))
    change_24h = float(btc_stats_24h.get("price_change_pct", 0))

    # BTC
    ctx["btc_price"] = current_price
    ctx["btc_change_24h"] = round(change_24h, 2)
    if btc_indicators.sma_20 and btc_indicators.sma_50 and btc_indicators.sma_200:
        if btc_indicators.sma_20 > btc_indicators.sma_50 > btc_indicators.sma_200:
            ctx["btc_trend"] = "BULLISH — MAs aligned upward"
        elif btc_indicators.sma_20 < btc_indicators.sma_50 < btc_indicators.sma_200:
            ctx["btc_trend"] = "BEARISH — MAs aligned downward"
        else:
            ctx["btc_trend"] = "MIXED — MAs transitioning"
    if btc_indicators.sma_200 and current_price:
        ctx["btc_vs_200sma"] = f"{((current_price - btc_indicators.sma_200) / btc_indicators.sma_200) * 100:+.1f}%"
    if btc_indicators.rsi_14:
        ctx["btc_rsi"] = round(btc_indicators.rsi_14, 1)

    # ── Algorithmic regime suggestion (quantitative, not subjective) ──
    # CEO can override but must justify departure
    bull_score = 0
    bear_score = 0
    # Factor 1: Price vs SMA200
    if btc_indicators.sma_200 and current_price:
        pct_above = ((current_price - btc_indicators.sma_200) / btc_indicators.sma_200) * 100
        if pct_above > 5:
            bull_score += 2
        elif pct_above > 0:
            bull_score += 1
        elif pct_above > -5:
            bear_score += 1
        else:
            bear_score += 2
    # Factor 2: RSI
    if btc_indicators.rsi_14:
        if btc_indicators.rsi_14 > 55:
            bull_score += 1
        elif btc_indicators.rsi_14 < 45:
            bear_score += 1
    # Factor 3: MA alignment
    if btc_indicators.sma_20 and btc_indicators.sma_50 and btc_indicators.sma_200:
        if btc_indicators.sma_20 > btc_indicators.sma_50 > btc_indicators.sma_200:
            bull_score += 2
        elif btc_indicators.sma_20 < btc_indicators.sma_50 < btc_indicators.sma_200:
            bear_score += 2
    # Factor 4: Fear & Greed
    fg_val = intel.get("fear_greed", {}).get("current_value", 50)
    if fg_val > 60:
        bull_score += 1
    elif fg_val < 25:
        bear_score += 1
        if fg_val < 10:
            bear_score += 1  # Extreme fear
    # Factor 5: 24h change
    if change_24h > 3:
        bull_score += 1
    elif change_24h < -5:
        bear_score += 1
        if change_24h < -10:
            bear_score += 1  # Potential crisis

    # Classify
    if bear_score >= 5 and fg_val < 15:
        algo_regime = "CRISIS"
    elif bull_score >= 4 and bull_score > bear_score + 1:
        algo_regime = "BULL"
    elif bear_score >= 4 and bear_score > bull_score + 1:
        algo_regime = "BEAR"
    else:
        algo_regime = "RANGING"

    ctx["algo_regime"] = algo_regime
    ctx["algo_bull_score"] = bull_score
    ctx["algo_bear_score"] = bear_score

    # Intelligence
    fg = intel.get("fear_greed")
    if fg:
        ctx["fear_greed"] = fg["current_value"]
        ctx["fear_greed_label"] = fg["current_label"]
    reddit = intel.get("reddit_sentiment")
    if reddit:
        ctx["reddit_sentiment"] = f"{reddit.get('sentiment_ratio', 0.5):.0%} bullish"
        ctx["reddit_engagement"] = reddit.get("engagement_level", "?")
    gm = intel.get("global_market")
    if gm:
        ctx["btc_dominance"] = gm.get("btc_dominance", 0)
        ctx["market_cap_change_24h"] = gm.get("market_cap_change_24h_pct", 0)
    trending = intel.get("trending")
    if trending:
        ctx["trending_coins"] = ", ".join(t.get("symbol", "?") for t in trending[:7])
    ds = intel.get("defi_summary")
    if ds:
        ctx["total_defi_tvl"] = ds.get("total_tvl", 0)

    # Portfolio
    ctx["portfolio_value"] = portfolio_summary.get("total_value", 100_000)
    ctx["portfolio_return"] = portfolio_summary.get("return_pct", 0)
    ctx["open_positions"] = portfolio_summary.get("open_positions", 0)
    ctx["drawdown"] = portfolio_summary.get("drawdown_pct", 0)

    # Performance
    ctx["total_signals"] = perf_summary.get("total_signals", 0)
    ctx["accuracy"] = round(perf_summary.get("accuracy", 0) * 100, 1)

    # Last cycle feedback (if any)
    if last_feedback:
        ctx["last_strategy_adjustment"] = last_feedback.get("strategy_adjustment", "")
        ctx["last_assessment"] = last_feedback.get("assessment", "")
        ctx["last_regime_called"] = last_feedback.get("regime_called", "")
        ctx["last_regime_was_valid"] = last_feedback.get("regime_was_valid", True)
        ctx["last_portfolio_return"] = last_feedback.get("portfolio_return", 0)

    return ctx


def compute_review_context(
    directive: StrategicDirective,
    all_signals: list,
    aggregated_signals: list,
    orders_executed: int,
    portfolio_summary: dict,
    team_stats: dict,
    perf_summary: dict,
) -> dict[str, Any]:
    """Pre-compute the post-cycle review context for the CEO."""
    ctx: dict[str, Any] = {}

    # What the CEO directed
    ctx["directed_regime"] = directive.regime.value.upper()
    ctx["directed_strategy"] = directive.focus_strategy
    ctx["directed_sector_weights"] = directive.sector_weights

    # What happened
    ctx["total_signals"] = len(all_signals)
    ctx["coins_analyzed"] = len(set(s.symbol for s in all_signals))
    ctx["orders_executed"] = orders_executed

    # Aggregated results
    ctx["aggregated_verdicts"] = []
    for agg in aggregated_signals:
        ctx["aggregated_verdicts"].append({
            "symbol": agg.symbol,
            "action": agg.recommended_action.value,
            "confidence": round(agg.aggregated_confidence, 2),
            "consensus": round(agg.consensus_ratio, 2),
        })

    # Portfolio outcome
    ctx["portfolio_value"] = portfolio_summary.get("total_value", 0)
    ctx["portfolio_return"] = portfolio_summary.get("return_pct", 0)
    ctx["drawdown"] = portfolio_summary.get("drawdown_pct", 0)

    # Team performance
    ctx["team_stats"] = {}
    for team_name, stats in team_stats.items():
        ctx["team_stats"][team_name] = {
            "total": stats.get("total", 0),
            "accuracy": round(stats.get("accuracy", 0) * 100, 1),
            "status": (
                "UNDERPERFORMING" if stats.get("accuracy", 0) < 0.3 and stats.get("total", 0) >= 20 else
                "STRONG" if stats.get("accuracy", 0) > 0.65 and stats.get("total", 0) >= 20 else
                "CALIBRATING" if stats.get("total", 0) < 10 else
                "ADEQUATE"
            ),
        }

    # Overall
    ctx["overall_accuracy"] = round(perf_summary.get("accuracy", 0) * 100, 1)

    return ctx


class CEOAgent(BaseLLMCaller):
    """CEO agent — strategic leadership, appears at both ends of the pipeline."""

    PRE_CYCLE_PROMPT = (
        "You are the CEO of a quantitative crypto hedge fund.\n\n"
        "Like Ken Griffin at Citadel, you DO NOT make trades. You set the strategic envelope "
        "within which the entire organization operates. Your primary levers:\n"
        "1. REGIME CLASSIFICATION — Bull, Bear, Ranging, Crisis\n"
        "2. SECTOR ALLOCATION — Where should capital flow (weights per sector)\n"
        "3. STRATEGIC FOCUS — One directive for your COO on what to hunt\n"
        "4. EMERGENCY HALT — Only for genuine black swan events\n\n"
        "SECTOR WEIGHT GUIDELINES:\n"
        "- L1s: Backbone. Overweight in bull (1.2-1.5), hold in bear (0.8).\n"
        "- DeFi: Follow TVL. Growing TVL = overweight (1.3-1.5).\n"
        "- L2s: High beta to ETH. Overweight when ETH is strong.\n"
        "- Memes: HIGH RISK. Only in bull (0.5-0.8). Zero in bear/crisis.\n"
        "- AI: Narrative-driven. Overweight when trending.\n\n"
        "RULES:\n"
        "- Reference provided data only. Sector weights should sum to ~5-8.\n"
        "- Focus strategy: ONE actionable sentence.\n"
        "- If you have feedback from your last cycle review, incorporate it.\n"
        "- Emergency halt for EXTREME events only.\n"
        "- Use your KNOWLEDGE BASE and EXPERIENCE to make historically-informed decisions.\n\n"
        + ("=== YOUR INSTITUTIONAL KNOWLEDGE ===\n" + _CEO_KNOWLEDGE + "\n" if _CEO_KNOWLEDGE else "")
    )

    POST_CYCLE_PROMPT = (
        "You are the CEO reviewing this cycle's results.\n\n"
        "Like Ken Griffin walking the floor at Citadel, you now see EVERYTHING: "
        "what every team recommended, what trades were executed, the P&L, and each team's track record.\n\n"
        "YOUR JOB NOW:\n"
        "1. EVALUATE EACH TEAM — Capital allocation is your feedback mechanism.\n"
        "   - INCREASE_CAPITAL (new_weight 1.2-1.5): Team is outperforming. Give them more influence.\n"
        "   - MAINTAIN (new_weight 1.0): Performing adequately.\n"
        "   - REDUCE_CAPITAL (new_weight 0.5-0.8): Underperforming. Reduce their influence.\n"
        "   - PROBATION (new_weight 0.3): On thin ice. One more bad cycle = fired.\n"
        "   - FIRE (new_weight 0.0): Remove from rotation entirely.\n\n"
        "2. ADJUST STRATEGY — What should change for the NEXT cycle?\n"
        "3. VALIDATE REGIME — Was your pre-cycle regime call correct based on results?\n"
        "4. STRUCTURAL OVERRIDE — Only if something went seriously wrong:\n"
        "   - CLOSE_ALL_POSITIONS: Liquidate everything.\n"
        "   - REDUCE_EXPOSURE_50: Cut all positions in half.\n"
        "   - HALT_NEXT_CYCLE: Don't trade next cycle.\n"
        "   - NONE: Normal operation (default).\n\n"
        "RULES:\n"
        "- Review EVERY team. Don't skip any.\n"
        "- With < 20 evaluated signals per team, default to MAINTAIN — insufficient data.\n"
        "- Don't fire teams in the first few cycles. Let them calibrate.\n"
        "- Your strategy adjustment persists to the next cycle's pre-cycle directive.\n"
        "- Assessment: 3-4 sentences on how the cycle went.\n"
        "- Use your knowledge of historical cycles and patterns to contextualize results."
    )

    def direct(
        self,
        btc_indicators: TechnicalIndicators,
        btc_stats_24h: dict,
        intel: dict,
        portfolio_summary: dict,
        perf_summary: dict,
        last_feedback: dict | None = None,
        experience_summary: str = "",
    ) -> StrategicDirective:
        """PRE-CYCLE: Issue strategic directive."""
        ctx = compute_strategic_context(
            btc_indicators, btc_stats_24h, intel, portfolio_summary, perf_summary, last_feedback,
        )
        if experience_summary:
            ctx["experience_summary"] = experience_summary
        prompt = self._build_pre_prompt(ctx)

        try:
            raw = self._call_llm_with_tool(self.PRE_CYCLE_PROMPT, prompt, STRATEGIC_DIRECTIVE_TOOL)
        except Exception as e:
            logger.error("ceo_directive_failed", error=str(e))
            return StrategicDirective(
                regime=MarketRegime.RANGING, regime_confidence=0.5, risk_multiplier=1.0,
                sector_weights={"L1s": 1.0, "DeFi": 1.0, "L2s": 1.0, "Memes": 0.5},
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

    _REVIEW_FALLBACK: dict = {
        "team_actions": [],
        "strategy_adjustment": "",
        "regime_still_valid": True,
        "override_action": "NONE",
        "override_reason": "",
        "assessment": "",
    }

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
        """POST-CYCLE: Review results and issue feedback for next cycle."""
        ctx = compute_review_context(
            directive, all_signals, aggregated_signals,
            orders_executed, portfolio_summary, team_stats, perf_summary,
        )
        prompt = self._build_post_prompt(ctx)

        try:
            raw = self._call_llm_with_tool(
                self.POST_CYCLE_PROMPT, prompt, CEO_REVIEW_TOOL,
                max_tokens=2048,
            )
        except Exception as e:
            logger.error("ceo_review_failed", error=str(e))
            return {**self._REVIEW_FALLBACK, "assessment": f"Review failed: {str(e)[:80]}"}

        # Defensive: LLM may return a string (e.g. truncated JSON) instead of a dict
        if not isinstance(raw, dict):
            logger.error("ceo_review_bad_type", raw_type=type(raw).__name__)
            return {**self._REVIEW_FALLBACK, "assessment": "Review returned non-dict response"}

        return raw

    def _build_pre_prompt(self, ctx: dict) -> str:
        prompt = "Issue your strategic directive for this trading cycle.\n\n"
        prompt += f"=== BTC ===\nPrice: ${ctx['btc_price']:,.2f} | 24h: {ctx['btc_change_24h']:+.2f}%\n"
        if "btc_trend" in ctx:
            prompt += f"Trend: {ctx['btc_trend']}\n"
        if "btc_vs_200sma" in ctx:
            prompt += f"vs SMA200: {ctx['btc_vs_200sma']}\n"
        if "btc_rsi" in ctx:
            prompt += f"RSI: {ctx['btc_rsi']}\n"

        # Algorithmic regime suggestion (quantitative — you can override but must justify)
        if "algo_regime" in ctx:
            prompt += (
                f"\n=== ALGORITHMIC REGIME SUGGESTION ===\n"
                f"Suggested: {ctx['algo_regime']} (bull_score={ctx['algo_bull_score']}, bear_score={ctx['algo_bear_score']})\n"
                f"This is computed from BTC vs SMA200, RSI, MA alignment, F&G, and 24h change.\n"
                f"You may OVERRIDE this but must explain why in your reasoning.\n"
            )

        prompt += "\n=== INTELLIGENCE ===\n"
        if "fear_greed" in ctx:
            prompt += f"Fear & Greed: {ctx['fear_greed']}/100 ({ctx.get('fear_greed_label', '?')})\n"
        if "btc_dominance" in ctx:
            prompt += f"BTC Dominance: {ctx['btc_dominance']:.1f}%\n"
        if "market_cap_change_24h" in ctx:
            prompt += f"Market Cap 24h: {ctx['market_cap_change_24h']:+.1f}%\n"
        if "reddit_sentiment" in ctx:
            prompt += f"Reddit: {ctx['reddit_sentiment']} | {ctx['reddit_engagement']}\n"
        if "trending_coins" in ctx:
            prompt += f"Trending: {ctx['trending_coins']}\n"
        if "total_defi_tvl" in ctx:
            prompt += f"DeFi TVL: ${ctx['total_defi_tvl']:,.0f}\n"

        prompt += f"\n=== PORTFOLIO ===\n"
        prompt += f"Value: ${ctx['portfolio_value']:,.2f} | Return: {ctx['portfolio_return']:+.2f}%\n"
        prompt += f"Positions: {ctx['open_positions']} | Drawdown: {ctx['drawdown']:.2f}%\n"
        prompt += f"Signal Accuracy: {ctx['accuracy']}% ({ctx['total_signals']} tracked)\n"

        if ctx.get("last_strategy_adjustment"):
            prompt += f"\n=== YOUR LAST CYCLE FEEDBACK ===\n"
            prompt += f"Strategy Adjustment: {ctx['last_strategy_adjustment']}\n"
            if ctx.get("last_assessment"):
                prompt += f"Assessment: {ctx['last_assessment']}\n"
            if not ctx.get("last_regime_was_valid", True):
                prompt += f"WARNING: Your last regime call ({ctx.get('last_regime_called', '?')}) was WRONG. Adjust.\n"

        if ctx.get("experience_summary"):
            prompt += f"\n=== YOUR EXPERIENCE (accumulated cycle history) ===\n"
            prompt += ctx["experience_summary"] + "\n"

        prompt += "\nIssue your directive."
        return prompt

    def _build_post_prompt(self, ctx: dict) -> str:
        prompt = "Review this cycle's results and issue feedback.\n\n"
        prompt += f"=== YOUR DIRECTIVE THIS CYCLE ===\n"
        prompt += f"Regime: {ctx['directed_regime']}\n"
        prompt += f"Strategy: {ctx['directed_strategy']}\n"
        sw = ctx.get("directed_sector_weights", {})
        if sw:
            prompt += f"Sector Weights: {sw}\n"

        prompt += f"\n=== RESULTS ===\n"
        prompt += f"Coins Analyzed: {ctx['coins_analyzed']} | Signals: {ctx['total_signals']} | Orders Executed: {ctx['orders_executed']}\n"
        prompt += f"Portfolio: ${ctx['portfolio_value']:,.2f} | Return: {ctx['portfolio_return']:+.2f}% | Drawdown: {ctx['drawdown']:.2f}%\n"

        prompt += f"\n=== AGGREGATED VERDICTS ===\n"
        for v in ctx["aggregated_verdicts"]:
            base = v["symbol"].replace("USDT", "")
            prompt += f"  {base}: {v['action']} (conf: {v['confidence']:.0%}, consensus: {v['consensus']:.0%})\n"

        prompt += f"\n=== TEAM PERFORMANCE ===\n"
        prompt += f"Overall Accuracy: {ctx['overall_accuracy']}%\n"
        for team, stats in ctx["team_stats"].items():
            prompt += f"  {team}: {stats['accuracy']}% accuracy ({stats['total']} signals) — {stats['status']}\n"

        prompt += "\nReview each team. Set capital allocation. Adjust strategy if needed."
        return prompt
