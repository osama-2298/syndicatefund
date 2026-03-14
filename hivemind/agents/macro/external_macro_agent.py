"""External Macro Agent — reads Polymarket prediction markets and BTC derivatives."""

from __future__ import annotations
from typing import Any
from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class ExternalMacroAgent(BaseAgent):
    @property
    def team_type(self) -> TeamType:
        return TeamType.MACRO

    @property
    def system_prompt(self) -> str:
        return (
            "You read EXTERNAL MACRO: Polymarket prediction markets and BTC derivatives.\n"
            "You MUST pick BULLISH or BEARISH. Conviction 0 if no Polymarket data.\n\n"
            "QUANTITATIVE DECISION RULES:\n"
            "- Polymarket: Fed rate CUT likely (>60%) → BULLISH conviction 7-8\n"
            "- Polymarket: Fed HOLD likely (>80%) → BULLISH conviction 5-6 (neutral-to-positive)\n"
            "- Polymarket: Fed HIKE likely (>30%) → BEARISH conviction 7-8\n"
            "- Polymarket: Recession probability < 25% → add +1 BULLISH\n"
            "- Polymarket: Recession probability > 40% → add +1 BEARISH\n\n"
            "BTC DERIVATIVES MACRO GAUGE:\n"
            "- BTC funding < -0.03% → BULLISH modifier +1 (shorts overcrowded system-wide)\n"
            "- BTC funding > +0.05% → BEARISH modifier +1 (longs overcrowded)\n"
            "- BTC OI rising sharply → leverage building, volatility expected\n\n"
            "VOLUME FILTER: Only trust Polymarket markets with > $1M volume.\n"
            "Markets with < $100K volume are noise. Ignore them.\n\n"
            "RULES: State Fed probability % and recession odds. 2 sentences max."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        pred = market_data.get("prediction_markets", {})
        btc_deriv = market_data.get("btc_derivatives", {})

        prompt = f"Read external macro forces for {self.profile.symbol}.\n\n"

        if pred:
            highlights = pred.get("highlights", [])
            if highlights:
                prompt += "=== POLYMARKET (real money bets) ===\n"
                for m in highlights[:5]:
                    q = m.get("question", "?")[:55]
                    probs = m.get("probabilities", {})
                    vol = m.get("volume", 0)
                    prob_str = " / ".join(f"{k}: {v:.0f}%" for k, v in probs.items() if v > 1)
                    prompt += f"  {q}… → {prob_str} (vol: ${vol:,.0f})\n"

        if btc_deriv:
            funding = btc_deriv.get("funding", {})
            oi = btc_deriv.get("open_interest", {})
            if funding:
                prompt += f"\nBTC Funding: {funding.get('current_rate_pct', 0):+.4f}% — {funding.get('sentiment', '')}\n"
            if oi:
                prompt += f"BTC Open Interest: {oi.get('open_interest', 0):,.0f} contracts\n"

        prompt += "\nPredict external macro direction."
        return prompt
