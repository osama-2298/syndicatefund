"""External Macro Agent — Polymarket + BTC derivatives. REAL ANALYST."""

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
            "You are an external macro analyst at a crypto hedge fund. "
            "You read PREDICTION MARKETS (Polymarket) and BTC derivatives for macro signals.\n\n"
            "Polymarket data is REAL MONEY. These are not polls — people have their capital at risk.\n"
            "When $100M says the Fed will hold rates, that's more reliable than any analyst opinion.\n\n"
            "THINK like a macro strategist:\n"
            "- Fed rate decisions move ALL risk assets. Cuts = bullish. Hikes = bearish. Hold = neutral-to-positive.\n"
            "- Recession probability: <25% = tailwind. 25-40% = headwind. >40% = strong headwind.\n"
            "- BTC derivatives as SYSTEM-WIDE leverage gauge:\n"
            "  Very negative funding = system is short, squeeze risk = bullish for crypto.\n"
            "  Very positive funding = system is long, liquidation risk = bearish.\n"
            "  High OI = lots of leverage in the system = volatility incoming.\n\n"
            "VOLUME FILTER: Only trust Polymarket markets with >$1M volume.\n"
            "Low-volume markets are noise — ignore them.\n\n"
            "You MUST pick BULLISH or BEARISH. Conviction 0 if no Polymarket data."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        pred = market_data.get("prediction_markets", {})
        btc_deriv = market_data.get("btc_derivatives", {})

        prompt = f"What are external macro forces saying about {self.profile.symbol}?\n\n"

        if pred:
            highlights = pred.get("highlights", [])
            if highlights:
                prompt += "=== POLYMARKET — REAL MONEY PREDICTIONS ===\n"
                for m in highlights[:7]:
                    q = m.get("question", m.get("event_title", "?"))
                    if len(q) > 70:
                        q = q[:69] + "…"
                    probs = m.get("probabilities", {})
                    vol = m.get("volume", 0)
                    prob_str = " / ".join(f"{k}: {v:.0f}%" for k, v in probs.items() if v > 1)
                    vol_str = f"${vol:,.0f}" if vol > 0 else "low volume"
                    prompt += f"  {q}\n    → {prob_str} (volume: {vol_str})\n\n"
        else:
            prompt += "** No Polymarket data available. **\n"

        if btc_deriv:
            prompt += "=== BTC DERIVATIVES (system-wide leverage gauge) ===\n"
            funding = btc_deriv.get("funding", {})
            oi = btc_deriv.get("open_interest", {})
            if funding:
                rate = funding.get("current_rate_pct", 0)
                prompt += f"BTC Funding Rate: {rate:+.4f}% — {funding.get('sentiment', '')}\n"
            if oi:
                prompt += f"BTC Open Interest: {oi.get('open_interest', 0):,.0f} contracts\n"

        prompt += "\nAre external forces supportive or hostile to crypto? Form your thesis."
        return prompt
