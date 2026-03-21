"""
Sentiment Scorer — F&G extremes and funding rate extremes.

These are the two sentiment signals with documented, backtestable edge:

1. Fear & Greed extremes:
   - F&G 0-10: Sharpe 8.0 historically (extreme fear = contrarian buy)
   - F&G 10-20: positive 30-day return 80% of the time
   - F&G 90-100: negative 30-day return 65% of the time

2. Funding rate extremes:
   - Negative funding < -0.05%: 70-75% probability of bounce (short squeeze)
   - High funding > 0.05%: overleveraged longs, mean reversion risk
"""

from __future__ import annotations

import structlog

from syndicate.scoring.models import ScoreComponent

logger = structlog.get_logger()


def score_sentiment(
    fear_greed: dict | None = None,
    funding_rate: float | None = None,
    cross_exchange_funding: dict | None = None,
    taker_buy_sell_ratio: float | None = None,
    top_trader_long_pct: float | None = None,
) -> tuple[float, list[ScoreComponent]]:
    """
    Compute sentiment score from fear/greed and derivatives positioning.

    Args:
        fear_greed: Fear & Greed Index data (current_value, trend, history)
        funding_rate: Current funding rate (e.g., 0.0001 = 0.01%)
        cross_exchange_funding: {exchange: rate} for cross-exchange spread
        taker_buy_sell_ratio: Ratio of taker buy vs sell volume
        top_trader_long_pct: % of top traders that are long

    Returns:
        (score, components) where score is -10 to +10
    """
    score = 0.0
    components: list[ScoreComponent] = []

    # ── FEAR & GREED INDEX ──
    # Documented historical edge at extremes
    if fear_greed:
        fg_value = fear_greed.get("current_value", 50)
        fg_trend = fear_greed.get("trend", "STABLE")
        is_stale = fear_greed.get("is_stale", False)

        # Apply staleness penalty
        weight = 0.5 if is_stale else 1.0

        if fg_value <= 10:
            # Extreme fear — strongest contrarian buy signal
            # Historical Sharpe 8.0 at this level
            delta = 3.0 * weight
            reason = f"F&G={fg_value} EXTREME FEAR (Sharpe 8.0 historically)"
        elif fg_value <= 20:
            # Fear — strong contrarian buy
            # Positive 30d return 80% of the time
            delta = 2.0 * weight
            reason = f"F&G={fg_value} FEAR (80% positive 30d return)"
        elif fg_value <= 30:
            delta = 1.0 * weight
            reason = f"F&G={fg_value} moderate fear (contrarian lean)"
        elif fg_value <= 45:
            delta = 0.3 * weight
            reason = f"F&G={fg_value} mild fear"
        elif fg_value <= 55:
            delta = 0.0
            reason = f"F&G={fg_value} neutral"
        elif fg_value <= 70:
            delta = -0.3 * weight
            reason = f"F&G={fg_value} mild greed"
        elif fg_value <= 80:
            delta = -1.0 * weight
            reason = f"F&G={fg_value} greed (caution)"
        elif fg_value <= 90:
            # High greed — risk of correction
            delta = -2.0 * weight
            reason = f"F&G={fg_value} HIGH GREED (correction risk)"
        else:
            # Extreme greed — strongest contrarian sell signal
            # Negative 30d return 65% of the time
            delta = -3.0 * weight
            reason = f"F&G={fg_value} EXTREME GREED (65% negative 30d return)"

        score += delta
        components.append(ScoreComponent(name="fear_greed", value=delta, reason=reason))

        # F&G trend matters — worsening fear or greed amplifies the signal
        if fg_trend == "WORSENING" and delta > 0:
            trend_boost = 0.5
            score += trend_boost
            components.append(ScoreComponent(
                name="fg_trend",
                value=trend_boost,
                reason="F&G worsening (fear deepening — stronger buy)",
            ))
        elif fg_trend == "IMPROVING" and delta < 0:
            trend_boost = -0.5
            score += trend_boost
            components.append(ScoreComponent(
                name="fg_trend",
                value=trend_boost,
                reason="F&G improving (greed rising — stronger caution)",
            ))

    # ── FUNDING RATE ──
    # Negative funding = shorts paying longs = crowded shorts = squeeze potential
    # High positive funding = longs paying shorts = crowded longs = correction risk
    if funding_rate is not None:
        if funding_rate < -0.0005:
            # Very negative: 70-75% bounce probability
            delta = 2.5
            reason = f"Funding {funding_rate*100:.3f}% VERY NEGATIVE (short squeeze 70-75%)"
        elif funding_rate < -0.0001:
            delta = 1.5
            reason = f"Funding {funding_rate*100:.3f}% negative (squeeze potential)"
        elif funding_rate < 0:
            delta = 0.5
            reason = f"Funding {funding_rate*100:.3f}% slightly negative (mild bullish)"
        elif funding_rate <= 0.0001:
            delta = 0.0
            reason = f"Funding {funding_rate*100:.3f}% neutral"
        elif funding_rate <= 0.0003:
            delta = -0.5
            reason = f"Funding {funding_rate*100:.3f}% slightly elevated"
        elif funding_rate <= 0.0005:
            delta = -1.5
            reason = f"Funding {funding_rate*100:.3f}% high (overleveraged longs)"
        else:
            delta = -2.5
            reason = f"Funding {funding_rate*100:.3f}% EXTREME (overleveraged, correction likely)"

        score += delta
        components.append(ScoreComponent(name="funding_rate", value=delta, reason=reason))

    # ── CROSS-EXCHANGE FUNDING SPREAD ──
    # If one exchange has very different funding, it's an arb signal
    if cross_exchange_funding and len(cross_exchange_funding) >= 2:
        rates = list(cross_exchange_funding.values())
        spread = max(rates) - min(rates)
        if spread > 0.0005:
            # Significant spread — unusual positioning
            components.append(ScoreComponent(
                name="funding_spread",
                value=0.0,
                reason=f"Cross-exchange funding spread {spread*100:.3f}% (unusual positioning)",
            ))

    # ── TAKER BUY/SELL RATIO ──
    # > 1.0 = more aggressive buying | < 1.0 = more aggressive selling
    if taker_buy_sell_ratio is not None:
        if taker_buy_sell_ratio > 1.3:
            delta = 1.0
            reason = f"Taker ratio {taker_buy_sell_ratio:.2f} (aggressive buying)"
        elif taker_buy_sell_ratio > 1.1:
            delta = 0.5
            reason = f"Taker ratio {taker_buy_sell_ratio:.2f} (mild buy pressure)"
        elif taker_buy_sell_ratio < 0.7:
            delta = -1.0
            reason = f"Taker ratio {taker_buy_sell_ratio:.2f} (aggressive selling)"
        elif taker_buy_sell_ratio < 0.9:
            delta = -0.5
            reason = f"Taker ratio {taker_buy_sell_ratio:.2f} (mild sell pressure)"
        else:
            delta = 0.0
            reason = f"Taker ratio {taker_buy_sell_ratio:.2f} (neutral)"

        if delta != 0:
            score += delta
            components.append(ScoreComponent(name="taker_ratio", value=delta, reason=reason))

    # ── TOP TRADER POSITIONING ──
    # Extreme one-sided positioning = contrarian signal
    if top_trader_long_pct is not None:
        if top_trader_long_pct > 70:
            delta = -1.0
            reason = f"Top traders {top_trader_long_pct:.0f}% long (crowded, contrarian sell)"
        elif top_trader_long_pct < 30:
            delta = 1.0
            reason = f"Top traders {top_trader_long_pct:.0f}% long (crowded short, contrarian buy)"
        else:
            delta = 0.0
            reason = f"Top traders {top_trader_long_pct:.0f}% long (balanced)"

        if delta != 0:
            score += delta
            components.append(ScoreComponent(name="top_trader_pos", value=delta, reason=reason))

    score = max(-10.0, min(10.0, score))
    return score, components
