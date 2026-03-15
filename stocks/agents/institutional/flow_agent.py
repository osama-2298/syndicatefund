"""
Stock Flow Agent — insider buys/sells, short interest, SSR, squeeze risk, borrow cost.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class StockFlowAgent(BaseAgent):
    """Insider flow and short selling analysis."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.INSTITUTIONAL

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Flow analyst at a stock hedge fund.\n"
            "You analyze insider transactions (Form 4), short interest, and squeeze risk.\n\n"
            "INSIDER TRANSACTIONS (strongest signal):\n"
            "- Insider buying > selling (90d) = BULLISH — they know the business best\n"
            "- Cluster buying (multiple insiders) = VERY BULLISH\n"
            "- Insider selling can be routine (stock comp), but cluster selling = warning\n"
            "- CEO/CFO buying > director buying in signal strength\n\n"
            "SHORT INTEREST:\n"
            "- SI% > 20% = heavily shorted → squeeze risk → could go either way\n"
            "- SI% > 10% with rising trend = building bearish conviction\n"
            "- SI% declining = shorts covering → short-term bullish\n"
            "- Days to cover (short ratio) > 5 = squeeze setup\n\n"
            "SSR (Short Sale Restriction):\n"
            "- Active when stock drops >10% from prior close\n"
            "- SSR limits aggressive short selling → reduces downside pressure\n\n"
            "SQUEEZE RISK:\n"
            "- HIGH: SI% > 20% AND days-to-cover > 5 → potential violent squeeze\n"
            "- When squeeze risk is HIGH, direction becomes BULLISH (asymmetric risk)\n\n"
            "CONVICTION: Based on net direction of flow signals.\n"
            "Reference specific data. 2 sentences."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        institutional = market_data.get("institutional")
        short_data = market_data.get("short_data")
        options = market_data.get("options")
        stats = market_data.get("stats", {})

        prompt = f"Analyze flow signals for {self.profile.symbol}.\n\n"

        # Insider transactions
        if institutional:
            prompt += "=== INSIDER TRANSACTIONS (90d) ===\n"
            prompt += f"Buys: {institutional.insider_buys_90d} | Sells: {institutional.insider_sells_90d}\n"
            prompt += f"Net: {institutional.insider_net_shares:+d} shares\n"
            if institutional.notable_insiders:
                prompt += "Notable:\n"
                for ins in institutional.notable_insiders[:3]:
                    prompt += f"  - {ins.get('insider', '?')}: {ins.get('action', '?')} ({ins.get('shares', 0):,} shares)\n"

        # Short selling
        if short_data:
            prompt += "\n=== SHORT INTEREST ===\n"
            if short_data.short_interest_pct:
                prompt += f"SI% of Float: {short_data.short_interest_pct:.1%}\n"
            if short_data.short_ratio:
                prompt += f"Days to Cover: {short_data.short_ratio:.1f}\n"
            prompt += f"Squeeze Risk: {short_data.squeeze_risk}\n"
            if short_data.ssr_active:
                prompt += "⚠ SSR (Short Sale Restriction) ACTIVE\n"
            if short_data.hard_to_borrow:
                prompt += "⚠ HARD TO BORROW\n"

        # Options unusual activity
        if options and options.unusual_activity_flag:
            prompt += "\n⚠ UNUSUAL OPTIONS ACTIVITY DETECTED\n"

        if stats:
            prompt += f"\nPrice: ${stats.get('close', 0):,.2f} ({stats.get('price_change_pct', 0):+.2f}%)\n"

        prompt += "\nAssess the net flow direction."
        return prompt
