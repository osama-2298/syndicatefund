"""
Technical Trend Agent — analyzes the DAILY (1D) timeframe.

This agent is a REAL ANALYST, not a classifier.
It receives raw indicator values and forms its own thesis.
Python computes the math (RSI, MACD, SMA). The LLM does the ANALYSIS.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType, TechnicalIndicators


class TechnicalTrendAgent(BaseAgent):
    """Daily (1D) trend analysis — the strategic direction."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.TECHNICAL

    @property
    def system_prompt(self) -> str:
        return (
            "You are a senior technical analyst at a crypto hedge fund. "
            "You specialize in DAILY chart analysis — reading the macro trend.\n\n"
            "You receive RAW indicator values. ANALYZE them — form a THESIS.\n\n"
            "Think like a real analyst:\n"
            "- What story do the moving averages tell? Converging, diverging, aligned?\n"
            "- Is RSI showing momentum or exhaustion? Context matters: 55 after coming from 30 "
            "is different from 55 after coming from 80.\n"
            "- What does MACD say about momentum direction AND acceleration?\n"
            "- Is price at a key level relative to SMA200?\n\n"
            "RESEARCH: Golden cross (SMA50 > SMA200) has 81.2% success rate in easing cycles.\n"
            "Death cross is a contrarian BUY in 64% of cases. Median 12mo return after: +89%.\n"
            "Multi-timeframe alignment: 64.7% win rate vs 31% when misaligned.\n\n"
            "VARIANT PERCEPTION: Where might the market be WRONG about the trend?\n"
            "What do you see that consensus might be missing?\n\n"
            "WHAT WOULD INVALIDATE YOUR THESIS? Name the specific level or condition.\n"
            "Example: 'Bullish thesis invalidated if price closes below SMA200 on volume.'\n\n"
            "CONVICTION CALIBRATION:\n"
            "- 9-10: Textbook trend, all MAs aligned, RSI confirms, MACD confirms. Exceptional.\n"
            "- 7-8: Clear trend with strong evidence, minor noise. High confidence setup.\n"
            "- 5-6: Trend visible but some conflicting signals. Good enough to lean.\n"
            "- 3-4: Ambiguous, but one side slightly favored. Low confidence.\n"
            "- 1-2: Genuinely unclear. Picking the direction of last resort.\n\n"
            "You MUST pick BULLISH or BEARISH. Conviction 0 only if data unavailable."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        """Present RAW indicator values for the analyst to interpret."""
        indicators_1d = market_data.get("indicators_1d")
        indicators = market_data.get("indicators")  # 4H fallback
        stats = market_data.get("stats_24h", {})

        ind = indicators_1d or indicators
        if ind is None:
            return f"No indicator data available for {self.profile.symbol}. Give conviction 0."

        current_price = float(stats.get("close", 0))
        change_24h = float(stats.get("price_change_pct", 0))

        prompt = (
            f"Analyze the DAILY trend for {self.profile.symbol}.\n\n"
            f"=== RAW MARKET DATA ===\n"
            f"Current Price: ${current_price:,.2f}\n"
            f"24h Change: {change_24h:+.2f}%\n\n"
        )

        # Moving Averages — the backbone of trend analysis
        prompt += "MOVING AVERAGES:\n"
        if ind.sma_20:
            pct_from_20 = ((current_price - ind.sma_20) / ind.sma_20) * 100 if ind.sma_20 else 0
            prompt += f"  SMA20:  ${ind.sma_20:,.2f} (price is {pct_from_20:+.1f}% from it)\n"
        if ind.sma_50:
            pct_from_50 = ((current_price - ind.sma_50) / ind.sma_50) * 100 if ind.sma_50 else 0
            prompt += f"  SMA50:  ${ind.sma_50:,.2f} (price is {pct_from_50:+.1f}% from it)\n"
        if ind.sma_200:
            pct_from_200 = ((current_price - ind.sma_200) / ind.sma_200) * 100 if ind.sma_200 else 0
            prompt += f"  SMA200: ${ind.sma_200:,.2f} (price is {pct_from_200:+.1f}% from it)\n"
        else:
            prompt += f"  SMA200: not available (insufficient data)\n"

        # MA alignment
        if ind.sma_20 and ind.sma_50 and ind.sma_200:
            if ind.sma_20 > ind.sma_50 > ind.sma_200:
                prompt += f"  MA Stack: SMA20 > SMA50 > SMA200 (bullish golden alignment)\n"
            elif ind.sma_20 < ind.sma_50 < ind.sma_200:
                prompt += f"  MA Stack: SMA20 < SMA50 < SMA200 (bearish death alignment)\n"
            else:
                prompt += f"  MA Stack: mixed/transitioning\n"

        if ind.ema_12 and ind.ema_26:
            prompt += f"  EMA12: ${ind.ema_12:,.2f} | EMA26: ${ind.ema_26:,.2f} "
            prompt += f"({'EMA12 > EMA26 = bullish cross' if ind.ema_12 > ind.ema_26 else 'EMA12 < EMA26 = bearish cross'})\n"

        # RSI — momentum
        prompt += "\nMOMENTUM:\n"
        if ind.rsi_14 is not None:
            prompt += f"  RSI(14): {ind.rsi_14:.1f}\n"
        else:
            prompt += f"  RSI: not available\n"

        # MACD
        if ind.macd_line is not None and ind.macd_signal is not None:
            prompt += f"  MACD Line: {ind.macd_line:.4f}\n"
            prompt += f"  MACD Signal: {ind.macd_signal:.4f}\n"
            if ind.macd_histogram is not None:
                prompt += f"  MACD Histogram: {ind.macd_histogram:+.4f}\n"

        # Volume
        prompt += "\nVOLUME:\n"
        if ind.volume_ratio is not None:
            prompt += f"  Volume Ratio: {ind.volume_ratio:.2f}x average\n"
            quote_vol = stats.get("quote_volume", 0)
            prompt += f"  24h Volume: ${quote_vol:,.0f}\n"

        # Volatility
        prompt += "\nVOLATILITY:\n"
        if ind.atr_14 and current_price:
            atr_pct = (ind.atr_14 / current_price) * 100
            prompt += f"  ATR(14): ${ind.atr_14:,.2f} ({atr_pct:.2f}% of price)\n"
        if ind.bb_upper and ind.bb_lower:
            bb_range = ind.bb_upper - ind.bb_lower
            bb_pos = (current_price - ind.bb_lower) / bb_range if bb_range > 0 else 0.5
            prompt += f"  Bollinger Bands: Upper ${ind.bb_upper:,.2f} | Mid ${ind.bb_middle:,.2f} | Lower ${ind.bb_lower:,.2f}\n"
            prompt += f"  BB Position: {bb_pos:.2f} (0=lower band, 1=upper band)\n"
            if ind.bb_width:
                prompt += f"  BB Width: {ind.bb_width:.4f}\n"

        prompt += (
            f"\n=== YOUR ANALYSIS ===\n"
            f"What is the daily trend telling you? Form a thesis.\n"
            f"Consider: MA alignment, RSI context, MACD momentum, volume confirmation.\n"
            f"Is this a clear trend or ambiguous? What are the risks to your thesis?"
        )

        return prompt
