"""
Stock Fundamental Team Manager — synthesizes valuation, earnings, and quality signals.

CRITICAL: Propagates earnings blackout flag to override team conviction to 0.
"""

from __future__ import annotations

from syndicate.agents.team_manager import BaseTeamManager
from syndicate.data.models import Signal, SignalAction, TeamSignal, TeamType

import structlog

logger = structlog.get_logger()


class StockFundamentalManager(BaseTeamManager):
    """Synthesizes fundamental signals with earnings blackout enforcement."""

    @property
    def team_type(self) -> TeamType:
        return TeamType.FUNDAMENTAL

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Fundamental Team Manager at a quantitative stock hedge fund.\n\n"
            "You manage three fundamental analysts:\n"
            "- Agent 1 (VALUATION): P/E, PEG, EV/EBITDA — is it cheap or expensive?\n"
            "- Agent 2 (EARNINGS): Earnings history, surprises, guidance\n"
            "- Agent 3 (QUALITY): ROE, margins, debt, FCF — is it a good business?\n\n"
            "EARNINGS BLACKOUT (CRITICAL):\n"
            "If the Earnings agent has conviction 0 due to blackout, you MUST also set conviction 0.\n"
            "This is non-negotiable — we never position within 3 days of earnings.\n\n"
            "NORMAL SYNTHESIS:\n"
            "- Value + Quality aligned → amplify conviction\n"
            "- Cheap but low quality → be cautious (value trap)\n"
            "- Expensive but high quality → moderate conviction (growth premium)\n"
            "- Quality declining → bearish regardless of valuation\n\n"
            "Reference specific agent signals. Note any dissent."
        )

    def synthesize(self, agent_signals: list[Signal], symbol: str) -> TeamSignal:
        """Override to enforce earnings blackout."""
        # Check if any agent flagged earnings blackout (conviction 0 from earnings agent)
        earnings_blackout = False
        for sig in agent_signals:
            if sig.metadata.get("conviction", 10) == 0:
                # Check if this is the earnings agent based on reasoning
                if "blackout" in sig.reasoning.lower() or "earnings" in sig.reasoning.lower():
                    earnings_blackout = True
                    break

        # If earnings blackout, override entire team to conviction 0
        if earnings_blackout:
            logger.info("fundamental_manager_earnings_blackout", symbol=symbol)
            return TeamSignal(
                team=self.team_type,
                symbol=symbol,
                direction="BULLISH",
                conviction=1,
                action=SignalAction.HOLD,
                confidence=0.0,
                agreement_level=1.0,
                dissent_summary="",
                key_factors=["earnings_blackout"],
                manager_reasoning=f"Earnings blackout active for {symbol} — conviction forced to 0.",
                contributing_signals=agent_signals,
            )

        # Normal synthesis
        return super().synthesize(agent_signals, symbol)
