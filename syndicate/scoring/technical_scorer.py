"""
Technical Scorer — Pure quantitative scoring from price/volume indicators.

Combines research-backed logic from:
- syndicate/backtest/engine.py _generate_deterministic_signals() (Zarattini 2025, PMC/NIH RSI study)
- syndicate/aggregator/signal_aggregator.py compute_deterministic_baseline()

Key research findings embedded:
- RSI 50-100 as TREND CONFIRMATION (773% vs 275% buy-and-hold)
- ADX > 25 as regime filter (only trend-follow when trending)
- EMA12/SMA50 crossover for entry timing
- MACD + RSI combined: 73% win rate
- SMA200 as macro trend direction filter
- Multi-timeframe: daily trend + 4h entry
- Volume confirmation for breakouts
- Bollinger Bands: trend mode (breakout) vs range mode (mean reversion)
"""

from __future__ import annotations

import structlog

from syndicate.scoring.models import ScoreComponent

logger = structlog.get_logger()


def score_technical(
    indicators_4h,
    indicators_1d=None,
    current_price: float = 0.0,
) -> tuple[float, list[ScoreComponent]]:
    """
    Compute technical score from pre-calculated indicators.

    Args:
        indicators_4h: TechnicalIndicators for 4h timeframe
        indicators_1d: TechnicalIndicators for 1d timeframe (optional)
        current_price: Current price of the asset

    Returns:
        (score, components) where score is -10 to +10
    """
    if indicators_4h is None:
        return 0.0, [ScoreComponent(name="no_data", value=0.0, reason="No 4h indicator data")]

    ind = indicators_4h
    ind_d = indicators_1d
    score = 0.0
    components: list[ScoreComponent] = []

    # ── REGIME DETECTION (ADX) ──
    adx = ind.adx_14
    is_trending = adx is not None and adx > 25
    is_strong_trend = adx is not None and adx > 35
    is_ranging = adx is not None and adx < 20

    if adx is not None:
        components.append(ScoreComponent(
            name="adx_regime",
            value=adx,
            reason=f"ADX={adx:.0f} ({'trending' if is_trending else 'ranging' if is_ranging else 'borderline'})",
        ))

    # ── MACRO TREND: SMA200 ──
    macro_bullish = True
    macro_bearish = False
    if ind.sma_200 is not None and current_price > 0:
        macro_bullish = current_price > ind.sma_200
        macro_bearish = current_price < ind.sma_200
        delta = 1.0 if macro_bullish else -1.0
        score += delta
        components.append(ScoreComponent(
            name="sma200",
            value=delta,
            reason=f"Price {'>' if macro_bullish else '<'} SMA200 ({'macro bull' if macro_bullish else 'macro bear'})",
        ))

        # Daily SMA200 confirmation
        if ind_d is not None and ind_d.sma_200 is not None:
            if (current_price > ind_d.sma_200) == macro_bullish:
                daily_delta = 0.5 if macro_bullish else -0.5
                score += daily_delta
                components.append(ScoreComponent(
                    name="sma200_daily_confirm",
                    value=daily_delta,
                    reason="Daily SMA200 confirms macro direction",
                ))

    # ── RSI TREND-FOLLOWING (50-100 zone) ──
    # Research: RSI 50-100 returned 773% vs 275% buy-and-hold
    if ind.rsi_14 is not None:
        rsi = ind.rsi_14
        if 50 <= rsi <= 70:
            delta = 1.5
            reason = f"RSI {rsi:.0f} in bull zone (50-70)"
        elif 70 < rsi <= 80:
            delta = 0.5
            reason = f"RSI {rsi:.0f} strong momentum"
        elif rsi > 80:
            delta = -0.5
            reason = f"RSI {rsi:.0f} overheated"
        elif 30 <= rsi < 50:
            delta = -1.5
            reason = f"RSI {rsi:.0f} in bear zone (30-50)"
        elif rsi < 30:
            delta = -0.5
            reason = f"RSI {rsi:.0f} extreme oversold (reversal risk)"
        else:
            delta = 0.0
            reason = f"RSI {rsi:.0f}"

        score += delta
        components.append(ScoreComponent(name="rsi_trend", value=delta, reason=reason))

    # ── EMA CROSSOVER (12/50) ──
    if ind.ema_12 is not None and ind.sma_50 is not None:
        if ind.ema_12 > ind.sma_50:
            delta = 1.0
            reason = "EMA12 > SMA50 (bullish cross)"
        else:
            delta = -1.0
            reason = "EMA12 < SMA50 (bearish cross)"
        score += delta
        components.append(ScoreComponent(name="ema_cross", value=delta, reason=reason))

    # ── MACD CONFIRMATION ──
    # MACD + RSI combined: 73% win rate (QuantifiedStrategies)
    if ind.macd_line is not None and ind.macd_signal is not None and ind.macd_histogram is not None:
        if ind.macd_line > ind.macd_signal and ind.macd_histogram > 0:
            delta = 1.0
            reason = "MACD bullish (line > signal, hist > 0)"
        elif ind.macd_line < ind.macd_signal and ind.macd_histogram < 0:
            delta = -1.0
            reason = "MACD bearish (line < signal, hist < 0)"
        else:
            delta = 0.0
            reason = "MACD mixed"
        score += delta
        components.append(ScoreComponent(name="macd", value=delta, reason=reason))

    # ── BOLLINGER BANDS ──
    # Trending: breakout signals | Ranging: mean reversion
    if ind.bb_lower is not None and ind.bb_upper is not None and current_price > 0:
        if is_trending:
            if current_price > ind.bb_upper:
                delta = 0.5
                reason = "BB breakout above (trend continuation)"
            elif current_price < ind.bb_lower:
                delta = -0.5
                reason = "BB breakout below (trend continuation)"
            else:
                delta = 0.0
                reason = "BB within bands (trending)"
        elif is_ranging:
            if current_price < ind.bb_lower:
                delta = 1.0
                reason = "BB lower touch (mean reversion buy)"
            elif current_price > ind.bb_upper:
                delta = -1.0
                reason = "BB upper touch (mean reversion sell)"
            else:
                delta = 0.0
                reason = "BB within bands (ranging)"
        else:
            delta = 0.0
            reason = "BB neutral (no regime)"

        if delta != 0:
            score += delta
            components.append(ScoreComponent(name="bollinger", value=delta, reason=reason))

    # ── VOLUME CONFIRMATION ──
    if ind.volume_ratio is not None and ind.volume_ratio > 1.5:
        if score > 0:
            delta = 0.5
            reason = f"Volume {ind.volume_ratio:.1f}x confirms bull"
        elif score < 0:
            delta = -0.5
            reason = f"Volume {ind.volume_ratio:.1f}x confirms bear"
        else:
            delta = 0.0
            reason = f"Volume {ind.volume_ratio:.1f}x (no direction to confirm)"

        if delta != 0:
            score += delta
            components.append(ScoreComponent(name="volume", value=delta, reason=reason))

    # ── DAILY TIMEFRAME CONFIRMATION ──
    if ind_d is not None:
        daily_confirms = 0
        if ind_d.rsi_14 is not None:
            if (ind_d.rsi_14 >= 50 and score > 0) or (ind_d.rsi_14 < 50 and score < 0):
                daily_confirms += 1
        if ind_d.macd_histogram is not None:
            if (ind_d.macd_histogram > 0 and score > 0) or (ind_d.macd_histogram < 0 and score < 0):
                daily_confirms += 1

        if daily_confirms >= 2:
            pre_boost = score
            score *= 1.2
            components.append(ScoreComponent(
                name="daily_confirm",
                value=score - pre_boost,
                reason=f"Daily confirms ({daily_confirms} indicators) — 20% boost",
            ))

    # ── REGIME-ADAPTIVE BLENDING ──
    if is_ranging:
        # In ranging markets, blend trend score with mean reversion
        mr_score = 0.0
        if ind.bb_lower is not None and ind.bb_upper is not None and current_price > 0:
            if current_price < ind.bb_lower:
                mr_score += 1.5
            elif current_price > ind.bb_upper:
                mr_score -= 1.5
        if ind.rsi_14 is not None:
            if ind.rsi_14 < 30:
                mr_score += 1.0
            elif ind.rsi_14 > 70:
                mr_score -= 1.0

        pre_blend = score
        score = score * 0.4 + mr_score * 0.6
        if mr_score != 0:
            components.append(ScoreComponent(
                name="regime_blend",
                value=score - pre_blend,
                reason=f"Ranging regime — 40% trend + 60% mean reversion (mr={mr_score:+.1f})",
            ))
    elif is_strong_trend:
        pre_boost = score
        score *= 1.15
        components.append(ScoreComponent(
            name="strong_trend_boost",
            value=score - pre_boost,
            reason="Strong trend (ADX > 35) — 15% boost",
        ))

    # ── MACRO DIRECTION FILTER ──
    # Don't fight the macro trend
    if macro_bullish and score < -1.0:
        pre_dampen = score
        score *= 0.5
        components.append(ScoreComponent(
            name="macro_dampen",
            value=score - pre_dampen,
            reason="Short dampened (macro bull)",
        ))
    elif macro_bearish and score > 1.0:
        pre_dampen = score
        score *= 0.5
        components.append(ScoreComponent(
            name="macro_dampen",
            value=score - pre_dampen,
            reason="Long dampened (macro bear)",
        ))

    # Clamp to [-10, +10] range
    score = max(-10.0, min(10.0, score))
    return score, components
