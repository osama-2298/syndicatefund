"""
Base Team Manager — synthesizes multiple agent signals into one team signal.

Architecture:
  Agents (independent) → Manager (synthesis) → TeamSignal → Aggregator

The manager:
1. Receives all agent signals from its team (AFTER agents committed independently)
2. Identifies agreement/disagreement patterns
3. Produces ONE synthesized TeamSignal per coin
4. Does NOT feed back to agents (one-way flow)

Each team's manager has a specialized knowledge base loaded from a markdown file.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import structlog

from hivemind.agents.base import BaseLLMCaller, CONVICTION_TRADE_THRESHOLD
from hivemind.config import LLMProvider
from hivemind.data.models import Signal, SignalAction, TeamSignal, TeamType

logger = structlog.get_logger()

TEAM_SIGNAL_TOOL = {
    "name": "produce_team_signal",
    "description": (
        "Synthesize your team's agent signals into one team signal. "
        "You MUST call this tool."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "direction": {
                "type": "string",
                "enum": ["BULLISH", "BEARISH"],
                "description": "The synthesized team direction. Pick the direction your team leans overall.",
            },
            "conviction": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "description": (
                    "Team conviction. Amplify when agents agree (8-10 if all aligned). "
                    "Reduce when they disagree (1-3 if conflicting). "
                    "5-7 if mostly aligned with minor dissent."
                ),
            },
            "agreement_level": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "How much agents agreed. 1.0 = unanimous, 0.5 = split, 0.0 = full disagreement.",
            },
            "dissent_summary": {
                "type": "string",
                "description": "What the minority agent(s) think and why. Empty if unanimous.",
            },
            "key_factors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Top 3 factors driving the synthesized direction.",
            },
            "timeframe_alignment": {
                "type": "string",
                "enum": ["FULLY_ALIGNED", "MOSTLY_ALIGNED", "CONFLICTING", "N/A"],
                "description": "For Technical team: timeframe alignment. N/A for other teams.",
            },
            "reasoning": {
                "type": "string",
                "description": "2-3 sentences explaining the synthesis. Reference specific agent signals.",
            },
        },
        "required": [
            "direction", "conviction", "agreement_level",
            "dissent_summary", "key_factors", "reasoning",
        ],
    },
}


def _load_manager_knowledge(knowledge_path: Path) -> str:
    """Load a manager's knowledge base from markdown file."""
    if not knowledge_path.exists():
        return ""
    try:
        content = knowledge_path.read_text()
        # Extract actionable rules (bullet points, numbered items, bold headings)
        lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith(("#", "- ", "* ", "**")) or (stripped and stripped[0].isdigit() and "." in stripped[:3]):
                lines.append(stripped)
        return "\n".join(lines[:200])  # Cap at 200 lines
    except Exception:
        return ""


class BaseTeamManager(BaseLLMCaller, ABC):
    """
    Abstract base for all team managers.
    Receives agent signals, produces a TeamSignal.
    """

    def __init__(self, api_key: str, provider: LLMProvider, model: str = "claude-opus-4-6") -> None:
        super().__init__(api_key=api_key, provider=provider, model=model)

    @property
    @abstractmethod
    def team_type(self) -> TeamType:
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        ...

    def synthesize(self, agent_signals: list[Signal], symbol: str) -> TeamSignal:
        """
        Synthesize multiple agent signals into one team signal.
        This is the main entry point for the manager.
        """
        if not agent_signals:
            return self._empty_signal(symbol)

        prompt = self._build_synthesis_prompt(agent_signals, symbol)

        try:
            raw = self._call_llm_with_tool(self.system_prompt, prompt, TEAM_SIGNAL_TOOL)
        except Exception as e:
            logger.error("team_manager_failed", team=self.team_type.value, error=str(e))
            return self._deterministic_fallback(agent_signals, symbol)

        direction = raw.get("direction", "BULLISH")
        conviction = max(1, min(10, int(raw.get("conviction", 5))))
        confidence = conviction / 10.0

        # Map conviction to action (same as base agent)
        if conviction < CONVICTION_TRADE_THRESHOLD:
            action = SignalAction.HOLD
        elif direction == "BULLISH":
            action = SignalAction.BUY
        elif direction == "BEARISH":
            action = SignalAction.SHORT
        else:
            action = SignalAction.HOLD

        return TeamSignal(
            team=self.team_type,
            symbol=symbol,
            direction=direction,
            conviction=conviction,
            action=action,
            confidence=confidence,
            agreement_level=float(raw.get("agreement_level", 0.5)),
            dissent_summary=raw.get("dissent_summary", ""),
            key_factors=raw.get("key_factors", []),
            timeframe_alignment=raw.get("timeframe_alignment", "N/A"),
            manager_reasoning=raw.get("reasoning", ""),
            contributing_signals=agent_signals,
        )

    def _build_synthesis_prompt(self, signals: list[Signal], symbol: str) -> str:
        """Build the prompt showing all agent signals for synthesis."""
        prompt = f"Synthesize your team's signals for {symbol}.\n\n"
        prompt += f"=== AGENT SIGNALS ({len(signals)} agents) ===\n\n"

        for i, sig in enumerate(signals, 1):
            direction = sig.metadata.get("direction", sig.action.value)
            conviction = sig.metadata.get("conviction", int(sig.confidence * 10))
            prompt += (
                f"Agent {i}: {direction} (conviction: {conviction}/10)\n"
                f"  Reasoning: {sig.reasoning}\n\n"
            )

        # Summary stats
        bullish = sum(1 for s in signals if s.metadata.get("direction") == "BULLISH" or s.action in (SignalAction.BUY, SignalAction.COVER))
        bearish = sum(1 for s in signals if s.metadata.get("direction") == "BEARISH" or s.action in (SignalAction.SHORT, SignalAction.SELL))
        prompt += f"Vote count: {bullish} BULLISH / {bearish} BEARISH\n"

        avg_conviction = sum(s.metadata.get("conviction", int(s.confidence * 10)) for s in signals) / len(signals)
        prompt += f"Average conviction: {avg_conviction:.1f}/10\n\n"

        prompt += "Synthesize these signals into ONE team signal. Apply your knowledge base."
        return prompt

    def _deterministic_fallback(self, signals: list[Signal], symbol: str) -> TeamSignal:
        """Fallback when LLM fails — majority vote + average conviction."""
        bullish = sum(1 for s in signals if s.metadata.get("direction") == "BULLISH" or s.action in (SignalAction.BUY, SignalAction.COVER))
        bearish = len(signals) - bullish

        direction = "BULLISH" if bullish >= bearish else "BEARISH"
        avg_conv = sum(s.metadata.get("conviction", int(s.confidence * 10)) for s in signals) / max(len(signals), 1)
        conviction = max(1, min(10, round(avg_conv)))
        confidence = conviction / 10.0

        if conviction < CONVICTION_TRADE_THRESHOLD:
            action = SignalAction.HOLD
        elif direction == "BULLISH":
            action = SignalAction.BUY
        else:
            action = SignalAction.SHORT

        agreement = max(bullish, bearish) / max(len(signals), 1)

        return TeamSignal(
            team=self.team_type,
            symbol=symbol,
            direction=direction,
            conviction=conviction,
            action=action,
            confidence=confidence,
            agreement_level=agreement,
            dissent_summary="LLM fallback — using majority vote.",
            key_factors=["deterministic_fallback"],
            manager_reasoning="Manager LLM call failed. Using majority vote with average conviction.",
            contributing_signals=signals,
        )

    def _empty_signal(self, symbol: str) -> TeamSignal:
        return TeamSignal(
            team=self.team_type,
            symbol=symbol,
            direction="BULLISH",
            conviction=1,
            action=SignalAction.HOLD,
            confidence=0.1,
            agreement_level=0.0,
            manager_reasoning="No agent signals received.",
            contributing_signals=[],
        )
