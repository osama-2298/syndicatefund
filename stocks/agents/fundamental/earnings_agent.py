"""
Stock Earnings Agent — earnings surprises, revisions, guidance + BLACKOUT enforcement.

KEY: If in_blackout is True, this agent sets conviction to 0.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class StockEarningsAgent(BaseAgent):
    """Earnings analysis with blackout enforcement."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.FUNDAMENTAL

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Earnings analyst at a stock hedge fund.\n"
            "You analyze earnings history, surprises, and upcoming reports.\n\n"
            "EARNINGS BLACKOUT RULE (CRITICAL):\n"
            "If the data shows 'EARNINGS BLACKOUT ACTIVE', you MUST set conviction to 0.\n"
            "Reason: We NEVER open new positions within 3 days of earnings — binary event risk.\n\n"
            "NORMAL ANALYSIS (when not in blackout):\n"
            "- Beat rate: >75% = consistent outperformer\n"
            "- Average surprise: >5% = earnings upside momentum\n"
            "- Negative surprises: Especially if accelerating → bearish\n"
            "- Days to earnings 4-14: Position for earnings run-up (common bullish drift)\n"
            "- Post-earnings: If just reported a beat, momentum often continues 2-3 weeks\n\n"
            "CONVICTION:\n"
            "- 0: EARNINGS BLACKOUT — mandatory, no exceptions\n"
            "- 9-10: Strong beat history + upcoming earnings catalyst\n"
            "- 7-8: Good earnings track record\n"
            "- 5-6: Mixed earnings history\n"
            "- 3-4: Weak or declining earnings\n"
            "- 1-2: Miss history or negative guidance\n\n"
            "Reference specific earnings data. 2 sentences."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        earnings = market_data.get("earnings")
        stats = market_data.get("stats", {})

        prompt = f"Analyze earnings outlook for {self.profile.symbol}.\n\n"

        if earnings:
            if earnings.in_blackout:
                prompt += "⚠ EARNINGS BLACKOUT ACTIVE ⚠\n"
                prompt += f"Next earnings: {earnings.next_earnings_date} ({earnings.days_to_earnings} days away)\n"
                prompt += "You MUST set conviction to 0. No exceptions.\n"
            else:
                if earnings.next_earnings_date:
                    prompt += f"Next Earnings: {earnings.next_earnings_date} ({earnings.days_to_earnings or '?'} days)\n"
                if earnings.beat_rate is not None:
                    prompt += f"Beat Rate (last 4Q): {earnings.beat_rate:.0%}\n"
                if earnings.avg_surprise_pct is not None:
                    prompt += f"Avg Surprise: {earnings.avg_surprise_pct:+.1f}%\n"
                if earnings.last_surprises:
                    prompt += "Recent quarters:\n"
                    for s in earnings.last_surprises[-4:]:
                        prompt += f"  EPS expected {s.get('expected_eps', '?')} → actual {s.get('actual_eps', '?')} ({s.get('surprise_pct', 0):+.1f}%)\n"
        else:
            prompt += "No earnings data available.\n"

        if stats:
            prompt += f"\nPrice: ${stats.get('close', 0):,.2f}\n"

        prompt += "\nAssess earnings outlook."
        return prompt
