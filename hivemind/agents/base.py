"""
Base agent classes for the Hivemind system.

BaseLLMCaller — shared LLM client initialization and calling logic.
BaseAgent     — analyst agents that produce trading Signals (inherits BaseLLMCaller).

KEY DESIGN: Agents output DIRECTION (BULLISH/BEARISH) + CONVICTION (1-10).
There is NO HOLD option. The SYSTEM decides whether to trade based on conviction.

This prevents the RLHF conservative bias where LLMs default to "do nothing."
Based on research: Lopez de Prado meta-labeling, ATLAS framework, TradingAgents,
Evidently AI binary classification research.
"""

from __future__ import annotations

import json
import threading
from abc import ABC, abstractmethod
from typing import Any

import anthropic
import openai
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from hivemind.config import LLMProvider
from hivemind.data.models import AgentProfile, Signal, SignalAction, TeamType

logger = structlog.get_logger()

# Max 10 concurrent Anthropic/OpenAI calls across all agents
_LLM_SEMAPHORE = threading.Semaphore(10)


def _is_retryable_error(exc: BaseException) -> bool:
    # Anthropic errors
    if isinstance(exc, anthropic.RateLimitError):
        return True
    if isinstance(exc, anthropic.APIStatusError) and exc.status_code >= 500:
        return True
    if isinstance(exc, (anthropic.APIConnectionError, anthropic.APITimeoutError)):
        return True
    # OpenAI errors
    if isinstance(exc, openai.RateLimitError):
        return True
    if isinstance(exc, openai.APIStatusError) and exc.status_code >= 500:
        return True
    if isinstance(exc, (openai.APIConnectionError, openai.APITimeoutError)):
        return True
    return False

# The tool schema forces agents to pick a DIRECTION.
# There is NO HOLD option. The system maps conviction to trade/no-trade.
SIGNAL_TOOL = {
    "name": "produce_signal",
    "description": (
        "Predict the price direction for this asset. "
        "You MUST pick BULLISH or BEARISH — there is no neutral option. "
        "If you barely lean one way, pick that direction with low conviction."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "direction": {
                "type": "string",
                "enum": ["BULLISH", "BEARISH"],
                "description": (
                    "Your directional prediction. BULLISH = price will go up. "
                    "BEARISH = price will go down. You MUST pick one. "
                    "Even if signals are mixed, choose the direction you lean toward."
                ),
            },
            "conviction": {
                "type": "integer",
                "minimum": 0,
                "maximum": 10,
                "description": (
                    "How strongly you believe in your direction, from 0 to 10. "
                    "0: GENUINELY NO EDGE — the data is truly directionless. Use LESS THAN 10% of the time. "
                    "This is NOT for uncertainty — if you lean even slightly, pick that direction with 1-2. "
                    "1-2: barely leaning, essentially a coin flip. "
                    "3-4: slight edge, some supporting evidence. "
                    "5-6: clear edge, multiple signals aligned. "
                    "7-8: strong conviction, most evidence agrees. "
                    "9-10: extreme conviction, textbook setup. Very rare."
                ),
            },
            "reasoning": {
                "type": "string",
                "description": (
                    "2-3 sentences. Reference specific pre-computed scores. "
                    "State which signals support your direction and which oppose it."
                ),
            },
        },
        "required": ["direction", "conviction", "reasoning"],
    },
}

# Conviction-to-action mapping thresholds
# Conviction 1-3: system decides "no edge" → HOLD
# Conviction 4+: system allows the trade through
CONVICTION_TRADE_THRESHOLD = 4


class BaseLLMCaller:
    """
    Shared LLM client initialization and structured tool calling.

    Both analyst agents (BaseAgent) and executive agents (CEO, COO) inherit from this.
    Each subclass provides its own tool schema and return type.
    """

    def __init__(self, api_key: str, provider: LLMProvider, model: str = "claude-opus-4-6") -> None:
        self._provider = provider
        self._api_key = api_key
        self._model = model

        if provider == LLMProvider.ANTHROPIC:
            self._anthropic = anthropic.Anthropic(api_key=api_key)
            self._openai = None
        elif provider == LLMProvider.OPENAI:
            self._openai = openai.OpenAI(api_key=api_key)
            self._anthropic = None
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def _call_llm_with_tool(
        self,
        system_prompt: str,
        user_prompt: str,
        tool: dict[str, Any],
    ) -> dict[str, Any]:
        if self._provider == LLMProvider.ANTHROPIC:
            return self._call_anthropic(system_prompt, user_prompt, tool)
        elif self._provider == LLMProvider.OPENAI:
            return self._call_openai(system_prompt, user_prompt, tool)
        raise ValueError(f"Unsupported provider: {self._provider}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception(_is_retryable_error),
    )
    def _call_anthropic(
        self, system_prompt: str, user_prompt: str, tool: dict[str, Any]
    ) -> dict[str, Any]:
        with _LLM_SEMAPHORE:
            response = self._anthropic.messages.create(
                model=self._model,
                max_tokens=1024,
                system=system_prompt,
                tools=[tool],
                tool_choice={"type": "tool", "name": tool["name"]},
                messages=[{"role": "user", "content": user_prompt}],
            )
        for block in response.content:
            if block.type == "tool_use" and block.name == tool["name"]:
                return block.input
        raise ValueError(f"LLM response did not contain a {tool['name']} tool call")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception(_is_retryable_error),
    )
    def _call_openai(
        self, system_prompt: str, user_prompt: str, tool: dict[str, Any]
    ) -> dict[str, Any]:
        openai_tool = {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        }
        with _LLM_SEMAPHORE:
            response = self._openai.chat.completions.create(
                model=self._model,
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                tools=[openai_tool],
                tool_choice={"type": "function", "function": {"name": tool["name"]}},
            )
        message = response.choices[0].message
        if message.tool_calls:
            args_str = message.tool_calls[0].function.arguments
            return json.loads(args_str)
        raise ValueError(f"LLM response did not contain a {tool['name']} function call")


class BaseAgent(BaseLLMCaller, ABC):
    """
    Abstract base for all Hivemind trading analyst agents.

    Agents output DIRECTION + CONVICTION. The system maps this to trading actions:
    - BULLISH + conviction >= 4 → BUY
    - BEARISH + conviction >= 4 → SHORT
    - Any direction + conviction <= 3 → HOLD (system decided, not the agent)
    """

    def __init__(self, profile: AgentProfile, api_key: str, provider: LLMProvider) -> None:
        super().__init__(api_key=api_key, provider=provider, model=profile.model)
        self.profile = profile

    @property
    @abstractmethod
    def team_type(self) -> TeamType:
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        ...

    @abstractmethod
    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        ...

    def analyze(self, market_data: dict[str, Any]) -> Signal:
        """
        Run analysis and produce a trading signal.

        The LLM outputs DIRECTION + CONVICTION.
        This method maps conviction to action:
          conviction 1-3 → HOLD (system says "no edge")
          conviction 4+ + BULLISH → BUY
          conviction 4+ + BEARISH → SHORT
        """
        prompt = self.build_analysis_prompt(market_data)

        try:
            raw = self._call_llm_with_tool(self.system_prompt, prompt, SIGNAL_TOOL)
        except Exception as e:
            logger.error("agent_llm_call_failed", agent_id=self.profile.agent_id, error=str(e))
            return Signal(
                agent_id=self.profile.agent_id,
                team=self.team_type,
                symbol=self.profile.symbol,
                action=SignalAction.HOLD,
                confidence=0.0,
                reasoning=f"Analysis failed: {str(e)[:100]}",
            )

        direction = raw.get("direction", "BULLISH")
        conviction = int(raw.get("conviction", 1))
        conviction = max(0, min(10, conviction))
        reasoning = raw.get("reasoning", "")

        # Map conviction to confidence (0.0 to 1.0)
        confidence = conviction / 10.0

        # Map direction + conviction to action
        if conviction == 0:
            # Agent explicitly says "genuinely no edge" — strongest no-trade signal
            action = SignalAction.HOLD
        elif conviction < CONVICTION_TRADE_THRESHOLD:
            # System decides: not enough conviction to trade
            action = SignalAction.HOLD
        elif direction == "BULLISH":
            action = SignalAction.BUY
        elif direction == "BEARISH":
            action = SignalAction.SHORT
        else:
            action = SignalAction.HOLD

        signal = Signal(
            agent_id=self.profile.agent_id,
            team=self.team_type,
            symbol=self.profile.symbol,
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            metadata={
                "direction": direction,
                "conviction": conviction,
            },
        )

        return signal
