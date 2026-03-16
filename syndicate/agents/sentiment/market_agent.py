"""Market Sentiment Agent — Fear & Greed + crowd positioning. REAL ANALYST with historical data."""

from __future__ import annotations
from typing import Any
from syndicate.agents.base import BaseAgent
from syndicate.data.models import TeamType, TechnicalIndicators
from syndicate.agents.sentiment.sentiment_agent import compute_sentiment_scores


class MarketSentimentAgent(BaseAgent):
    @property
    def team_type(self) -> TeamType:
        return TeamType.SENTIMENT

    @property
    def system_prompt(self) -> str:
        return (
            "You are a market psychologist at a crypto hedge fund, backed by historical data.\n\n"
            "HISTORICAL EVIDENCE (research-backed, from 2018-2026):\n"
            "- F&G 0-10: Sharpe 8.0. Avg 12mo return +440%. ALWAYS preceded major rallies.\n"
            "  COVID F&G=9 → +1,500% 12mo. FTX F&G=6 → +85% 12mo.\n"
            "- F&G 10-20: Positive 30-day return 80% of the time. Median 90-day +32%.\n"
            "- F&G 80-90: 70% chance of >20% drawdown within 90 days.\n"
            "- Fear-weighted DCA: +1,145% over 7 years vs +202% standard DCA.\n"
            "- ONE EXCEPTION: June 2022 (ACTIVE Luna contagion — signal was 5 months early).\n\n"
            "VARIANT PERCEPTION: When the crowd is terrified but price structure is intact\n"
            "(above SMA200), the market is WRONG about the risk. This is where alpha lives.\n"
            "When the crowd is euphoric (F&G > 80) and everyone thinks 'this time is different',\n"
            "the market is WRONG about the upside.\n\n"
            "ANALYZE F&G in CONTEXT:\n"
            "- F&G 16 with BTC above SMA200 = STRONG contrarian buy (structure intact despite fear)\n"
            "- F&G 16 with BTC 50% below SMA200 = fear may be justified (check for contagion)\n"
            "- F&G 80 with declining volume = distribution forming, smart money exiting\n\n"
            "WHAT WOULD INVALIDATE: 'Contrarian buy invalid if exchange/protocol failure is ONGOING.'\n\n"
            "You MUST pick BULLISH or BEARISH. Conviction 0 only if F&G unavailable."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        indicators = market_data.get("indicators")
        stats = market_data.get("stats_24h", {})
        fear_greed = market_data.get("fear_greed")

        prompt = f"Read market psychology for {self.profile.symbol}.\n\n"

        # Fear & Greed — the primary input
        if fear_greed:
            val = fear_greed["current_value"]
            label = fear_greed["current_label"]
            trend = fear_greed.get("trend", "?")
            hours = fear_greed.get("hours_since_update")
            stale = fear_greed.get("is_stale", False)

            prompt += f"=== FEAR & GREED INDEX ===\n"
            prompt += f"Current: {val}/100 ({label})\n"
            prompt += f"Trend: {trend}\n"
            if hours:
                prompt += f"Data age: {hours:.0f} hours"
                if stale:
                    prompt += " (STALE — more than 24h old)"
                prompt += "\n"

            history = fear_greed.get("history", [])
            if len(history) >= 3:
                recent = [h["value"] for h in history[:3]]
                prompt += f"Last 3 readings: {recent}\n"
        else:
            prompt += "** NO Fear & Greed data available. **\n"

        # Market-derived emotion from indicators
        if indicators:
            prompt += f"\n=== MARKET EMOTION INDICATORS ===\n"
            price = float(stats.get("close", 0))
            change = float(stats.get("price_change_pct", 0))
            prompt += f"Price: ${price:,.2f} | 24h Change: {change:+.2f}%\n"

            if indicators.rsi_14 is not None:
                prompt += f"RSI(14): {indicators.rsi_14:.1f}"
                if indicators.rsi_14 > 70:
                    prompt += " — OVERBOUGHT (crowd is greedy)"
                elif indicators.rsi_14 < 30:
                    prompt += " — OVERSOLD (crowd is fearful)"
                else:
                    prompt += " — neutral zone"
                prompt += "\n"

            if indicators.volume_ratio is not None:
                prompt += f"Volume: {indicators.volume_ratio:.2f}x average"
                if indicators.volume_ratio > 2:
                    prompt += " — CLIMACTIC (emotional extreme)"
                elif indicators.volume_ratio > 1.5:
                    prompt += " — elevated (crowd is paying attention)"
                elif indicators.volume_ratio < 0.7:
                    prompt += " — quiet (crowd is apathetic)"
                prompt += "\n"

            if indicators.sma_200 and price:
                pct = ((price - indicators.sma_200) / indicators.sma_200) * 100
                prompt += f"Price vs SMA200: {pct:+.1f}% — "
                if pct > 30:
                    prompt += "crowd is euphoric (far above mean)"
                elif pct > 0:
                    prompt += "above long-term mean (cautiously optimistic)"
                elif pct > -20:
                    prompt += "below mean (crowd is nervous)"
                else:
                    prompt += "deep below mean (crowd has capitulated)"
                prompt += "\n"

        prompt += (
            f"\n=== YOUR ANALYSIS ===\n"
            f"What is the market FEELING right now? Fear? Greed? Apathy?\n"
            f"Is this an extreme that historically reverses? Or is the crowd right?\n"
            f"Consider: is the fear from a RESOLVED cause or is something still unfolding?"
        )

        return prompt
