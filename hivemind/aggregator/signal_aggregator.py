"""
Signal Aggregator — Conflict-Aware, Meta-Label Inspired.

Based on research from:
- Lopez de Prado's Meta-Labeling (separate direction from trade/no-trade)
- Bridgewater's believability-weighted voting
- Shannon entropy for disagreement measurement
- Condorcet Jury Theorem for independent voter aggregation

KEY DESIGN CHANGES from naive averaging:
1. Agents vote on DIRECTION first (bullish vs bearish), HOLD is NOT a direction
2. Conviction is measured separately from direction
3. Disagreement is INFORMATION, not noise — it modulates position size
4. HOLD signals are treated as "no edge" (low conviction), not as a vote AGAINST trading
5. Team weights from CEO decisions are applied
"""

from __future__ import annotations

import math
from collections import defaultdict

import structlog

from hivemind.data.models import (
    AgentProfile,
    AggregatedSignal,
    Signal,
    SignalAction,
)

logger = structlog.get_logger()

# Actions grouped by direction
BULLISH_ACTIONS = {SignalAction.BUY, SignalAction.COVER}
BEARISH_ACTIONS = {SignalAction.SELL, SignalAction.SHORT}
NEUTRAL_ACTIONS = {SignalAction.HOLD}


def _shannon_entropy(votes: dict[str, int], total: int) -> float:
    """Compute Shannon entropy of vote distribution. 0 = unanimous, higher = more disagreement."""
    if total <= 0:
        return 0.0
    entropy = 0.0
    for count in votes.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    return entropy


class SignalAggregator:
    """
    Conflict-aware signal aggregation with meta-label-inspired separation
    of direction from trade/no-trade decision.
    """

    def __init__(self, team_weight_overrides: dict[str, float] | None = None) -> None:
        self._team_weights = team_weight_overrides or {}

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
        for symbol, symbol_signals in by_symbol.items():
            agg = self._aggregate_symbol(symbol, symbol_signals, agent_profiles)
            results.append(agg)
            logger.info(
                "signal_aggregated",
                symbol=symbol,
                action=agg.recommended_action.value,
                confidence=round(agg.aggregated_confidence, 3),
                consensus=round(agg.consensus_ratio, 3),
                n_signals=len(symbol_signals),
            )

        return results

    def _aggregate_symbol(
        self,
        symbol: str,
        signals: list[Signal],
        agent_profiles: dict[str, AgentProfile],
    ) -> AggregatedSignal:
        """
        Meta-label inspired aggregation:
        Step 1: Determine DIRECTION (bullish vs bearish) — HOLD is NOT a vote for "do nothing"
        Step 2: Measure CONVICTION (weighted confidence of directional signals)
        Step 3: Measure DISAGREEMENT (entropy) — modulates final confidence
        Step 4: Determine final action and confidence
        """
        # ── Step 1: Separate directional signals from neutral ──
        bullish_signals = []
        bearish_signals = []
        neutral_signals = []
        weighted_scores: dict[str, float] = defaultdict(float)
        total_weight = 0.0

        for sig in signals:
            # Get effective weight (agent track record × CEO team multiplier)
            profile = agent_profiles.get(sig.agent_id)
            agent_weight = profile.weight if profile else 0.5
            team_multiplier = self._team_weights.get(sig.team.value, 1.0)

            if team_multiplier <= 0:
                continue  # Team has been FIRED

            effective_weight = agent_weight * team_multiplier

            # Classify signal by direction
            if sig.action in BULLISH_ACTIONS:
                bullish_signals.append((sig, effective_weight))
            elif sig.action in BEARISH_ACTIONS:
                bearish_signals.append((sig, effective_weight))
            else:
                neutral_signals.append((sig, effective_weight))

            # Also compute traditional weighted scores for compatibility
            score = effective_weight * sig.confidence
            weighted_scores[sig.action.value] += score
            total_weight += effective_weight

        n_total = len(bullish_signals) + len(bearish_signals) + len(neutral_signals)
        if n_total == 0:
            return self._empty_signal(symbol, signals)

        # ── Step 2: Directional conviction ──
        # Bullish conviction: weighted confidence of bullish signals
        bullish_conviction = 0.0
        bullish_weight = 0.0
        for sig, w in bullish_signals:
            bullish_conviction += w * sig.confidence
            bullish_weight += w

        bearish_conviction = 0.0
        bearish_weight = 0.0
        for sig, w in bearish_signals:
            bearish_conviction += w * sig.confidence
            bearish_weight += w

        # Neutral signals contribute NOTHING to direction — they're abstentions
        # But their confidence matters for the "no edge" assessment
        neutral_avg_conf = 0.0
        if neutral_signals:
            neutral_avg_conf = sum(s.confidence * w for s, w in neutral_signals) / sum(w for _, w in neutral_signals)

        # ── Step 3: Measure disagreement ──
        direction_votes = {
            "bullish": len(bullish_signals),
            "bearish": len(bearish_signals),
            "neutral": len(neutral_signals),
        }
        n_directional = len(bullish_signals) + len(bearish_signals)
        entropy = _shannon_entropy(direction_votes, n_total)
        max_entropy = math.log2(3)  # Maximum for 3 categories
        disagreement = entropy / max_entropy if max_entropy > 0 else 0  # 0 to 1

        # ── Step 4: Determine action and confidence ──

        # Case 1: Strong directional consensus (majority of agents pick a direction)
        if n_directional > 0 and (bullish_conviction > 0 or bearish_conviction > 0):
            if bullish_conviction > bearish_conviction:
                # Bullish wins
                direction = "bullish"
                raw_confidence = bullish_conviction / (bullish_weight if bullish_weight > 0 else 1)
                best_action = SignalAction.BUY
                consensus = len(bullish_signals) / n_total
            else:
                # Bearish wins
                direction = "bearish"
                raw_confidence = bearish_conviction / (bearish_weight if bearish_weight > 0 else 1)
                best_action = SignalAction.SHORT if any(
                    s.action == SignalAction.SHORT for s, _ in bearish_signals
                ) else SignalAction.SELL
                consensus = len(bearish_signals) / n_total

            # Apply disagreement penalty — high disagreement reduces confidence
            # But doesn't kill it (minimum 60% of raw confidence preserved)
            disagreement_penalty = 1.0 - (disagreement * 0.4)
            adjusted_confidence = raw_confidence * disagreement_penalty

            # Bonus: if neutral signals have LOW confidence (agents say "I have no edge"),
            # don't let them drag down a strong directional signal
            # Only penalize if neutral signals have HIGH confidence (agents actively choose HOLD)
            if neutral_signals and neutral_avg_conf > 0.6:
                # Strong HOLD signals from some agents — reduce confidence
                hold_penalty = len(neutral_signals) / n_total * 0.3
                adjusted_confidence *= (1 - hold_penalty)

        # Case 2: All neutral (everyone says HOLD)
        elif n_directional == 0:
            best_action = SignalAction.HOLD
            adjusted_confidence = neutral_avg_conf
            consensus = 1.0

        # Case 3: Only neutral signals with any confidence
        else:
            best_action = SignalAction.HOLD
            adjusted_confidence = 0.0
            consensus = 0.0

        # Clamp confidence
        adjusted_confidence = max(0.0, min(1.0, adjusted_confidence))

        return AggregatedSignal(
            symbol=symbol,
            recommended_action=best_action,
            aggregated_confidence=adjusted_confidence,
            contributing_signals=signals,
            consensus_ratio=consensus,
            weighted_scores=dict(weighted_scores),
        )

    def _empty_signal(self, symbol: str, signals: list[Signal]) -> AggregatedSignal:
        return AggregatedSignal(
            symbol=symbol,
            recommended_action=SignalAction.HOLD,
            aggregated_confidence=0.0,
            contributing_signals=signals,
            consensus_ratio=0.0,
            weighted_scores={},
        )
