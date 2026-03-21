"""
On-Chain Scorer — Exchange flows, DeFi TVL trends, whale accumulation.

Key signals:
- Exchange inflows = selling pressure (coins moving to exchanges to sell)
- Exchange outflows = accumulation (coins moving to cold storage)
- DeFi TVL growth = ecosystem health
- BTC network health (hashrate, transaction count) = structural confidence
"""

from __future__ import annotations

import structlog

from syndicate.scoring.models import ScoreComponent

logger = structlog.get_logger()


def score_onchain(
    exchange_flow_direction: str | None = None,
    exchange_btc_reserves: float | None = None,
    exchange_btc_reserves_prev: float | None = None,
    defi_total_tvl: float | None = None,
    defi_tvl_change_24h: float | None = None,
    protocols_growing: int = 0,
    protocols_shrinking: int = 0,
    btc_hashrate: float | None = None,
    btc_transaction_count: int | None = None,
) -> tuple[float, list[ScoreComponent]]:
    """
    Compute on-chain score from blockchain and DeFi data.

    Returns:
        (score, components) where score is -10 to +10
    """
    score = 0.0
    components: list[ScoreComponent] = []

    # ── EXCHANGE FLOW DIRECTION ──
    # This is the strongest on-chain signal
    if exchange_flow_direction is not None:
        direction = exchange_flow_direction.upper()
        if direction == "OUTFLOW":
            delta = 2.0
            reason = "Exchange outflows (accumulation — bullish)"
        elif direction == "STRONG_OUTFLOW":
            delta = 3.0
            reason = "Strong exchange outflows (heavy accumulation)"
        elif direction == "INFLOW":
            delta = -2.0
            reason = "Exchange inflows (selling pressure — bearish)"
        elif direction == "STRONG_INFLOW":
            delta = -3.0
            reason = "Strong exchange inflows (heavy selling)"
        else:
            delta = 0.0
            reason = f"Exchange flow: {direction}"

        if delta != 0:
            score += delta
            components.append(ScoreComponent(name="exchange_flow", value=delta, reason=reason))

    # ── EXCHANGE BTC RESERVE CHANGE ──
    # Direct measurement of supply/demand on exchanges
    if exchange_btc_reserves is not None and exchange_btc_reserves_prev is not None:
        if exchange_btc_reserves_prev > 0:
            reserve_change_pct = ((exchange_btc_reserves - exchange_btc_reserves_prev) / exchange_btc_reserves_prev) * 100

            if reserve_change_pct < -2:
                delta = 1.5
                reason = f"BTC reserves down {reserve_change_pct:.1f}% (accumulation)"
            elif reserve_change_pct < -0.5:
                delta = 0.5
                reason = f"BTC reserves down {reserve_change_pct:.1f}% (mild outflow)"
            elif reserve_change_pct > 2:
                delta = -1.5
                reason = f"BTC reserves up {reserve_change_pct:+.1f}% (selling pressure)"
            elif reserve_change_pct > 0.5:
                delta = -0.5
                reason = f"BTC reserves up {reserve_change_pct:+.1f}% (mild inflow)"
            else:
                delta = 0.0
                reason = f"BTC reserves stable ({reserve_change_pct:+.1f}%)"

            if delta != 0:
                score += delta
                components.append(ScoreComponent(name="btc_reserves", value=delta, reason=reason))

    # ── DEFI TVL TREND ──
    # Growing TVL = healthy ecosystem, more capital in crypto
    if defi_tvl_change_24h is not None:
        if defi_tvl_change_24h > 5:
            delta = 1.5
            reason = f"DeFi TVL surging {defi_tvl_change_24h:+.1f}% (strong growth)"
        elif defi_tvl_change_24h > 1:
            delta = 0.5
            reason = f"DeFi TVL growing {defi_tvl_change_24h:+.1f}%"
        elif defi_tvl_change_24h < -5:
            delta = -1.5
            reason = f"DeFi TVL dropping {defi_tvl_change_24h:+.1f}% (capital flight)"
        elif defi_tvl_change_24h < -1:
            delta = -0.5
            reason = f"DeFi TVL declining {defi_tvl_change_24h:+.1f}%"
        else:
            delta = 0.0
            reason = f"DeFi TVL flat ({defi_tvl_change_24h:+.1f}%)"

        if delta != 0:
            score += delta
            components.append(ScoreComponent(name="defi_tvl", value=delta, reason=reason))

    # ── PROTOCOL GROWTH VS SHRINK ──
    total_protocols = protocols_growing + protocols_shrinking
    if total_protocols > 0:
        growth_ratio = protocols_growing / total_protocols
        if growth_ratio > 0.7:
            delta = 0.5
            reason = f"DeFi ecosystem healthy ({protocols_growing}/{total_protocols} growing)"
        elif growth_ratio < 0.3:
            delta = -0.5
            reason = f"DeFi ecosystem stressed ({protocols_shrinking}/{total_protocols} shrinking)"
        else:
            delta = 0.0
            reason = f"DeFi ecosystem mixed ({protocols_growing}/{total_protocols} growing)"

        if delta != 0:
            score += delta
            components.append(ScoreComponent(name="protocol_health", value=delta, reason=reason))

    score = max(-10.0, min(10.0, score))
    return score, components
