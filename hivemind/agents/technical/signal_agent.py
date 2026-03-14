"""
Technical Signal Agent — analyzes the 4-HOUR (4H) timeframe.

REAL ANALYST approach: receives raw indicator values + order book + derivatives.
Forms its own thesis about whether there's a tradable setup right now.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType, TechnicalIndicators


class TechnicalSignalAgent(BaseAgent):
    """4-Hour (4H) signal analysis — the primary trading timeframe."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.TECHNICAL

    @property
    def system_prompt(self) -> str:
        return (
            "You are a senior technical analyst specializing in 4-HOUR chart setups.\n\n"
            "You receive RAW indicators, order book, and derivatives. ANALYZE — don't classify.\n\n"
            "What a great setup analyst looks for:\n"
            "- Is there a SETUP? Breakout, pullback to support, divergence, BB squeeze?\n"
            "- Does volume CONFIRM or is this low-conviction drift?\n"
            "- Order book: heavy bids = support. Heavy asks = resistance. The book doesn't lie.\n"
            "- Derivatives: funding extremes = crowded positioning. Taker flow = urgency.\n"
            "- Research shows: MACD+RSI combined achieves Sharpe 1.0-1.44 vs 0.3 standalone.\n"
            "  Funding < -0.05% has 70-75% bounce probability. Multi-TF alignment: 64.7% win rate.\n\n"
            "VARIANT PERCEPTION: Is the derivatives market seeing something the chart isn't?\n"
            "When funding is very negative but technicals are bullish = squeeze setup.\n\n"
            "WHAT WOULD INVALIDATE: Name the price level or condition.\n"
            "Example: 'Short thesis dies if price breaks above BB upper on volume with positive taker flow.'\n\n"
            "CONVICTION:\n"
            "- 8-10: Clear setup + volume confirms + derivatives confirm. Textbook.\n"
            "- 5-7: Setup present, partial confirmation. Tradeable but risky.\n"
            "- 3-4: No setup, just a lean based on indicator readings.\n"
            "- 0-2: No data or genuinely ambiguous.\n\n"
            "You MUST pick BULLISH or BEARISH."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        indicators = market_data.get("indicators")
        stats = market_data.get("stats_24h", {})
        order_book = market_data.get("order_book")
        derivatives = market_data.get("derivatives")

        if indicators is None:
            return f"No 4H indicators for {self.profile.symbol}. Give conviction 0."

        current_price = float(stats.get("close", 0))
        change_24h = float(stats.get("price_change_pct", 0))

        prompt = (
            f"Is there a tradable setup on {self.profile.symbol} right now?\n\n"
            f"=== 4H CHART DATA ===\n"
            f"Price: ${current_price:,.2f} | 24h: {change_24h:+.2f}%\n\n"
        )

        # Trend indicators
        prompt += "TREND:\n"
        if indicators.sma_20:
            prompt += f"  SMA20: ${indicators.sma_20:,.2f} | SMA50: ${indicators.sma_50:,.2f if indicators.sma_50 else 'N/A'}\n"
        if indicators.ema_12 and indicators.ema_26:
            cross = "EMA12 ABOVE EMA26 (bullish)" if indicators.ema_12 > indicators.ema_26 else "EMA12 BELOW EMA26 (bearish)"
            prompt += f"  {cross} | EMA12=${indicators.ema_12:,.2f} EMA26=${indicators.ema_26:,.2f}\n"

        # Momentum
        prompt += "\nMOMENTUM:\n"
        if indicators.rsi_14 is not None:
            prompt += f"  RSI(14): {indicators.rsi_14:.1f}\n"
        if indicators.macd_line is not None and indicators.macd_signal is not None:
            prompt += f"  MACD: line={indicators.macd_line:.4f} signal={indicators.macd_signal:.4f} histogram={indicators.macd_histogram:+.4f}\n"

        # Volume
        prompt += "\nVOLUME:\n"
        if indicators.volume_ratio is not None:
            prompt += f"  Volume Ratio: {indicators.volume_ratio:.2f}x average\n"
            prompt += f"  24h Volume: ${stats.get('quote_volume', 0):,.0f}\n"

        # Volatility
        if indicators.bb_upper and indicators.bb_lower:
            bb_range = indicators.bb_upper - indicators.bb_lower
            bb_pos = (current_price - indicators.bb_lower) / bb_range if bb_range > 0 else 0.5
            prompt += f"\nBOLLINGER BANDS:\n"
            prompt += f"  Upper: ${indicators.bb_upper:,.2f} | Mid: ${indicators.bb_middle:,.2f} | Lower: ${indicators.bb_lower:,.2f}\n"
            prompt += f"  Price Position: {bb_pos:.2f} (0=lower, 0.5=middle, 1=upper)\n"
            if indicators.bb_width:
                prompt += f"  Width: {indicators.bb_width:.4f} ({'SQUEEZE — breakout likely' if indicators.bb_width < 2 else 'WIDE — high volatility' if indicators.bb_width > 8 else 'normal'})\n"

        if indicators.atr_14 and current_price:
            prompt += f"\nATR(14): ${indicators.atr_14:,.2f} ({indicators.atr_14/current_price*100:.2f}% of price)\n"

        # Order book depth
        if order_book:
            prompt += f"\nORDER BOOK (live):\n"
            prompt += f"  Bid Value: ${order_book['bid_value_usd']:,.0f} | Ask Value: ${order_book['ask_value_usd']:,.0f}\n"
            prompt += f"  Bid/Ask Ratio: {order_book['bid_ratio']:.3f} ({order_book['pressure']})\n"
            prompt += f"  Spread: {order_book['spread_pct']:.4f}%\n"

        # Derivatives
        if derivatives:
            prompt += f"\nDERIVATIVES (live):\n"
            funding = derivatives.get("funding")
            if funding:
                prompt += f"  Funding Rate: {funding.get('current_rate_pct', 0):+.4f}% ({funding.get('sentiment', 'N/A')})\n"
            oi = derivatives.get("open_interest")
            if oi:
                prompt += f"  Open Interest: {oi.get('open_interest', 0):,.2f} contracts\n"
            taker = derivatives.get("taker_volume")
            if taker:
                prompt += f"  Taker Buy/Sell: {taker.get('buy_sell_ratio', 1):.4f} ({taker.get('signal', 'N/A')})\n"
            top_ls = derivatives.get("top_trader_ls")
            if top_ls:
                prompt += f"  Top Traders: {top_ls.get('long_pct', 50):.1f}% long / {top_ls.get('short_pct', 50):.1f}% short\n"
            divergence = derivatives.get("smart_money_divergence")
            if divergence and divergence not in ("ALIGNED", None):
                prompt += f"  SMART MONEY DIVERGENCE: {divergence}\n"

        prompt += (
            f"\n=== YOUR ANALYSIS ===\n"
            f"Is there a setup here? Breakout? Pullback? Divergence? Or nothing?\n"
            f"Does volume and derivatives CONFIRM or CONTRADICT the chart?\n"
            f"What's your thesis and what's the risk?"
        )

        return prompt
