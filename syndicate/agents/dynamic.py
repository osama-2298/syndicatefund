"""Dynamic agents and team managers — prompt-driven from database."""

from __future__ import annotations

from typing import Any

from syndicate.agents.base import BaseAgent
from syndicate.agents.team_manager import BaseTeamManager
from syndicate.config import LLMProvider
from syndicate.data.models import AgentProfile


class DynamicAgent(BaseAgent):
    """
    Agent whose system prompt is stored in the database (Board-written).
    Used for contributor agents — no hardcoded Python class.
    """

    def __init__(
        self,
        profile: AgentProfile,
        api_key: str,
        provider: LLMProvider,
        system_prompt_text: str,
        team_name: str,
        data_keys: list[str],
    ) -> None:
        super().__init__(profile=profile, api_key=api_key, provider=provider)
        self._system_prompt_text = system_prompt_text
        self._team_name = team_name
        self._data_keys = data_keys

    @property
    def team_type(self) -> str:
        """Return team name as string (dynamic teams don't use TeamType enum)."""
        return self._team_name

    @property
    def system_prompt(self) -> str:
        return self._system_prompt_text

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        """Generic prompt builder — presents all data keys with labels."""
        symbol = self.profile.symbol
        parts = [f"Analyze {symbol} for trading signals.\n"]

        for key, value in market_data.items():
            if value is None:
                continue
            if hasattr(value, "to_summary"):
                parts.append(f"=== {key.upper()} ===\n{value.to_summary()}\n")
            elif isinstance(value, dict):
                # Format dict data
                formatted = "\n".join(f"  {k}: {v}" for k, v in value.items() if v is not None)
                if formatted:
                    parts.append(f"=== {key.upper()} ===\n{formatted}\n")
            elif isinstance(value, str) and len(value) > 0:
                parts.append(f"=== {key.upper()} ===\n{value}\n")
            elif isinstance(value, (list, tuple)) and len(value) > 0:
                items = "\n".join(f"  - {item}" for item in value[:20])
                parts.append(f"=== {key.upper()} ===\n{items}\n")

        parts.append(
            "\nProvide your directional prediction (BULLISH or BEARISH) "
            "with conviction (0-10) and reasoning."
        )
        return "\n".join(parts)


class DynamicTeamManager(BaseTeamManager):
    """
    Team manager whose prompt is stored in the database.
    Used for Board-created teams.
    """

    def __init__(
        self,
        api_key: str,
        provider: LLMProvider,
        model: str,
        manager_prompt: str,
        team_name: str,
    ) -> None:
        super().__init__(api_key=api_key, provider=provider, model=model)
        self._manager_prompt = manager_prompt
        self._team_name = team_name

    @property
    def team_type(self) -> str:
        """Return team name as string."""
        return self._team_name

    @property
    def system_prompt(self) -> str:
        return self._manager_prompt
