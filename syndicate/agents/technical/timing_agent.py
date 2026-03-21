"""Technical Timing Agent — 1H entry timing. Real analyst, not classifier."""

from __future__ import annotations
from pathlib import Path
from typing import Any
from syndicate.agents.base import BaseAgent
from syndicate.agents.team_manager import _load_manager_knowledge
from syndicate.data.models import TeamType

_TRADING_KB = _load_manager_knowledge(Path(__file__).parent / "trading_knowledge.md")


class TechnicalTimingAgent(BaseAgent):
    @property
    def team_type(self) -> TeamType:
        return TeamType.TECHNICAL

    @property
    def system_prompt(self) -> str:
        base = (
            "You are an execution trader specializing in 1-HOUR entry timing. "
            "Your job: is the SHORT-TERM momentum right to enter a position NOW?\n\n"
            "You receive raw 1H indicator data. Analyze it — don't classify.\n\n"
            "What you're looking for:\n"
            "- Is short-term momentum building or fading?\n"
            "- Are EMAs crossing or diverging right now?\n"
            "- Is RSI showing immediate overbought/oversold that could reverse?\n"
            "- Is there a micro-pullback in a larger move (entry opportunity)?\n\n"
            "Your conviction will NATURALLY be lower than other agents — 1H signals are noisy.\n"
            "Conviction 4-6 is your normal range. 7+ requires clear 1H momentum.\n"
            "You MUST pick BULLISH or BEARISH."
        )
        if _TRADING_KB:
            base += f"\n=== TRADING KNOWLEDGE ===\n{_TRADING_KB}\n"
        return base

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        indicators_1h = market_data.get("indicators_1h")
        stats = market_data.get("stats_24h", {})

        if indicators_1h is None:
            return f"No 1H data for {self.profile.symbol}. Give conviction 0."

        price = float(stats.get("close", 0))
        prompt = f"Should we enter {self.profile.symbol} RIGHT NOW based on 1H timing?\n\n"
        prompt += f"Price: ${price:,.2f}\n\n"

        prompt += "1H INDICATORS:\n"
        if indicators_1h.ema_12 and indicators_1h.ema_26:
            cross = "ABOVE" if indicators_1h.ema_12 > indicators_1h.ema_26 else "BELOW"
            prompt += f"  EMA12 {cross} EMA26 | EMA12=${indicators_1h.ema_12:,.2f} EMA26=${indicators_1h.ema_26:,.2f}\n"
        if indicators_1h.rsi_14 is not None:
            prompt += f"  RSI(14): {indicators_1h.rsi_14:.1f}\n"
        if indicators_1h.macd_line is not None and indicators_1h.macd_signal is not None:
            prompt += f"  MACD: line={indicators_1h.macd_line:.4f} signal={indicators_1h.macd_signal:.4f} hist={indicators_1h.macd_histogram:+.4f}\n"
        if indicators_1h.volume_ratio is not None:
            prompt += f"  Volume: {indicators_1h.volume_ratio:.2f}x average\n"
        if indicators_1h.sma_20:
            above = "above" if price > indicators_1h.sma_20 else "below"
            prompt += f"  Price is {above} 1H SMA20 (${indicators_1h.sma_20:,.2f})\n"

        prompt += "\nIs the short-term momentum supportive for an entry right now? What's your read?"
        return prompt
