"""
Macro Scorer — Crypto macro environment assessment.

Scores the overall market environment using:
- BTC dominance trend (rising = risk-off for alts)
- Total market cap momentum
- Volume direction (expanding vs contracting)
- BTC vs SMA200 (macro regime for the entire market)
"""

from __future__ import annotations

import structlog

from syndicate.scoring.models import ScoreComponent

logger = structlog.get_logger()


def score_macro(
    btc_dominance: float | None = None,
    btc_dominance_change_24h: float | None = None,
    total_market_cap: float | None = None,
    market_cap_change_24h: float | None = None,
    total_volume_24h: float | None = None,
    volume_change_24h: float | None = None,
    btc_price_vs_sma200: float | None = None,
) -> tuple[float, list[ScoreComponent]]:
    """
    Compute macro score from global crypto market data.

    Returns:
        (score, components) where score is -10 to +10
    """
    score = 0.0
    components: list[ScoreComponent] = []

    # ── BTC DOMINANCE ──
    # Rising dominance = risk-off (money flowing from alts to BTC)
    # Falling dominance = risk-on (money flowing into alts)
    if btc_dominance_change_24h is not None:
        if btc_dominance_change_24h > 1.0:
            delta = -1.5  # Bearish for alts (BTC dominance surging)
            reason = f"BTC dominance rising {btc_dominance_change_24h:+.1f}% (risk-off for alts)"
        elif btc_dominance_change_24h > 0.3:
            delta = -0.5
            reason = f"BTC dominance rising {btc_dominance_change_24h:+.1f}% (mild risk-off)"
        elif btc_dominance_change_24h < -1.0:
            delta = 1.5  # Bullish for alts (alt season signal)
            reason = f"BTC dominance falling {btc_dominance_change_24h:+.1f}% (risk-on, alt season)"
        elif btc_dominance_change_24h < -0.3:
            delta = 0.5
            reason = f"BTC dominance falling {btc_dominance_change_24h:+.1f}% (mild risk-on)"
        else:
            delta = 0.0
            reason = f"BTC dominance stable ({btc_dominance_change_24h:+.1f}%)"

        if delta != 0:
            score += delta
            components.append(ScoreComponent(name="btc_dominance", value=delta, reason=reason))

    # ── TOTAL MARKET CAP MOMENTUM ──
    if market_cap_change_24h is not None:
        if market_cap_change_24h > 5.0:
            delta = 2.0
            reason = f"Market cap surging {market_cap_change_24h:+.1f}% (strong risk-on)"
        elif market_cap_change_24h > 2.0:
            delta = 1.0
            reason = f"Market cap rising {market_cap_change_24h:+.1f}% (risk-on)"
        elif market_cap_change_24h > 0.5:
            delta = 0.3
            reason = f"Market cap up {market_cap_change_24h:+.1f}% (mild positive)"
        elif market_cap_change_24h < -5.0:
            delta = -2.0
            reason = f"Market cap dropping {market_cap_change_24h:+.1f}% (strong risk-off)"
        elif market_cap_change_24h < -2.0:
            delta = -1.0
            reason = f"Market cap falling {market_cap_change_24h:+.1f}% (risk-off)"
        elif market_cap_change_24h < -0.5:
            delta = -0.3
            reason = f"Market cap down {market_cap_change_24h:+.1f}% (mild negative)"
        else:
            delta = 0.0
            reason = f"Market cap flat ({market_cap_change_24h:+.1f}%)"

        score += delta
        components.append(ScoreComponent(name="market_cap_momentum", value=delta, reason=reason))

    # ── VOLUME DIRECTION ──
    # Expanding volume = conviction behind the move
    # Contracting volume = move losing steam
    if volume_change_24h is not None:
        if volume_change_24h > 30:
            # Volume spike — confirms direction
            delta = 0.5 if score > 0 else -0.5 if score < 0 else 0.0
            reason = f"Volume spike {volume_change_24h:+.0f}% (confirms direction)"
        elif volume_change_24h < -30:
            # Volume contracting — move losing steam
            delta = -0.3 if score > 0 else 0.3 if score < 0 else 0.0
            reason = f"Volume contracting {volume_change_24h:+.0f}% (losing conviction)"
        else:
            delta = 0.0
            reason = f"Volume change {volume_change_24h:+.0f}% (normal)"

        if delta != 0:
            score += delta
            components.append(ScoreComponent(name="volume_direction", value=delta, reason=reason))

    # ── BTC vs SMA200 (market-wide regime) ──
    # When BTC is above SMA200, the entire crypto market tends to trend up
    if btc_price_vs_sma200 is not None:
        pct_above = (btc_price_vs_sma200 - 1.0) * 100  # Convert ratio to %

        if pct_above > 20:
            delta = 1.5
            reason = f"BTC {pct_above:.0f}% above SMA200 (strong macro bull)"
        elif pct_above > 5:
            delta = 1.0
            reason = f"BTC {pct_above:.0f}% above SMA200 (macro bull)"
        elif pct_above > 0:
            delta = 0.3
            reason = f"BTC {pct_above:.0f}% above SMA200 (mild bull)"
        elif pct_above > -5:
            delta = -0.3
            reason = f"BTC {pct_above:.0f}% below SMA200 (mild bear)"
        elif pct_above > -20:
            delta = -1.0
            reason = f"BTC {pct_above:.0f}% below SMA200 (macro bear)"
        else:
            delta = -1.5
            reason = f"BTC {pct_above:.0f}% below SMA200 (deep macro bear)"

        score += delta
        components.append(ScoreComponent(name="btc_sma200_regime", value=delta, reason=reason))

    score = max(-10.0, min(10.0, score))
    return score, components
