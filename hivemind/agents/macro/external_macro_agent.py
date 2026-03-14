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
            "You read EXTERNAL MACRO forces: Polymarket prediction markets (Fed rates, recession odds, "
            "crypto regulation) and BTC derivatives as a leverage/risk gauge.\n\n"
            "Your job: predict whether external macro forces are SUPPORTIVE or HOSTILE to crypto.\n"
            "You MUST pick BULLISH (supportive) or BEARISH (hostile).\n\n"
            "KEY SIGNALS:\n"
            "- Polymarket: Fed holding/cutting rates = bullish. Fed hiking = bearish.\n"
            "- Low recession probability (<30%) = bullish. High (>50%) = bearish.\n"
            "- BTC funding negative = shorts crowded = potential squeeze (bullish)\n"
            "- BTC high OI + negative funding = high leverage bearish positioning\n\n"
            "CONVICTION: 9-10 extreme prediction market consensus. 5-6 mixed signals. 1-2 no data.\n"
            "RULES: Polymarket probabilities are REAL MONEY bets. Weight them heavily. 2 sentences."
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
