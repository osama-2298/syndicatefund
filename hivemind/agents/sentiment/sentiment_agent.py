"""
Sentiment Analysis Agent.

Architecture follows the virattt/ai-hedge-fund pattern:
- Phase 1: Python computes ALL sentiment scores deterministically
  (fear/greed index, crowd positioning, momentum sentiment, contrarian signals)
- Phase 2: LLM receives pre-computed scores and makes a JUDGMENT call

The LLM never does math. It interprets pre-computed analysis.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType, TechnicalIndicators


def compute_sentiment_scores(
    indicators: TechnicalIndicators,
    stats_24h: dict,
    fear_greed: dict | None = None,
    coingecko_coin: dict | None = None,
    trending: list[dict] | None = None,
    reddit_sentiment: dict | None = None,
) -> dict[str, Any]:
    """
    Pre-compute sentiment analysis scores BEFORE sending to LLM.
    All math happens here. The LLM only interprets results.

    Now uses REAL external sentiment data:
    - Fear & Greed Index (alternative.me)
    - CoinGecko sentiment votes + trending coins
    """
    current_price = float(stats_24h.get("close", 0))
    change_24h = float(stats_24h.get("price_change_pct", 0))
    scores: dict[str, Any] = {"current_price": current_price, "change_24h": change_24h}

    # ── 1. FEAR/GREED SCORE (-1 to +1) ──
    # -1 = extreme fear, +1 = extreme greed
    fg_signals = []

    if indicators.rsi_14 is not None:
        rsi = indicators.rsi_14
        scores["rsi"] = round(rsi, 1)
        # Map RSI to fear/greed: RSI 50 = neutral, RSI 80+ = extreme greed, RSI 20- = extreme fear
        rsi_fg = (rsi - 50) / 50  # Normalize to -1 to +1 range (approx)
        rsi_fg = max(-1.0, min(1.0, rsi_fg))
        fg_signals.append(rsi_fg)

        if rsi > 80:
            scores["rsi_emotion"] = "EXTREME_GREED"
        elif rsi > 70:
            scores["rsi_emotion"] = "GREED"
        elif rsi > 55:
            scores["rsi_emotion"] = "MILD_OPTIMISM"
        elif rsi > 45:
            scores["rsi_emotion"] = "NEUTRAL"
        elif rsi > 30:
            scores["rsi_emotion"] = "MILD_FEAR"
        elif rsi > 20:
            scores["rsi_emotion"] = "FEAR"
        else:
            scores["rsi_emotion"] = "EXTREME_FEAR"

    # 24h price change as crowd emotion proxy
    if change_24h:
        # Large moves = stronger emotion
        if abs(change_24h) > 10:
            emotion_strength = 1.0
        elif abs(change_24h) > 5:
            emotion_strength = 0.7
        elif abs(change_24h) > 2:
            emotion_strength = 0.4
        else:
            emotion_strength = 0.2

        price_fg = emotion_strength if change_24h > 0 else -emotion_strength
        fg_signals.append(price_fg)
        scores["price_emotion_strength"] = round(emotion_strength, 2)

    # ── REAL Fear & Greed Index (alternative.me) ──
    if fear_greed:
        fg_value = fear_greed.get("current_value", 50)
        fg_label = fear_greed.get("current_label", "Neutral")
        fg_trend = fear_greed.get("trend", "STABLE")
        scores["fg_index_value"] = fg_value
        scores["fg_index_label"] = fg_label
        scores["fg_index_trend"] = fg_trend

        # Normalize 0-100 to -1 to +1 (50 = neutral)
        fg_normalized = (fg_value - 50) / 50
        fg_signals.append(fg_normalized * 1.5)  # Weight real F&G heavily

        # Historical trend matters
        history = fear_greed.get("history", [])
        if len(history) >= 3:
            recent_values = [h["value"] for h in history[:3]]
            scores["fg_3day_avg"] = round(sum(recent_values) / 3, 1)

    # ── CoinGecko sentiment votes ──
    if coingecko_coin:
        up_pct = coingecko_coin.get("sentiment_votes_up_pct", 0)
        down_pct = coingecko_coin.get("sentiment_votes_down_pct", 0)
        if up_pct > 0 or down_pct > 0:
            # Normalize: 50% up = neutral, 80% up = bullish, 20% up = bearish
            sentiment_bias = (up_pct - 50) / 50 if up_pct > 0 else 0
            fg_signals.append(sentiment_bias)
            scores["coingecko_sentiment_up"] = round(up_pct, 1)
            scores["coingecko_sentiment_down"] = round(down_pct, 1)

        watchlist = coingecko_coin.get("watchlist_users", 0)
        if watchlist > 0:
            scores["watchlist_users"] = watchlist

    # ── Reddit social sentiment (REAL data) ──
    if reddit_sentiment and reddit_sentiment.get("total_posts", 0) > 0:
        r_ratio = reddit_sentiment.get("sentiment_ratio", 0.5)
        r_engagement = reddit_sentiment.get("engagement_level", "UNKNOWN")
        r_bullish = reddit_sentiment.get("bullish_keywords", 0)
        r_bearish = reddit_sentiment.get("bearish_keywords", 0)

        scores["reddit_sentiment_ratio"] = round(r_ratio, 3)
        scores["reddit_engagement"] = r_engagement
        scores["reddit_bullish_posts"] = r_bullish
        scores["reddit_bearish_posts"] = r_bearish
        scores["reddit_avg_score"] = reddit_sentiment.get("avg_score", 0)
        scores["reddit_avg_comments"] = reddit_sentiment.get("avg_comments", 0)
        scores["reddit_subs_reached"] = reddit_sentiment.get("subreddits_reached", 0)
        scores["reddit_coin_mentions"] = reddit_sentiment.get("coin_mentions", {})

        # Normalize ratio (0.5 = neutral) to -1 to +1
        reddit_signal = (r_ratio - 0.5) * 2
        fg_signals.append(reddit_signal)

        # Top posts for LLM context
        top_posts = reddit_sentiment.get("top_posts", [])
        if top_posts:
            scores["reddit_top_posts"] = top_posts

    # ── Trending status ──
    if trending:
        base_symbol = indicators.symbol.replace("USDT", "")
        is_trending = any(
            t.get("symbol", "").upper() == base_symbol.upper()
            for t in trending
        )
        scores["is_trending"] = is_trending
        if is_trending:
            fg_signals.append(0.3)  # Trending = mild greed signal

    fear_greed_score = sum(fg_signals) / max(len(fg_signals), 1)
    scores["fear_greed_score"] = round(fear_greed_score, 3)
    scores["fear_greed_label"] = (
        "EXTREME_GREED" if fear_greed_score > 0.6 else
        "GREED" if fear_greed_score > 0.3 else
        "MILD_GREED" if fear_greed_score > 0.1 else
        "NEUTRAL" if fear_greed_score > -0.1 else
        "MILD_FEAR" if fear_greed_score > -0.3 else
        "FEAR" if fear_greed_score > -0.6 else
        "EXTREME_FEAR"
    )

    # ── 2. CROWD POSITIONING SCORE (-1 to +1) ──
    # How extended is the crowd? Positive = crowd is long/overextended, negative = crowd is short/capitulated
    crowd_signals = []

    # Price vs SMA200 — how far the crowd has pushed price from long-term mean
    if indicators.sma_200 and current_price:
        pct_from_200 = ((current_price - indicators.sma_200) / indicators.sma_200) * 100
        scores["pct_from_sma200"] = round(pct_from_200, 1)

        # Normalize: 0% = neutral, ±30%+ = extreme
        crowd_extension = max(-1.0, min(1.0, pct_from_200 / 30))
        crowd_signals.append(crowd_extension)

        if pct_from_200 > 30:
            scores["crowd_position"] = "EXTREME_LONG"
        elif pct_from_200 > 10:
            scores["crowd_position"] = "OVEREXTENDED_LONG"
        elif pct_from_200 > -5:
            scores["crowd_position"] = "NEUTRAL"
        elif pct_from_200 > -20:
            scores["crowd_position"] = "FEARFUL_SIDELINED"
        else:
            scores["crowd_position"] = "CAPITULATED"

    # Bollinger Band position — where price sits within volatility envelope
    if indicators.bb_upper and indicators.bb_lower and current_price:
        bb_range = indicators.bb_upper - indicators.bb_lower
        if bb_range > 0:
            bb_position = (current_price - indicators.bb_lower) / bb_range
            scores["bb_position"] = round(bb_position, 3)

            # BB position: 0.5 = neutral, >0.9 = crowd max long, <0.1 = crowd max short
            bb_crowd = (bb_position - 0.5) * 2  # Normalize to -1 to +1
            crowd_signals.append(bb_crowd)

            if bb_position > 0.95:
                scores["bb_crowd"] = "MAX_LONG_TOUCH_UPPER"
            elif bb_position > 0.7:
                scores["bb_crowd"] = "EXTENDED_BULLISH"
            elif bb_position > 0.3:
                scores["bb_crowd"] = "NEUTRAL_ZONE"
            elif bb_position > 0.05:
                scores["bb_crowd"] = "EXTENDED_BEARISH"
            else:
                scores["bb_crowd"] = "MAX_SHORT_TOUCH_LOWER"

    crowd_score = sum(crowd_signals) / max(len(crowd_signals), 1)
    scores["crowd_score"] = round(crowd_score, 3)
    scores["crowd_label"] = (
        "EXTREME_GREED_POSITIONING" if crowd_score > 0.5 else
        "BULLISH_POSITIONING" if crowd_score > 0.15 else
        "NEUTRAL_POSITIONING" if crowd_score > -0.15 else
        "BEARISH_POSITIONING" if crowd_score > -0.5 else
        "EXTREME_FEAR_POSITIONING"
    )

    # ── 3. MOMENTUM SENTIMENT SCORE (-1 to +1) ──
    # Is conviction building or fading? Volume + price direction tells the story.
    momentum_sent_signals = []

    if indicators.volume_ratio is not None:
        vr = indicators.volume_ratio
        scores["volume_ratio"] = round(vr, 2)

        # Volume + direction = conviction
        if vr > 2.0:
            scores["volume_emotion"] = "CLIMACTIC"
            vol_conviction = 1.0
        elif vr > 1.5:
            scores["volume_emotion"] = "ELEVATED"
            vol_conviction = 0.7
        elif vr > 1.0:
            scores["volume_emotion"] = "NORMAL"
            vol_conviction = 0.3
        elif vr > 0.5:
            scores["volume_emotion"] = "LOW_CONVICTION"
            vol_conviction = -0.2
        else:
            scores["volume_emotion"] = "DEAD"
            vol_conviction = -0.5

        # Volume * direction = sentiment momentum
        direction = 1 if change_24h > 0 else -1 if change_24h < 0 else 0
        momentum_sent_signals.append(vol_conviction * direction)

        # Divergence detection
        if vr > 1.5 and change_24h > 0:
            scores["volume_price_dynamic"] = "STRONG_BULLISH_CONVICTION"
        elif vr > 1.5 and change_24h < 0:
            scores["volume_price_dynamic"] = "STRONG_BEARISH_CONVICTION"
        elif vr < 0.7 and change_24h > 0:
            scores["volume_price_dynamic"] = "WEAK_RALLY_DIVERGENCE"
        elif vr < 0.7 and change_24h < 0:
            scores["volume_price_dynamic"] = "SELLING_EXHAUSTION"
        else:
            scores["volume_price_dynamic"] = "NEUTRAL"

    # MACD histogram as momentum shift
    if indicators.macd_histogram is not None:
        hist = indicators.macd_histogram
        scores["macd_histogram"] = round(hist, 4)

        if indicators.macd_line is not None and indicators.macd_signal is not None:
            macd_diff = indicators.macd_line - indicators.macd_signal
            if hist > 0 and macd_diff > 0:
                momentum_sent_signals.append(0.7)
                scores["momentum_shift"] = "BULLISH_ACCELERATING"
            elif hist > 0 and macd_diff <= 0:
                momentum_sent_signals.append(0.3)
                scores["momentum_shift"] = "BEARISH_FADING"
            elif hist < 0 and macd_diff < 0:
                momentum_sent_signals.append(-0.7)
                scores["momentum_shift"] = "BEARISH_ACCELERATING"
            elif hist < 0 and macd_diff >= 0:
                momentum_sent_signals.append(-0.3)
                scores["momentum_shift"] = "BULLISH_FADING"

    momentum_sent_score = sum(momentum_sent_signals) / max(len(momentum_sent_signals), 1)
    scores["momentum_sentiment_score"] = round(momentum_sent_score, 3)
    scores["momentum_sentiment_label"] = (
        "STRONG_BULLISH" if momentum_sent_score > 0.5 else
        "BULLISH" if momentum_sent_score > 0.15 else
        "NEUTRAL" if momentum_sent_score > -0.15 else
        "BEARISH" if momentum_sent_score > -0.5 else
        "STRONG_BEARISH"
    )

    # ── 4. CONTRARIAN SIGNAL SCORE (-1 to +1) ──
    # When sentiment is extreme, the contrarian trade is often correct.
    # Positive = contrarian bullish (crowd is too fearful), Negative = contrarian bearish (crowd is too greedy)
    contrarian_signals = []

    if indicators.rsi_14 is not None:
        rsi = indicators.rsi_14
        if rsi > 80:
            contrarian_signals.append(-0.8)  # Extreme greed → contrarian bearish
            scores["contrarian_rsi"] = "OVERBOUGHT_REVERSAL_RISK"
        elif rsi > 70:
            contrarian_signals.append(-0.4)
            scores["contrarian_rsi"] = "STRETCHED_BULLISH"
        elif rsi < 20:
            contrarian_signals.append(0.8)  # Extreme fear → contrarian bullish
            scores["contrarian_rsi"] = "OVERSOLD_REVERSAL_OPPORTUNITY"
        elif rsi < 30:
            contrarian_signals.append(0.4)
            scores["contrarian_rsi"] = "STRETCHED_BEARISH"
        else:
            scores["contrarian_rsi"] = "NO_EXTREME"

    if indicators.volume_ratio is not None and indicators.volume_ratio > 2.5:
        # Volume climax often marks turning points
        if change_24h > 5:
            contrarian_signals.append(-0.5)  # Blowoff top risk
            scores["contrarian_volume"] = "POTENTIAL_BLOWOFF_TOP"
        elif change_24h < -5:
            contrarian_signals.append(0.5)  # Capitulation bounce potential
            scores["contrarian_volume"] = "POTENTIAL_CAPITULATION_BOTTOM"
        else:
            scores["contrarian_volume"] = "CLIMACTIC_VOLUME_NO_DIRECTION"

    if indicators.bb_upper and indicators.bb_lower and current_price:
        bb_range = indicators.bb_upper - indicators.bb_lower
        if bb_range > 0:
            bb_pos = (current_price - indicators.bb_lower) / bb_range
            if bb_pos > 0.97:
                contrarian_signals.append(-0.6)
                scores["contrarian_bb"] = "UPPER_BAND_PIERCE_REVERSAL_RISK"
            elif bb_pos < 0.03:
                contrarian_signals.append(0.6)
                scores["contrarian_bb"] = "LOWER_BAND_PIERCE_REVERSAL_OPPORTUNITY"
            else:
                scores["contrarian_bb"] = "NO_EXTREME"

    contrarian_score = sum(contrarian_signals) / max(len(contrarian_signals), 1)
    scores["contrarian_score"] = round(contrarian_score, 3)
    scores["contrarian_label"] = (
        "STRONG_CONTRARIAN_BULLISH" if contrarian_score > 0.5 else
        "CONTRARIAN_BULLISH" if contrarian_score > 0.2 else
        "NO_CONTRARIAN_SIGNAL" if contrarian_score > -0.2 else
        "CONTRARIAN_BEARISH" if contrarian_score > -0.5 else
        "STRONG_CONTRARIAN_BEARISH"
    )

    # ── 5. COMPOSITE SENTIMENT SCORE ──
    # Weighted: fear/greed 0.25, crowd positioning 0.20, momentum sentiment 0.30, contrarian 0.25
    weights = {
        "fear_greed": 0.25,
        "crowd": 0.20,
        "momentum_sentiment": 0.30,
        "contrarian": 0.25,
    }

    composite = (
        scores["fear_greed_score"] * weights["fear_greed"]
        + scores["crowd_score"] * weights["crowd"]
        + scores["momentum_sentiment_score"] * weights["momentum_sentiment"]
        + scores["contrarian_score"] * weights["contrarian"]
    )

    total_weight = sum(weights.values())
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


class SentimentAgent(BaseAgent):
    """
    Sentiment analyst — pre-computes sentiment scores in Python, then asks LLM for judgment.
    """

    @property
    def team_type(self) -> TeamType:
        return TeamType.SENTIMENT

    @property
    def system_prompt(self) -> str:
        return (
            "You are a senior sentiment analyst at a quantitative crypto hedge fund.\n\n"
            "You read CROWD PSYCHOLOGY using real data: Fear & Greed Index, Reddit sentiment, "
            "CoinGecko trending, and smart money vs retail positioning.\n\n"
            "YOUR TASK: Predict whether crowd psychology favors HIGHER or LOWER prices.\n"
            "You MUST pick BULLISH or BEARISH. There is no neutral option.\n\n"
            "DIRECTION RULES:\n"
            "- BULLISH if: Fear & Greed is extreme fear (contrarian buy), OR momentum sentiment "
            "is positive with volume confirmation, OR smart money is accumulating.\n"
            "- BEARISH if: Fear & Greed is extreme greed (contrarian sell), OR crowd is "
            "overextended long, OR smart money is distributing.\n"
            "- CONTRARIAN: Extreme fear (F&G < 15) → lean BULLISH (bottoms form in fear). "
            "Extreme greed (F&G > 85) → lean BEARISH (tops form in greed).\n"
            "- When momentum and contrarian conflict, pick the contrarian direction "
            "with lower conviction.\n\n"
            "CONVICTION SCALE:\n"
            "- 9-10: Extreme sentiment reading + multiple confirming sources. Very rare.\n"
            "- 7-8: Clear sentiment direction with Reddit + F&G + smart money aligned.\n"
            "- 5-6: Moderate lean. Some sources agree, some mixed.\n"
            "- 3-4: Slight lean. Sentiment is noisy but one direction slightly favored.\n"
            "- 1-2: No clear read. Pick the direction the composite leans.\n\n"
            "RULES:\n"
            "- Do NOT invent data. Reference provided scores.\n"
            "- Keep reasoning to 2-3 sentences. Explain what the crowd is FEELING.\n"
            "- You read psychology, not charts. What are people afraid of or excited about?"
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        """Build prompt with pre-computed sentiment scores + real external data."""
        indicators: TechnicalIndicators = market_data["indicators"]
        stats_24h: dict = market_data["stats_24h"]
        fear_greed: dict | None = market_data.get("fear_greed")
        coingecko_coin: dict | None = market_data.get("coingecko_coin")
        trending: list[dict] | None = market_data.get("trending")
        reddit_sentiment: dict | None = market_data.get("reddit_sentiment")

        # Phase 1: Pre-compute everything in Python
        scores = compute_sentiment_scores(
            indicators, stats_24h, fear_greed, coingecko_coin, trending, reddit_sentiment
        )

        current_price = scores["current_price"]
        change_24h = scores["change_24h"]

        prompt = (
            f"Read the market sentiment for {self.profile.symbol} and produce a trading signal.\n\n"
            f"=== PRE-COMPUTED SENTIMENT SCORES ===\n"
            f"Current Price: ${current_price:,.2f} | 24h Change: {change_24h:+.2f}%\n\n"
            f"COMPOSITE: {scores['composite_score']:+.3f} ({scores['composite_label']})\n\n"
            f"1. FEAR/GREED SCORE: {scores['fear_greed_score']:+.3f} ({scores['fear_greed_label']})\n"
        )

        if "fg_index_value" in scores:
            prompt += f"   REAL Fear & Greed Index: {scores['fg_index_value']}/100 ({scores['fg_index_label']}) — Trend: {scores.get('fg_index_trend', 'N/A')}\n"
        if "fg_3day_avg" in scores:
            prompt += f"   3-Day F&G Average: {scores['fg_3day_avg']}\n"
        if "coingecko_sentiment_up" in scores:
            prompt += f"   CoinGecko Sentiment: {scores['coingecko_sentiment_up']:.0f}% bullish / {scores['coingecko_sentiment_down']:.0f}% bearish\n"
        if scores.get("is_trending"):
            prompt += f"   TRENDING on CoinGecko (social momentum signal)\n"
        if "reddit_sentiment_ratio" in scores:
            subs_reached = scores.get("reddit_subs_reached", "?")
            prompt += f"   Reddit ({subs_reached} subreddits): {scores['reddit_sentiment_ratio']:.0%} bullish "
            prompt += f"({scores['reddit_bullish_posts']}B / {scores['reddit_bearish_posts']}Be)\n"
            prompt += f"   Engagement: {scores['reddit_engagement']} "
            prompt += f"(avg score: {scores['reddit_avg_score']:.0f}, avg comments: {scores['reddit_avg_comments']:.0f})\n"
            # Show if this specific coin is being mentioned
            coin_mentions = scores.get("reddit_coin_mentions", {})
            base = indicators.symbol.replace("USDT", "")
            if base in coin_mentions:
                prompt += f"   THIS COIN ({base}) mentioned in {coin_mentions[base]} Reddit posts\n"
            # Show top mentioned coins
            if coin_mentions:
                top_mentioned = list(coin_mentions.items())[:5]
                mention_str = ", ".join(f"{c}({n})" for c, n in top_mentioned)
                prompt += f"   Top Reddit mentions: {mention_str}\n"
            top_posts = scores.get("reddit_top_posts", [])
            if top_posts:
                prompt += "   Hot on Reddit:\n"
                for p in top_posts[:3]:
                    prompt += f"     - \"{p['title']}\" ({p['score']}pts, r/{p.get('subreddit', '?')})\n"
        if "rsi" in scores:
            prompt += f"   RSI(14): {scores['rsi']:.1f} — Emotion: {scores.get('rsi_emotion', 'N/A')}\n"
        if "price_emotion_strength" in scores:
            prompt += f"   Price Move Emotion: {'POSITIVE' if change_24h > 0 else 'NEGATIVE'} (strength: {scores['price_emotion_strength']})\n"

        prompt += f"\n2. CROWD POSITIONING SCORE: {scores['crowd_score']:+.3f} ({scores['crowd_label']})\n"
        if "pct_from_sma200" in scores:
            prompt += f"   Price vs SMA200: {scores['pct_from_sma200']:+.1f}% — Position: {scores.get('crowd_position', 'N/A')}\n"
        if "bb_position" in scores:
            prompt += f"   BB Position: {scores['bb_position']:.3f} — Crowd: {scores.get('bb_crowd', 'N/A')}\n"

        prompt += f"\n3. MOMENTUM SENTIMENT SCORE: {scores['momentum_sentiment_score']:+.3f} ({scores['momentum_sentiment_label']})\n"
        if "volume_ratio" in scores:
            prompt += f"   Volume Ratio: {scores['volume_ratio']:.2f}x avg — Emotion: {scores.get('volume_emotion', 'N/A')}\n"
        if "volume_price_dynamic" in scores:
            prompt += f"   Volume/Price Dynamic: {scores['volume_price_dynamic']}\n"
        if "momentum_shift" in scores:
            prompt += f"   MACD Momentum Shift: {scores['momentum_shift']}\n"

        prompt += f"\n4. CONTRARIAN SCORE: {scores['contrarian_score']:+.3f} ({scores['contrarian_label']})\n"
        if "contrarian_rsi" in scores:
            prompt += f"   RSI Contrarian: {scores['contrarian_rsi']}\n"
        if "contrarian_volume" in scores:
            prompt += f"   Volume Contrarian: {scores['contrarian_volume']}\n"
        if "contrarian_bb" in scores:
            prompt += f"   BB Contrarian: {scores['contrarian_bb']}\n"

        # Smart money / derivatives sentiment
        smart_money = market_data.get("smart_money")
        if smart_money:
            prompt += f"\n5. SMART MONEY SIGNALS (Binance Futures):\n"
            prompt += f"   Funding: {smart_money.get('funding_sentiment', 'N/A')} ({smart_money.get('funding_rate_pct', 0):+.4f}%)\n"
            divergence = smart_money.get("divergence", "ALIGNED")
            if divergence != "ALIGNED":
                prompt += f"   DIVERGENCE: {divergence}\n"
            else:
                prompt += f"   Smart money and retail: ALIGNED\n"

        prompt += (
            f"\nApply the DECISION RULES from your instructions to these scores. "
            f"Read the crowd psychology and produce your signal."
        )

        return prompt
