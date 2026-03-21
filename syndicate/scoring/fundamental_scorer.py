"""
Fundamental Scorer — Supply dynamics and valuation metrics.

In crypto, traditional valuation (P/E, DCF) doesn't apply. Instead we use:
- FDV/MCap ratio: high = lots of tokens still to unlock (dilution risk)
- Supply inflation: high circulating/max supply ratio = less dilution ahead
- ATH distance: not a valuation metric per se, but contextualizes current price
- Price momentum (30d, 200d): trend persistence
"""

from __future__ import annotations

import structlog

from syndicate.scoring.models import ScoreComponent

logger = structlog.get_logger()


def score_fundamental(
    market_cap: float | None = None,
    fully_diluted_valuation: float | None = None,
    circulating_supply: float | None = None,
    max_supply: float | None = None,
    ath_distance_pct: float | None = None,
    price_change_30d: float | None = None,
    price_change_200d: float | None = None,
) -> tuple[float, list[ScoreComponent]]:
    """
    Compute fundamental score from supply dynamics and valuation.

    Returns:
        (score, components) where score is -10 to +10
    """
    score = 0.0
    components: list[ScoreComponent] = []

    # ── FDV / MARKET CAP RATIO ──
    # High ratio = lots of tokens still locked/unvested = dilution risk
    if market_cap and fully_diluted_valuation and market_cap > 0:
        fdv_ratio = fully_diluted_valuation / market_cap

        if fdv_ratio > 10:
            delta = -2.0
            reason = f"FDV/MCap ratio {fdv_ratio:.1f}x — extreme dilution risk"
        elif fdv_ratio > 5:
            delta = -1.0
            reason = f"FDV/MCap ratio {fdv_ratio:.1f}x — high dilution risk"
        elif fdv_ratio > 2:
            delta = -0.3
            reason = f"FDV/MCap ratio {fdv_ratio:.1f}x — moderate dilution"
        elif fdv_ratio <= 1.2:
            delta = 0.5
            reason = f"FDV/MCap ratio {fdv_ratio:.1f}x — nearly fully circulating"
        else:
            delta = 0.0
            reason = f"FDV/MCap ratio {fdv_ratio:.1f}x — normal"

        if delta != 0:
            score += delta
            components.append(ScoreComponent(name="fdv_ratio", value=delta, reason=reason))

    # ── SUPPLY RATIO ──
    # High circulating/max = less future dilution
    if circulating_supply and max_supply and max_supply > 0:
        supply_ratio = circulating_supply / max_supply

        if supply_ratio > 0.90:
            delta = 0.5
            reason = f"Supply {supply_ratio*100:.0f}% circulating — minimal dilution left"
        elif supply_ratio < 0.30:
            delta = -0.5
            reason = f"Supply {supply_ratio*100:.0f}% circulating — heavy future dilution"
        else:
            delta = 0.0
            reason = f"Supply {supply_ratio*100:.0f}% circulating"

        if delta != 0:
            score += delta
            components.append(ScoreComponent(name="supply_ratio", value=delta, reason=reason))

    # ── PRICE MOMENTUM (30d) ──
    # Strong recent momentum tends to persist (momentum factor)
    if price_change_30d is not None:
        if price_change_30d > 30:
            delta = 1.0
            reason = f"30d price change {price_change_30d:+.0f}% (strong momentum)"
        elif price_change_30d > 10:
            delta = 0.5
            reason = f"30d price change {price_change_30d:+.0f}% (positive momentum)"
        elif price_change_30d < -30:
            delta = -1.0
            reason = f"30d price change {price_change_30d:+.0f}% (strong downtrend)"
        elif price_change_30d < -10:
            delta = -0.5
            reason = f"30d price change {price_change_30d:+.0f}% (negative momentum)"
        else:
            delta = 0.0
            reason = f"30d price change {price_change_30d:+.0f}% (flat)"

        if delta != 0:
            score += delta
            components.append(ScoreComponent(name="momentum_30d", value=delta, reason=reason))

    # ── PRICE MOMENTUM (200d) ──
    # Longer-term trend context
    if price_change_200d is not None:
        if price_change_200d > 100:
            delta = 0.5
            reason = f"200d price change {price_change_200d:+.0f}% (strong long-term trend)"
        elif price_change_200d < -50:
            delta = -0.5
            reason = f"200d price change {price_change_200d:+.0f}% (deep long-term decline)"
        else:
            delta = 0.0
            reason = f"200d price change {price_change_200d:+.0f}%"

        if delta != 0:
            score += delta
            components.append(ScoreComponent(name="momentum_200d", value=delta, reason=reason))

    score = max(-10.0, min(10.0, score))
    return score, components
