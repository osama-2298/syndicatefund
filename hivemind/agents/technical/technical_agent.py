"""
Technical Analysis Agent.

Architecture follows the virattt/ai-hedge-fund pattern:
- Phase 1: Python computes ALL scores deterministically (trend, momentum, volatility, volume)
- Phase 2: LLM receives pre-computed scores and makes a JUDGMENT call

The LLM never does math. It interprets pre-computed analysis.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType, TechnicalIndicators


def compute_technical_scores(indicators: TechnicalIndicators, stats_24h: dict) -> dict[str, Any]:
    """
    Pre-compute technical analysis scores BEFORE sending to LLM.
    All math happens here. The LLM only interprets results.

    Returns a dict with scored assessments for each dimension.
    """
    current_price = float(stats_24h.get("close", 0))
    scores: dict[str, Any] = {"current_price": current_price}

    # ── 1. TREND SCORE (-1 to +1) ──
    trend_signals = []

    # Price vs moving averages
    if indicators.sma_20 and current_price:
        trend_signals.append(1 if current_price > indicators.sma_20 else -1)
    if indicators.sma_50 and current_price:
        trend_signals.append(1 if current_price > indicators.sma_50 else -1)
    if indicators.sma_200 and current_price:
        trend_signals.append(1 if current_price > indicators.sma_200 else -1)

    # EMA alignment (fast above slow = bullish)
    if indicators.ema_12 and indicators.ema_26:
        trend_signals.append(1 if indicators.ema_12 > indicators.ema_26 else -1)

    # MA stack alignment (20 > 50 > 200 = strong uptrend)
    if indicators.sma_20 and indicators.sma_50 and indicators.sma_200:
        if indicators.sma_20 > indicators.sma_50 > indicators.sma_200:
            trend_signals.append(1)
            scores["ma_alignment"] = "BULLISH_STACK"
        elif indicators.sma_20 < indicators.sma_50 < indicators.sma_200:
            trend_signals.append(-1)
            scores["ma_alignment"] = "BEARISH_STACK"
        else:
            scores["ma_alignment"] = "MIXED"

    trend_score = sum(trend_signals) / max(len(trend_signals), 1)
    scores["trend_score"] = round(trend_score, 3)
    scores["trend_label"] = "BULLISH" if trend_score > 0.3 else "BEARISH" if trend_score < -0.3 else "NEUTRAL"

    # ── 2. MOMENTUM SCORE (-1 to +1) ──
    momentum_signals = []

    if indicators.rsi_14 is not None:
        rsi = indicators.rsi_14
        scores["rsi"] = round(rsi, 1)
        if rsi > 70:
            momentum_signals.append(-0.5)  # Overbought, negative for momentum continuation
            scores["rsi_zone"] = "OVERBOUGHT"
        elif rsi < 30:
            momentum_signals.append(0.5)  # Oversold, positive for mean reversion
            scores["rsi_zone"] = "OVERSOLD"
        elif rsi > 55:
            momentum_signals.append(0.3)
            scores["rsi_zone"] = "BULLISH"
        elif rsi < 45:
            momentum_signals.append(-0.3)
            scores["rsi_zone"] = "BEARISH"
        else:
            scores["rsi_zone"] = "NEUTRAL"

    if indicators.macd_line is not None and indicators.macd_signal is not None:
        # MACD above signal = bullish
        macd_diff = indicators.macd_line - indicators.macd_signal
        scores["macd_crossover"] = "BULLISH" if macd_diff > 0 else "BEARISH"
        scores["macd_histogram"] = round(indicators.macd_histogram or 0, 4)
        momentum_signals.append(1 if macd_diff > 0 else -1)

        # Histogram direction (accelerating or decelerating)
        if indicators.macd_histogram is not None:
            if indicators.macd_histogram > 0:
                scores["macd_momentum"] = "ACCELERATING_BULLISH"
            else:
                scores["macd_momentum"] = "DECELERATING" if macd_diff > 0 else "ACCELERATING_BEARISH"

    momentum_score = sum(momentum_signals) / max(len(momentum_signals), 1)
    scores["momentum_score"] = round(momentum_score, 3)
    scores["momentum_label"] = "BULLISH" if momentum_score > 0.2 else "BEARISH" if momentum_score < -0.2 else "NEUTRAL"

    # ── 3. VOLATILITY SCORE ──
    if indicators.bb_upper and indicators.bb_lower and current_price:
        bb_range = indicators.bb_upper - indicators.bb_lower
        if bb_range > 0:
            bb_position = (current_price - indicators.bb_lower) / bb_range
            scores["bb_position"] = round(bb_position, 3)
            if bb_position > 0.95:
                scores["bb_zone"] = "UPPER_BAND_TOUCH"
            elif bb_position < 0.05:
                scores["bb_zone"] = "LOWER_BAND_TOUCH"
            elif bb_position > 0.8:
                scores["bb_zone"] = "UPPER_ZONE"
            elif bb_position < 0.2:
                scores["bb_zone"] = "LOWER_ZONE"
            else:
                scores["bb_zone"] = "MIDDLE"

    if indicators.bb_width is not None:
        scores["bb_width"] = round(indicators.bb_width, 4)
        scores["volatility_state"] = (
            "EXPANDING" if indicators.bb_width > 6 else
            "CONTRACTING" if indicators.bb_width < 3 else
            "NORMAL"
        )

    if indicators.atr_14 and current_price:
        atr_pct = (indicators.atr_14 / current_price) * 100
        scores["atr_pct"] = round(atr_pct, 3)

    # ── 4. VOLUME SCORE (-1 to +1) ──
    volume_signals = []

    if indicators.volume_ratio is not None:
        vr = indicators.volume_ratio
        scores["volume_ratio"] = round(vr, 2)
        change_24h = float(stats_24h.get("price_change_pct", 0))

        # Volume confirms direction
        if vr > 1.5 and change_24h > 0:
            volume_signals.append(1)  # High volume up = strong bullish
            scores["volume_confirmation"] = "STRONG_BULLISH"
        elif vr > 1.5 and change_24h < 0:
            volume_signals.append(-1)  # High volume down = strong bearish
            scores["volume_confirmation"] = "STRONG_BEARISH"
        elif vr < 0.7 and change_24h > 0:
            volume_signals.append(-0.3)  # Low volume up = weak, bearish divergence
            scores["volume_confirmation"] = "WEAK_BULLISH_DIVERGENCE"
        elif vr < 0.7 and change_24h < 0:
            volume_signals.append(0.3)  # Low volume down = selling exhaustion
            scores["volume_confirmation"] = "SELLING_EXHAUSTION"
        else:
            scores["volume_confirmation"] = "NEUTRAL"

    volume_score = sum(volume_signals) / max(len(volume_signals), 1)
    scores["volume_score"] = round(volume_score, 3)

    # ── 5. COMPOSITE SCORE ──
    # Weighted average matching virattt pattern
    weights = {"trend": 0.30, "momentum": 0.25, "volatility": 0.0, "volume": 0.20}
    # Volatility informs position sizing, not direction — weight = 0

    composite = (
        scores["trend_score"] * weights["trend"]
        + scores["momentum_score"] * weights["momentum"]
        + scores["volume_score"] * weights["volume"]
    )

    # Normalize to -1 to +1 range
    total_weight = weights["trend"] + weights["momentum"] + weights["volume"]
    if total_weight > 0:
        composite = composite / total_weight

    scores["composite_score"] = round(composite, 3)
    scores["composite_label"] = (
        "STRONG_BULLISH" if composite > 0.5 else
        "BULLISH" if composite > 0.15 else
        "BEARISH" if composite < -0.15 else
        "STRONG_BEARISH" if composite < -0.5 else
        "NEUTRAL"
    )

    return scores


class TechnicalAgent(BaseAgent):
    """
    Technical analyst — pre-computes scores in Python, then asks LLM for judgment.
    """

    @property
    def team_type(self) -> TeamType:
        return TeamType.TECHNICAL

    @property
    def system_prompt(self) -> str:
        return (
            "You are a senior technical analyst at a quantitative crypto hedge fund.\n\n"
            "You will receive PRE-COMPUTED technical scores. All math is already done.\n"
            "Your job: PREDICT whether the price will go HIGHER or LOWER.\n\n"
            "YOU MUST PICK A DIRECTION. There is no neutral option.\n"
            "If signals are mixed, pick the direction the composite score leans toward "
            "and give low conviction (1-3).\n\n"
            "DIRECTION RULES:\n"
            "- BULLISH if composite_score > 0 OR if at least 2 of 3 sub-scores are positive.\n"
            "- BEARISH if composite_score < 0 OR if at least 2 of 3 sub-scores are negative.\n"
            "- If composite is near zero, pick based on whichever sub-score has the strongest signal.\n\n"
            "CONVICTION SCALE:\n"
            "- 9-10: All sub-scores strongly aligned. Textbook setup. Extremely rare.\n"
            "- 7-8: Most sub-scores agree. Strong setup with minor conflicts.\n"
            "- 5-6: Clear lean but some opposing signals. Moderate edge.\n"
            "- 3-4: Slight lean. Mixed signals but one direction slightly favored.\n"
            "- 1-2: Essentially a coin flip. You barely lean one way.\n\n"
            "Out of 100 similar setups with these exact scores, estimate how many would "
            "move in your predicted direction. 70/100 → conviction 7. 55/100 → conviction 5.\n\n"
            "RULES:\n"
            "- Do NOT invent data. Only reference provided scores.\n"
            "- Do NOT do math. Scores are pre-computed.\n"
            "- Keep reasoning to 2-3 sentences.\n"
            "- When sub-scores conflict, pick the stronger signal's direction with low conviction."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        """Build prompt with pre-computed scores + multi-timeframe alignment."""
        indicators: TechnicalIndicators = market_data["indicators"]
        stats_24h: dict = market_data["stats_24h"]
        indicators_1h = market_data.get("indicators_1h")
        indicators_1d = market_data.get("indicators_1d")

        # Phase 1: Pre-compute primary (4H) scores
        scores = compute_technical_scores(indicators, stats_24h)

        current_price = scores["current_price"]
        change_24h = float(stats_24h.get("price_change_pct", 0))

        prompt = (
            f"Predict the price direction for {self.profile.symbol}.\n\n"
            f"=== PRE-COMPUTED TECHNICAL SCORES ===\n"
            f"Current Price: ${current_price:,.2f} | 24h Change: {change_24h:+.2f}%\n\n"
            f"COMPOSITE: {scores['composite_score']:+.3f} ({scores['composite_label']})\n\n"
            f"1. TREND SCORE: {scores['trend_score']:+.3f} ({scores['trend_label']})\n"
        )

        if "ma_alignment" in scores:
            prompt += f"   MA Stack: {scores['ma_alignment']}\n"
        if indicators.sma_20:
            prompt += f"   Price vs SMA20: {'ABOVE' if current_price > indicators.sma_20 else 'BELOW'} (${indicators.sma_20:,.2f})\n"
        if indicators.sma_50:
            prompt += f"   Price vs SMA50: {'ABOVE' if current_price > indicators.sma_50 else 'BELOW'} (${indicators.sma_50:,.2f})\n"
        if indicators.sma_200:
            prompt += f"   Price vs SMA200: {'ABOVE' if current_price > indicators.sma_200 else 'BELOW'} (${indicators.sma_200:,.2f})\n"

        prompt += f"\n2. MOMENTUM SCORE: {scores['momentum_score']:+.3f} ({scores['momentum_label']})\n"
        if "rsi" in scores:
            prompt += f"   RSI(14): {scores['rsi']:.1f} [{scores['rsi_zone']}]\n"
        if "macd_crossover" in scores:
            prompt += f"   MACD Crossover: {scores['macd_crossover']}\n"
        if "macd_momentum" in scores:
            prompt += f"   MACD Momentum: {scores['macd_momentum']}\n"
        if "macd_histogram" in scores:
            prompt += f"   MACD Histogram: {scores['macd_histogram']:+.4f}\n"

        prompt += f"\n3. VOLUME SCORE: {scores['volume_score']:+.3f}\n"
        if "volume_ratio" in scores:
            prompt += f"   Volume Ratio: {scores['volume_ratio']:.2f}x avg\n"
        if "volume_confirmation" in scores:
            prompt += f"   Confirmation: {scores['volume_confirmation']}\n"

        prompt += "\n4. VOLATILITY:\n"
        if "bb_zone" in scores:
            prompt += f"   BB Zone: {scores['bb_zone']} (position: {scores.get('bb_position', 'N/A')})\n"
        if "volatility_state" in scores:
            prompt += f"   BB State: {scores['volatility_state']}\n"
        if "atr_pct" in scores:
            prompt += f"   ATR/Price: {scores['atr_pct']:.3f}%\n"

        # Order book pressure (real-time buy/sell imbalance)
        order_book = market_data.get("order_book")
        if order_book:
            prompt += f"\n5. ORDER BOOK DEPTH (live Binance data):\n"
            prompt += f"   Bid/Ask Ratio: {order_book['bid_ratio']:.3f} — {order_book['pressure']}\n"
            prompt += f"   Bid Value: ${order_book['bid_value_usd']:,.0f} | Ask Value: ${order_book['ask_value_usd']:,.0f}\n"
            prompt += f"   Spread: {order_book['spread_pct']:.4f}%\n"

        # Derivatives data (funding rates, open interest, taker flow)
        derivatives = market_data.get("derivatives")
        if derivatives:
            prompt += f"\n6. DERIVATIVES (live Binance Futures):\n"
            funding = derivatives.get("funding")
            if funding:
                prompt += f"   Funding Rate: {funding.get('current_rate_pct', 0):+.4f}% — {funding.get('sentiment', 'N/A')}\n"
            oi = derivatives.get("open_interest")
            if oi:
                prompt += f"   Open Interest: {oi.get('open_interest', 0):,.2f} contracts\n"
            taker = derivatives.get("taker_volume")
            if taker:
                prompt += f"   Taker Buy/Sell: {taker.get('buy_sell_ratio', 1):.4f} — {taker.get('signal', 'N/A')}\n"
            top_ls = derivatives.get("top_trader_ls")
            if top_ls:
                prompt += f"   Top Traders: {top_ls.get('long_pct', 50):.1f}% long / {top_ls.get('short_pct', 50):.1f}% short — {top_ls.get('signal', 'N/A')}\n"
            divergence = derivatives.get("smart_money_divergence")
            if divergence and divergence != "ALIGNED":
                prompt += f"   SMART MONEY DIVERGENCE: {divergence}\n"

        # Multi-timeframe alignment (Elder's Triple Screen)
        tf_bullish = 0
        tf_bearish = 0
        tf_summary = []

        # Daily (1D) — trend direction
        if indicators_1d:
            d_trend = "BULLISH" if (indicators_1d.sma_50 and indicators_1d.sma_200 and indicators_1d.sma_50 > indicators_1d.sma_200) else "BEARISH" if (indicators_1d.sma_50 and indicators_1d.sma_200 and indicators_1d.sma_50 < indicators_1d.sma_200) else "MIXED"
            d_rsi = f"RSI {indicators_1d.rsi_14:.0f}" if indicators_1d.rsi_14 else "RSI N/A"
            d_macd = "MACD+" if (indicators_1d.macd_line and indicators_1d.macd_signal and indicators_1d.macd_line > indicators_1d.macd_signal) else "MACD-" if (indicators_1d.macd_line and indicators_1d.macd_signal) else "MACD N/A"
            tf_summary.append(f"Daily(1D): {d_trend} | {d_rsi} | {d_macd}")
            if d_trend == "BULLISH":
                tf_bullish += 1
            elif d_trend == "BEARISH":
                tf_bearish += 1

        # 4H — signal (already detailed above, summarize alignment)
        h4_trend = "BULLISH" if scores.get("trend_score", 0) > 0 else "BEARISH"
        tf_summary.append(f"4-Hour(4H): {h4_trend} | composite {scores['composite_score']:+.3f}")
        if h4_trend == "BULLISH":
            tf_bullish += 1
        else:
            tf_bearish += 1

        # Hourly (1H) — entry timing
        if indicators_1h:
            h1_trend = "BULLISH" if (indicators_1h.ema_12 and indicators_1h.ema_26 and indicators_1h.ema_12 > indicators_1h.ema_26) else "BEARISH" if (indicators_1h.ema_12 and indicators_1h.ema_26) else "MIXED"
            h1_rsi = f"RSI {indicators_1h.rsi_14:.0f}" if indicators_1h.rsi_14 else "RSI N/A"
            tf_summary.append(f"Hourly(1H): {h1_trend} | {h1_rsi}")
            if h1_trend == "BULLISH":
                tf_bullish += 1
            elif h1_trend == "BEARISH":
                tf_bearish += 1

        total_tf = tf_bullish + tf_bearish
        if total_tf > 0:
            alignment_pct = max(tf_bullish, tf_bearish) / total_tf
            if alignment_pct >= 0.9:
                alignment_read = "FULLY ALIGNED"
            elif alignment_pct >= 0.66:
                alignment_read = "MOSTLY ALIGNED"
            else:
                alignment_read = "CONFLICTING"
            alignment_dir = "BULLISH" if tf_bullish > tf_bearish else "BEARISH"

            prompt += f"\n7. MULTI-TIMEFRAME ALIGNMENT (Elder Triple Screen):\n"
            for s in tf_summary:
                prompt += f"   {s}\n"
            prompt += f"   Alignment: {tf_bullish}B/{tf_bearish}Be = {alignment_read} {alignment_dir}\n"
            prompt += f"   NOTE: When all timeframes agree, increase conviction. When they conflict, reduce it.\n"

        prompt += f"\nPredict the price direction and your conviction level."

        return prompt
