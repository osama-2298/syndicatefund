"""
Signal Aggregator — God-Tier, Research-Backed.

Based on:
- Bayesian log-odds combination (mathematically correct signal combining)
- Bridgewater believability-weighted voting
- Goldman Sachs signal quality integration
- Shannon entropy for disagreement
- Team hierarchy (Macro override, Technical gate)
- Conviction distribution analysis (polarization detection)
- Close-call detection with position size modulation
- Alert system for edge cases

This is DETERMINISTIC — no LLM, no bias, pure math.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

import structlog

from hivemind.data.models import (
    AgentProfile,
    AggregatedSignal,
    Signal,
    SignalAction,
)

logger = structlog.get_logger()

BULLISH_ACTIONS = {SignalAction.BUY, SignalAction.COVER}
BEARISH_ACTIONS = {SignalAction.SELL, SignalAction.SHORT}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _conviction_to_log_odds(conviction: int) -> float:
    """Convert conviction (0-10) to log-odds for Bayesian combination."""
    p = _clamp(conviction / 10.0, 0.05, 0.95)
    return math.log(p / (1 - p))


def _log_odds_to_confidence(log_odds: float) -> float:
    """Convert log-odds back to probability (0-1)."""
    return 1.0 / (1.0 + math.exp(-log_odds))


def _shannon_entropy(counts: dict[str, int], total: int) -> float:
    """Shannon entropy of vote distribution. 0 = unanimous."""
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        if c > 0:
            p = c / total
            h -= p * math.log2(p)
    return h


class AggregationAlert:
    """An alert generated during aggregation."""

    def __init__(self, alert_type: str, severity: str, message: str, data: dict | None = None):
        self.alert_type = alert_type
        self.severity = severity  # HIGH, MEDIUM, LOW, INFO
        self.message = message
        self.data = data or {}

    def __str__(self) -> str:
        return f"[{self.severity}] {self.alert_type}: {self.message}"


class SignalAggregator:
    """
    God-tier signal aggregation.

    Pipeline:
      1. Quality-weight each signal (track record × CEO weight × agreement × timeframe)
      2. Bayesian log-odds combination (mathematically correct)
      3. Conviction distribution analysis (detect polarization)
      4. Macro regime gate (can override direction)
      5. Technical execution gate (can reduce confidence)
      6. Close-call detection
      7. Alert generation
      8. Final confidence + decision quality rating
    """

    def __init__(
        self,
        team_weight_overrides: dict[str, float] | None = None,
        regime: str = "ranging",
    ) -> None:
        self._team_weights = team_weight_overrides or {}
        self._regime = regime.lower()

    def aggregate(
        self,
        signals: list[Signal],
        agent_profiles: dict[str, AgentProfile],
    ) -> list[AggregatedSignal]:
        if not signals:
            return []

        by_symbol: dict[str, list[Signal]] = defaultdict(list)
        for sig in signals:
            by_symbol[sig.symbol].append(sig)

        results = []
        for symbol, syms in by_symbol.items():
            agg = self._aggregate_symbol(symbol, syms, agent_profiles)
            results.append(agg)
            logger.info(
                "signal_aggregated",
                symbol=symbol,
                action=agg.recommended_action.value,
                confidence=round(agg.aggregated_confidence, 3),
                consensus=round(agg.consensus_ratio, 3),
                quality=agg.weighted_scores.get("_decision_quality", "?"),
            )

        return results

    # ─────────────────────────────────────────────
    #  CORE AGGREGATION
    # ─────────────────────────────────────────────

    def _aggregate_symbol(
        self,
        symbol: str,
        signals: list[Signal],
        profiles: dict[str, AgentProfile],
    ) -> AggregatedSignal:
        alerts: list[AggregationAlert] = []

        # ── Step 1: Quality-weight each signal ──
        weighted_signals = []
        for sig in signals:
            w = self._compute_quality_weight(sig, profiles)
            if w <= 0:
                continue
            weighted_signals.append((sig, w))

        if not weighted_signals:
            return self._empty(symbol, signals)

        # ── Step 2: Separate by direction ──
        # CRITICAL: Conviction < 4 signals are NOISE, not data.
        # Even if the manager mapped them to BUY/SHORT, they get zero weight.
        MIN_ACTIONABLE_CONVICTION = 4
        bullish = []
        bearish = []
        neutral = []
        for s, w in weighted_signals:
            conv = s.metadata.get("conviction", int(s.confidence * 10))
            if conv < MIN_ACTIONABLE_CONVICTION:
                # Low conviction = abstention regardless of action
                neutral.append((s, w))
            elif s.action in BULLISH_ACTIONS:
                bullish.append((s, w))
            elif s.action in BEARISH_ACTIONS:
                bearish.append((s, w))
            else:
                neutral.append((s, w))
        n_total = len(weighted_signals)

        # All neutral → genuine no-trade
        if not bullish and not bearish:
            avg_conf = sum(s.confidence * w for s, w in neutral) / max(sum(w for _, w in neutral), 1)
            alerts.append(AggregationAlert("ALL_HOLD", "LOW", "No directional edge detected."))
            return self._build_result(symbol, signals, SignalAction.HOLD, avg_conf, 1.0, alerts, weighted_signals)

        # ── Step 3: Bayesian log-odds combination ──
        bullish_log_odds = 0.0
        bullish_total_w = 0.0
        for sig, w in bullish:
            conv = sig.metadata.get("conviction", int(sig.confidence * 10))
            bullish_log_odds += _conviction_to_log_odds(conv) * w
            bullish_total_w += w

        bearish_log_odds = 0.0
        bearish_total_w = 0.0
        for sig, w in bearish:
            conv = sig.metadata.get("conviction", int(sig.confidence * 10))
            bearish_log_odds += _conviction_to_log_odds(conv) * w
            bearish_total_w += w

        # Normalize
        bull_avg = bullish_log_odds / max(bullish_total_w, 0.001)
        bear_avg = bearish_log_odds / max(bearish_total_w, 0.001)

        bull_conf = _log_odds_to_confidence(bull_avg) if bullish else 0
        bear_conf = _log_odds_to_confidence(bear_avg) if bearish else 0

        # Winner
        if bullish_log_odds > abs(bearish_log_odds):
            direction = "bullish"
            raw_confidence = bull_conf
            action = SignalAction.BUY
            winner_count = len(bullish)
        else:
            direction = "bearish"
            raw_confidence = bear_conf
            action = SignalAction.SHORT if any(s.action == SignalAction.SHORT for s, _ in bearish) else SignalAction.SELL
            winner_count = len(bearish)

        consensus = winner_count / n_total

        # ── Step 4: Conviction distribution (polarization) ──
        all_convictions = [sig.metadata.get("conviction", int(sig.confidence * 10)) for sig, _ in weighted_signals]
        polarization = self._compute_polarization(weighted_signals)
        if polarization > 0.7:
            alerts.append(AggregationAlert(
                "POLARIZATION", "MEDIUM",
                f"Teams are highly polarized (score: {polarization:.2f}). Reducing position.",
                {"convictions": all_convictions},
            ))

        # ── Step 5: Directional strength (margin of victory) ──
        total_directional = bullish_total_w + bearish_total_w
        directional_strength = abs(bullish_log_odds - abs(bearish_log_odds)) / max(abs(bullish_log_odds) + abs(bearish_log_odds), 0.001)
        directional_strength = _clamp(directional_strength, 0, 1)

        # ── Step 6: Disagreement (Shannon entropy) ──
        vote_counts = {"bullish": len(bullish), "bearish": len(bearish), "neutral": len(neutral)}
        entropy = _shannon_entropy(vote_counts, n_total)
        max_entropy = math.log2(3)
        disagreement = entropy / max_entropy if max_entropy > 0 else 0

        # ── Step 6b: Consensus bonus ──
        # When all directional signals agree, breadth of agreement should count.
        # 5/5 same direction gets +15% boost. 3/5 gets no boost.
        n_directional = len(bullish) + len(bearish)
        if n_directional > 0:
            unanimity = max(len(bullish), len(bearish)) / n_directional
            if unanimity >= 0.95:  # Nearly unanimous
                raw_confidence *= 1.15  # 15% boost
            elif unanimity >= 0.80:
                raw_confidence *= 1.08  # 8% boost

        # ── Step 7: Apply modifiers ──
        confidence = raw_confidence

        # 7a: Polarization penalty (high polarization = reduce size)
        polarization_penalty = 1.0 - (polarization * 0.4)
        confidence *= polarization_penalty

        # 7b: Macro regime gate
        confidence, action, macro_alerts = self._apply_macro_gate(
            signals, direction, confidence, action, alerts,
        )
        alerts.extend(macro_alerts)

        # 7c: Technical execution gate
        confidence, tech_alerts = self._apply_technical_gate(
            signals, direction, confidence,
        )
        alerts.extend(tech_alerts)

        # 7d: Smart money divergence check
        sm_alerts = self._check_smart_money_divergence(signals)
        alerts.extend(sm_alerts)

        # ── Step 8: Close-call detection ──
        close_call = (
            directional_strength < 0.15
            or (0.40 <= confidence <= 0.55 and consensus < 0.6)
            or (consensus < 0.5 and polarization > 0.5)
        )
        if close_call:
            confidence *= 0.75  # Reduce to 75% on close calls
            alerts.append(AggregationAlert(
                "CLOSE_CALL", "MEDIUM",
                f"Close call — directional strength {directional_strength:.2f}, consensus {consensus:.0%}.",
            ))

        # ── Step 9: Decision quality rating ──
        if directional_strength > 0.5 and consensus >= 0.7 and polarization < 0.3:
            decision_quality = "HIGH_CONVICTION"
        elif directional_strength > 0.25 and consensus >= 0.5:
            decision_quality = "MODERATE"
        elif close_call:
            decision_quality = "CLOSE_CALL"
        else:
            decision_quality = "LOW"

        # Unanimous high conviction → special alert
        if consensus >= 0.8 and min(all_convictions) >= 6 and polarization < 0.15:
            alerts.append(AggregationAlert(
                "UNANIMOUS_HIGH_CONVICTION", "INFO",
                f"All teams aligned with high conviction. Strongest signal type.",
                {"convictions": all_convictions},
            ))

        confidence = _clamp(confidence, 0.0, 1.0)

        # ── Build result with enriched metadata ──
        scores = {
            "_decision_quality": decision_quality,
            "_directional_strength": round(directional_strength, 3),
            "_polarization": round(polarization, 3),
            "_disagreement": round(disagreement, 3),
            "_close_call": close_call,
            "_alerts": [str(a) for a in alerts],
            "_conviction_distribution": all_convictions,
        }

        # Also include traditional scores for backward compat
        for sig, w in weighted_signals:
            scores[sig.action.value] = scores.get(sig.action.value, 0) + w * sig.confidence

        return AggregatedSignal(
            symbol=symbol,
            recommended_action=action,
            aggregated_confidence=confidence,
            contributing_signals=signals,
            consensus_ratio=consensus,
            weighted_scores=scores,
        )

    # ─────────────────────────────────────────────
    #  QUALITY WEIGHTING
    # ─────────────────────────────────────────────

    def _compute_quality_weight(self, sig: Signal, profiles: dict[str, AgentProfile]) -> float:
        """
        Effective weight = base × CEO multiplier × agreement boost × timeframe boost.
        """
        # Base weight from track record
        profile = profiles.get(sig.agent_id)
        base = profile.weight if profile else 0.5

        # CEO team multiplier
        team_mult = self._team_weights.get(sig.team.value, 1.0)
        if team_mult <= 0:
            return 0.0  # FIRED

        # Agreement boost (from TeamSignal metadata)
        agreement = sig.metadata.get("agreement_level", 0.7)  # Default 0.7 if not a TeamSignal
        agreement_boost = 0.5 + (agreement * 0.5)  # Range: 0.5 to 1.0

        # Timeframe boost (Technical team only)
        tf_alignment = sig.metadata.get("timeframe_alignment", "N/A")
        tf_boost = {"FULLY_ALIGNED": 1.2, "MOSTLY_ALIGNED": 1.0, "CONFLICTING": 0.7}.get(tf_alignment, 1.0)

        return base * team_mult * agreement_boost * tf_boost

    # ─────────────────────────────────────────────
    #  POLARIZATION
    # ─────────────────────────────────────────────

    def _compute_polarization(self, signals: list[tuple]) -> float:
        """
        Measure DIRECTIONAL polarization — how split are teams on DIRECTION?
        Only penalizes when teams disagree on bullish vs bearish.
        Does NOT penalize conviction variance within the same direction.
        """
        if len(signals) < 2:
            return 0.0

        n_bull = sum(1 for s, _ in signals if s.action in BULLISH_ACTIONS)
        n_bear = sum(1 for s, _ in signals if s.action in BEARISH_ACTIONS)
        n_directional = n_bull + n_bear

        if n_directional == 0:
            return 0.0

        # Polarization = how evenly split the directional votes are
        # 0 = all one direction, 1 = perfectly split
        minority = min(n_bull, n_bear)
        polarization = (2 * minority) / n_directional  # 0 to 1

        return polarization

    # ─────────────────────────────────────────────
    #  TEAM HIERARCHY: MACRO GATE
    # ─────────────────────────────────────────────

    def _apply_macro_gate(
        self,
        signals: list[Signal],
        aggregate_direction: str,
        confidence: float,
        action: SignalAction,
        existing_alerts: list,
    ) -> tuple[float, SignalAction, list[AggregationAlert]]:
        """
        Macro sits at the TOP of the hierarchy.
        In crisis/bear regimes, Macro can override bullish aggregate.
        """
        alerts: list[AggregationAlert] = []

        # Find Macro signal
        macro_sig = None
        for sig in signals:
            if sig.team.value == "macro":
                macro_sig = sig
                break

        if macro_sig is None:
            return confidence, action, alerts

        macro_conviction = macro_sig.metadata.get("conviction", int(macro_sig.confidence * 10))
        macro_direction = macro_sig.metadata.get("direction", "BULLISH" if macro_sig.action in BULLISH_ACTIONS else "BEARISH")
        macro_is_bearish = macro_direction == "BEARISH"

        # Crisis regime: Macro MODERATES, doesn't crush.
        # History: March 2020 (F&G=9, CRISIS) was the best buy ever. Don't kill contrarian signals.
        if self._regime == "crisis":
            if macro_is_bearish and aggregate_direction == "bullish":
                confidence *= 0.65  # Moderate, not crush (was 0.3 → 0.65)
                alerts.append(AggregationAlert(
                    "REGIME_OVERRIDE", "HIGH",
                    "CRISIS regime + Macro BEARISH. Bullish signal moderated (not killed — contrarian may be right).",
                ))
            # In crisis, reduce position size but don't prevent trading
            confidence *= 0.75  # Was 0.5 → 0.75

        # Bear regime: Macro moderates, doesn't veto
        elif self._regime == "bear":
            if macro_is_bearish and macro_conviction >= 7 and aggregate_direction == "bullish":
                confidence *= 0.70  # Was 0.5 → 0.70
                alerts.append(AggregationAlert(
                    "REGIME_CONFLICT", "HIGH",
                    f"BEAR regime + Macro BEARISH (conv {macro_conviction}). Bullish signal moderated.",
                ))

        # Macro dissent: mild reduction, not a wall
        elif macro_conviction >= 8 and (
            (macro_is_bearish and aggregate_direction == "bullish") or
            (not macro_is_bearish and aggregate_direction == "bearish")
        ):
            confidence *= 0.85  # Was 0.7 → 0.85
            alerts.append(AggregationAlert(
                "MACRO_DISSENT", "MEDIUM",
                f"Macro high-conviction ({macro_conviction}) dissent. Aggregate moderated.",
            ))

        return confidence, action, alerts

    # ─────────────────────────────────────────────
    #  TEAM HIERARCHY: TECHNICAL GATE
    # ─────────────────────────────────────────────

    def _apply_technical_gate(
        self,
        signals: list[Signal],
        aggregate_direction: str,
        confidence: float,
    ) -> tuple[float, list[AggregationAlert]]:
        """
        Technical is the execution gatekeeper.
        If Technical opposes the aggregate with conflicting timeframes, reduce confidence.
        """
        alerts: list[AggregationAlert] = []

        tech_sig = None
        for sig in signals:
            if sig.team.value == "technical":
                tech_sig = sig
                break

        if tech_sig is None:
            return confidence, alerts

        tech_direction = tech_sig.metadata.get("direction", "BULLISH" if tech_sig.action in BULLISH_ACTIONS else "BEARISH")
        tech_conviction = tech_sig.metadata.get("conviction", int(tech_sig.confidence * 10))
        tf_alignment = tech_sig.metadata.get("timeframe_alignment", "N/A")

        # Technical opposes aggregate AND timeframes are conflicting
        tech_opposes = (
            (tech_direction == "BEARISH" and aggregate_direction == "bullish") or
            (tech_direction == "BULLISH" and aggregate_direction == "bearish")
        )

        if tech_opposes and tf_alignment == "CONFLICTING":
            confidence *= 0.6
            alerts.append(AggregationAlert(
                "TECHNICAL_VETO", "HIGH",
                f"Technical opposes with CONFLICTING timeframes. Poor entry timing.",
            ))
        elif tech_opposes and tech_conviction >= 7:
            confidence *= 0.75
            alerts.append(AggregationAlert(
                "TECHNICAL_DISSENT", "MEDIUM",
                f"Technical high-conviction ({tech_conviction}) dissent against {aggregate_direction}.",
            ))
        elif tech_conviction <= 3:
            confidence *= 0.85
            alerts.append(AggregationAlert(
                "WEAK_TECHNICAL", "LOW",
                f"Technical has very low conviction ({tech_conviction}). No clear setup.",
            ))

        return confidence, alerts

    # ─────────────────────────────────────────────
    #  SMART MONEY DIVERGENCE
    # ─────────────────────────────────────────────

    def _check_smart_money_divergence(self, signals: list[Signal]) -> list[AggregationAlert]:
        """
        When On-Chain (whales) and Sentiment (retail) disagree,
        that's a historically strong signal — flag it.
        """
        alerts = []
        onchain_sig = None
        sentiment_sig = None

        for sig in signals:
            if sig.team.value == "onchain":
                onchain_sig = sig
            elif sig.team.value == "sentiment":
                sentiment_sig = sig

        if onchain_sig is None or sentiment_sig is None:
            return alerts

        oc_dir = onchain_sig.metadata.get("direction", "")
        se_dir = sentiment_sig.metadata.get("direction", "")
        oc_conv = onchain_sig.metadata.get("conviction", 0)
        se_conv = sentiment_sig.metadata.get("conviction", 0)

        # Flag divergence when: directions oppose AND at least one side has strong conviction,
        # OR when the conviction gap is large regardless of absolute levels
        diverges = (
            oc_dir and se_dir and oc_dir != se_dir and
            (oc_conv >= 6 or se_conv >= 6 or abs(oc_conv - se_conv) > 4)
        )
        if diverges:
            alerts.append(AggregationAlert(
                "SMART_MONEY_DIVERGENCE", "MEDIUM",
                f"On-Chain ({oc_dir} {oc_conv}) vs Sentiment ({se_dir} {se_conv}). "
                f"Historically favors On-Chain (whale) direction.",
                {"whale_direction": oc_dir, "retail_direction": se_dir},
            ))

        return alerts

    # ─────────────────────────────────────────────
    #  HELPERS
    # ─────────────────────────────────────────────

    def _build_result(
        self, symbol: str, signals: list[Signal], action: SignalAction,
        confidence: float, consensus: float, alerts: list, weighted_signals: list,
    ) -> AggregatedSignal:
        scores: dict[str, Any] = {
            "_alerts": [str(a) for a in alerts],
            "_decision_quality": "ABSTAIN",
        }
        return AggregatedSignal(
            symbol=symbol,
            recommended_action=action,
            aggregated_confidence=_clamp(confidence, 0, 1),
            contributing_signals=signals,
            consensus_ratio=consensus,
            weighted_scores=scores,
        )

    def _empty(self, symbol: str, signals: list[Signal]) -> AggregatedSignal:
        return AggregatedSignal(
            symbol=symbol,
            recommended_action=SignalAction.HOLD,
            aggregated_confidence=0.0,
            contributing_signals=signals,
            consensus_ratio=0.0,
            weighted_scores={"_decision_quality": "ABSTAIN", "_alerts": []},
        )
