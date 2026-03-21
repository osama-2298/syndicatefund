"""CommGenerator — transforms pipeline data into comm dicts.

Zero extra LLM calls. Uses existing reasoning text from agents + personality prefixes.
"""

from __future__ import annotations

from syndicate.comms.personalities import get_personality, TEAM_MANAGER_MAP


class CommGenerator:
    """Generate all comms from a completed cycle's data."""

    def generate_all(
        self,
        directive=None,
        selection=None,
        risk_limits=None,
        cro_reasoning: str = "",
        individual_signals: list | None = None,
        manager_signals: list | None = None,
        aggregated: list | None = None,
        final_orders: list | None = None,
        results: list | None = None,
        ceo_feedback: dict | None = None,
        quant_scores: dict | None = None,
        risk_snapshot=None,
    ) -> list[dict]:
        comms: list[dict] = []
        comms.extend(self._from_ceo_directive(directive))
        comms.extend(self._from_coo_selection(selection))
        comms.extend(self._from_cro_rules(risk_limits, cro_reasoning))
        comms.extend(self._from_quant_scores(quant_scores or {}))
        comms.extend(self._from_agent_signals(individual_signals or []))
        comms.extend(self._from_manager_signals(manager_signals or []))
        comms.extend(self._from_aggregation(aggregated or []))
        comms.extend(self._from_portfolio_risk(risk_snapshot))
        comms.extend(self._from_trades(final_orders or [], results or []))
        comms.extend(self._from_ceo_review(ceo_feedback))
        return comms

    # ── Executive comms ──────────────────────────────────────────────

    def _from_ceo_directive(self, directive) -> list[dict]:
        if directive is None:
            return []
        p = get_personality("CEO")
        regime = getattr(directive, "regime", None)
        regime_str = regime.value if hasattr(regime, "value") else str(regime or "unknown")
        risk_mult = getattr(directive, "risk_multiplier", 1.0)
        focus = getattr(directive, "focus_strategy", "")
        content = (
            f"Market regime classified as {regime_str.upper()}. "
            f"Risk multiplier set to {risk_mult}x. "
        )
        if focus:
            content += f"Strategic focus: {focus}"
        return [{
            "comm_type": "ceo_directive",
            "agent_class": "CEO",
            "agent_name": p["name"],
            "team": None,
            "symbol": None,
            "direction": regime_str.upper(),
            "conviction": None,
            "content": content,
            "metadata": {
                "regime": regime_str,
                "risk_multiplier": risk_mult,
                "sector_weights": getattr(directive, "sector_weights", {}),
                "focus_strategy": focus,
            },
        }]

    def _from_coo_selection(self, selection) -> list[dict]:
        if selection is None:
            return []
        p = get_personality("COO")
        coins = getattr(selection, "selected_coins", [])
        reasoning = getattr(selection, "reasoning", "")
        scores = getattr(selection, "scores", {})
        coin_list = ", ".join(c.replace("USDT", "") for c in coins)
        content = f"Selected {len(coins)} coins for analysis: {coin_list}. "
        if reasoning:
            content += reasoning[:300]
        return [{
            "comm_type": "coo_selection",
            "agent_class": "COO",
            "agent_name": p["name"],
            "team": None,
            "symbol": None,
            "direction": None,
            "conviction": None,
            "content": content,
            "metadata": {
                "selected_coins": coins,
                "scores": {k: round(v, 3) if isinstance(v, float) else v for k, v in scores.items()},
            },
        }]

    def _from_cro_rules(self, risk_limits, cro_reasoning: str) -> list[dict]:
        if risk_limits is None:
            return []
        p = get_personality("CRO")
        content = cro_reasoning[:400] if cro_reasoning else "Risk parameters set for this cycle."
        return [{
            "comm_type": "cro_rules",
            "agent_class": "CRO",
            "agent_name": p["name"],
            "team": None,
            "symbol": None,
            "direction": None,
            "conviction": None,
            "content": content,
            "metadata": {
                "max_position_pct": getattr(risk_limits, "max_position_pct", None),
                "max_drawdown_pct": getattr(risk_limits, "max_drawdown_pct", None),
                "max_open_positions": getattr(risk_limits, "max_open_positions", None),
                "min_signal_confidence": getattr(risk_limits, "min_signal_confidence", None),
                "min_consensus_ratio": getattr(risk_limits, "min_consensus_ratio", None),
            },
        }]

    # ── Agent signals ────────────────────────────────────────────────

    def _from_agent_signals(self, signals: list) -> list[dict]:
        comms = []
        for sig in signals:
            meta = getattr(sig, "metadata", {}) or {}
            # agent_class is tagged by _run_single_agent / _run_single_agent_dynamic
            agent_class = meta.get("agent_class", "") or getattr(sig, "agent_id", "")
            p = get_personality(agent_class)
            team_val = getattr(sig, "team", None)
            team_str = team_val.value if hasattr(team_val, "value") else (str(team_val) if team_val else p.get("team") or "")
            action_val = getattr(sig, "action", None)
            action_str = action_val.value if hasattr(action_val, "value") else str(action_val or "")
            direction = meta.get("direction", action_str)
            conviction = meta.get("conviction", int(getattr(sig, "confidence", 0.0) * 10))
            reasoning = getattr(sig, "reasoning", "") or ""
            confidence = getattr(sig, "confidence", 0.0)
            symbol = getattr(sig, "symbol", None)

            content = reasoning[:500] if reasoning else f"{direction} signal with {confidence:.0%} confidence."

            comms.append({
                "comm_type": "agent_signal",
                "agent_class": agent_class,
                "agent_name": p["name"],
                "team": team_str,
                "symbol": symbol,
                "direction": direction,
                "conviction": conviction,
                "content": content,
                "metadata": {
                    "confidence": round(confidence, 4),
                    "title": p.get("title", ""),
                },
            })
        return comms

    # ── Manager synthesis ────────────────────────────────────────────

    def _from_manager_signals(self, signals: list) -> list[dict]:
        comms = []
        for sig in signals:
            meta = getattr(sig, "metadata", {}) or {}
            agent_id = getattr(sig, "agent_id", "") or ""
            team_val = getattr(sig, "team", None)
            team_str = team_val.value if hasattr(team_val, "value") else (str(team_val) if team_val else "")
            # Resolve manager personality
            mgr_key = TEAM_MANAGER_MAP.get(team_str, agent_id)
            p = get_personality(mgr_key)
            action_val = getattr(sig, "action", None)
            action_str = action_val.value if hasattr(action_val, "value") else str(action_val or "")
            direction = meta.get("direction", action_str)
            conviction = meta.get("conviction", int(getattr(sig, "confidence", 0.0) * 10))
            reasoning = getattr(sig, "reasoning", "") or ""
            confidence = getattr(sig, "confidence", 0.0)
            symbol = getattr(sig, "symbol", None)

            content = reasoning[:500] if reasoning else f"Team synthesis: {direction} with {confidence:.0%} confidence."

            comms.append({
                "comm_type": "manager_synthesis",
                "agent_class": mgr_key,
                "agent_name": p["name"],
                "team": team_str,
                "symbol": symbol,
                "direction": direction,
                "conviction": conviction,
                "content": content,
                "metadata": {
                    "confidence": round(confidence, 4),
                    "title": p.get("title", ""),
                },
            })
        return comms

    # ── Quant Scoring Engine ──────────────────────────────────────────

    def _from_quant_scores(self, quant_scores: dict) -> list[dict]:
        """Generate comms from the Quantitative Scoring Engine (Layer 1)."""
        comms = []
        for symbol, qs in quant_scores.items():
            base = symbol.replace("USDT", "")
            action = getattr(qs, "action", "HOLD")
            composite = getattr(qs, "composite_score", 0)
            confidence = getattr(qs, "confidence", 0)

            tech = getattr(qs, "technical_score", 0)
            sent = getattr(qs, "sentiment_score", 0)
            macro = getattr(qs, "macro_score", 0)
            onchain = getattr(qs, "onchain_score", 0)
            fund = getattr(qs, "fundamental_score", 0)

            content = (
                f"Quantitative analysis for {base}: {action} "
                f"(composite {composite:+.2f}, confidence {confidence:.0%}). "
                f"Technical {tech:+.1f} | Sentiment {sent:+.1f} | "
                f"Macro {macro:+.1f} | On-Chain {onchain:+.1f} | Fundamental {fund:+.1f}"
            )

            direction = "BULLISH" if action == "BUY" else "BEARISH" if action == "SELL" else "NEUTRAL"
            comms.append({
                "comm_type": "quant_scoring",
                "agent_class": "QuantScoringEngine",
                "agent_name": "Quant Engine",
                "team": None,
                "symbol": symbol,
                "direction": direction,
                "conviction": int(confidence * 10),
                "content": content,
                "metadata": {
                    "action": action,
                    "composite_score": round(composite, 4),
                    "confidence": round(confidence, 4),
                    "technical_score": round(tech, 4),
                    "sentiment_score": round(sent, 4),
                    "macro_score": round(macro, 4),
                    "onchain_score": round(onchain, 4),
                    "fundamental_score": round(fund, 4),
                    "components": getattr(qs, "components", {}),
                },
            })
        return comms

    def _from_portfolio_risk(self, risk_snapshot) -> list[dict]:
        """Generate comm from portfolio-level risk check."""
        if risk_snapshot is None:
            return []

        dd_pct = getattr(risk_snapshot, "drawdown_pct", 0)
        heat = getattr(risk_snapshot, "portfolio_heat", 0)
        corr = getattr(risk_snapshot, "avg_correlation", 0)
        level = getattr(risk_snapshot, "drawdown_level", None)
        level_name = level.name if level else "OK"
        actions = getattr(risk_snapshot, "actions", [])

        content = (
            f"Portfolio risk check: Drawdown {dd_pct*100:.1f}% (level {level_name}), "
            f"heat {heat*100:.1f}%, avg correlation {corr:.2f}."
        )
        if actions:
            content += f" Actions: {'; '.join(actions[:3])}"

        direction = "NEUTRAL"
        if level_name in ("REDUCED", "BTC_ETH_ONLY"):
            direction = "BEARISH"
        elif level_name == "HALTED":
            direction = "BEARISH"

        return [{
            "comm_type": "risk_check",
            "agent_class": "PortfolioRiskManager",
            "agent_name": "Risk Sentinel",
            "team": None,
            "symbol": None,
            "direction": direction,
            "conviction": max(1, min(10, int(dd_pct * 100))),
            "content": content,
            "metadata": {
                "drawdown_pct": round(dd_pct * 100, 2),
                "drawdown_level": level_name,
                "portfolio_heat": round(heat * 100, 2),
                "avg_correlation": round(corr, 4),
                "actions": actions,
            },
        }]

    # ── Aggregation ──────────────────────────────────────────────────

    def _from_aggregation(self, aggregated: list) -> list[dict]:
        comms = []
        for agg in aggregated:
            symbol = getattr(agg, "symbol", "")
            action_val = getattr(agg, "recommended_action", None)
            action_str = action_val.value if hasattr(action_val, "value") else str(action_val or "")
            confidence = getattr(agg, "aggregated_confidence", 0)
            consensus = getattr(agg, "consensus_ratio", 0)
            weighted = getattr(agg, "weighted_scores", {})
            quality = weighted.get("_decision_quality", "")
            alerts = weighted.get("_alerts", [])
            scores = {k: round(v, 3) if isinstance(v, float) else v for k, v in weighted.items() if not k.startswith("_")}

            content = (
                f"Aggregated signal for {symbol.replace('USDT', '')}: {action_str} "
                f"with {confidence:.0%} confidence and {consensus:.0%} consensus."
            )
            if quality:
                content += f" Decision quality: {quality}."
            if alerts:
                content += f" Alerts: {'; '.join(str(a) for a in alerts[:3])}"

            comms.append({
                "comm_type": "aggregation",
                "agent_class": "Aggregator",
                "agent_name": "Signal Aggregator",
                "team": None,
                "symbol": symbol,
                "direction": action_str,
                "conviction": int(confidence * 10),
                "content": content,
                "metadata": {
                    "confidence": round(confidence, 4),
                    "consensus": round(consensus, 4),
                    "team_scores": scores,
                    "decision_quality": quality,
                    "alerts": alerts[:5],
                },
            })
        return comms

    # ── Trade execution ──────────────────────────────────────────────

    def _from_trades(self, final_orders: list, results: list) -> list[dict]:
        comms = []
        result_by_sym = {}
        for r in results:
            sym = getattr(r, "symbol", "")
            result_by_sym[sym] = r

        for order in final_orders:
            symbol = getattr(order, "symbol", "")
            side_val = getattr(order, "side", None)
            side_str = side_val.value if hasattr(side_val, "value") else str(side_val or "")
            params = getattr(order, "params", None)
            result = result_by_sym.get(symbol)
            price = getattr(result, "executed_price", 0) if result else 0

            content = f"Executed {side_str} {symbol.replace('USDT', '')} at ${price:,.2f}."
            if params:
                sl = getattr(params, "stop_loss_price", 0)
                tp1 = getattr(params, "take_profit_1", 0)
                if sl:
                    content += f" Stop loss: ${sl:,.2f}."
                if tp1:
                    content += f" Take profit: ${tp1:,.2f}."

            comms.append({
                "comm_type": "trade_execution",
                "agent_class": "Execution",
                "agent_name": "Kai Nakamura",
                "team": None,
                "symbol": symbol,
                "direction": side_str,
                "conviction": None,
                "content": content,
                "metadata": {
                    "side": side_str,
                    "price": price,
                    "stop_loss": getattr(params, "stop_loss_price", 0) if params else 0,
                    "take_profit_1": getattr(params, "take_profit_1", 0) if params else 0,
                },
            })
        return comms

    # ── CEO review ───────────────────────────────────────────────────

    def _from_ceo_review(self, feedback: dict | None) -> list[dict]:
        if not feedback:
            return []
        p = get_personality("CEO")
        summary = feedback.get("summary", "")
        grade = feedback.get("grade", "")
        content = f"Cycle grade: {grade}. " if grade else ""
        content += summary[:400] if summary else "Post-cycle review complete."

        return [{
            "comm_type": "ceo_review",
            "agent_class": "CEO",
            "agent_name": p["name"],
            "team": None,
            "symbol": None,
            "direction": None,
            "conviction": None,
            "content": content,
            "metadata": {
                "grade": grade,
                "team_actions": feedback.get("team_actions", []),
            },
        }]
