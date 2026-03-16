"""Agent registry — loads agent definitions from database, resolves to callable instances."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from syndicate.config import LLMProvider, settings
from syndicate.core.encryption import decrypt_api_key
from syndicate.data.models import AgentProfile

logger = structlog.get_logger()

# ── Founding agent class lookup ──
# Maps agent_class string from DB to the actual Python class

from syndicate.agents.technical.trend_agent import TechnicalTrendAgent
from syndicate.agents.technical.signal_agent import TechnicalSignalAgent
from syndicate.agents.technical.timing_agent import TechnicalTimingAgent
from syndicate.agents.sentiment.social_agent import SocialSentimentAgent
from syndicate.agents.sentiment.market_agent import MarketSentimentAgent
from syndicate.agents.sentiment.smart_money_agent import SmartMoneySentimentAgent
from syndicate.agents.fundamental.valuation_agent import ValuationAgent
from syndicate.agents.fundamental.cycle_agent import CyclePositionAgent
from syndicate.agents.macro.crypto_macro_agent import CryptoMacroAgent
from syndicate.agents.macro.external_macro_agent import ExternalMacroAgent
from syndicate.agents.onchain.network_agent import NetworkHealthAgent
from syndicate.agents.onchain.capital_flow_agent import CapitalFlowAgent

from syndicate.agents.technical.technical_manager import TechnicalManager
from syndicate.agents.sentiment.sentiment_manager import SentimentManager
from syndicate.agents.fundamental.fundamental_manager import FundamentalManager
from syndicate.agents.macro.macro_manager import MacroManager
from syndicate.agents.onchain.onchain_manager import OnChainManager

FOUNDING_AGENT_CLASSES: dict[str, type] = {
    "TechnicalTrendAgent": TechnicalTrendAgent,
    "TechnicalSignalAgent": TechnicalSignalAgent,
    "TechnicalTimingAgent": TechnicalTimingAgent,
    "SocialSentimentAgent": SocialSentimentAgent,
    "MarketSentimentAgent": MarketSentimentAgent,
    "SmartMoneySentimentAgent": SmartMoneySentimentAgent,
    "ValuationAgent": ValuationAgent,
    "CyclePositionAgent": CyclePositionAgent,
    "CryptoMacroAgent": CryptoMacroAgent,
    "ExternalMacroAgent": ExternalMacroAgent,
    "NetworkHealthAgent": NetworkHealthAgent,
    "CapitalFlowAgent": CapitalFlowAgent,
}

FOUNDING_MANAGER_CLASSES: dict[str, type] = {
    "technical": TechnicalManager,
    "sentiment": SentimentManager,
    "fundamental": FundamentalManager,
    "macro": MacroManager,
    "onchain": OnChainManager,
}


@dataclass
class AgentDefinition:
    """Lightweight struct representing an agent loaded from the database."""

    id: UUID
    contributor_id: UUID | None
    team_id: UUID | None
    team_name: str
    role: str
    agent_class: str | None  # Python class name for founding agents
    model: str
    provider: str  # "anthropic", "openai", "google"
    system_prompt: str | None
    status: str
    total_signals: int
    correct_signals: int
    quarantine_signals_remaining: int
    data_keys: list[str]  # From the team
    # Encrypted key bytes (resolved lazily)
    _api_key_enc: bytes | None = field(default=None, repr=False)


class AgentRegistry:
    """Loads agent definitions from database, resolves to callable agent instances."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session
        self._cache: dict[UUID, list[AgentDefinition]] = {}  # team_id -> agents
        self._team_meta: dict[UUID, dict[str, Any]] = {}  # team_id -> {name, manager_prompt, ...}
        self._key_cache: dict[UUID, str] = {}  # contributor_id -> decrypted key

    async def load_all(self) -> None:
        """Load all active agents and teams from the database."""
        from syndicate.db.models import AgentRow, AgentStatusDB, TeamRow

        # Load all active teams
        team_result = await self._db.execute(select(TeamRow))
        teams = {t.id: t for t in team_result.scalars().all()}

        # Load all active agents (founding, assigned, active, probation)
        active_statuses = [
            AgentStatusDB.FOUNDING,
            AgentStatusDB.ASSIGNED,
            AgentStatusDB.ACTIVE,
            AgentStatusDB.PROBATION,
        ]
        agent_result = await self._db.execute(
            select(AgentRow)
            .options(joinedload(AgentRow.contributor))
            .where(AgentRow.status.in_(active_statuses))
            .where(AgentRow.team_id.isnot(None))
        )
        agents = agent_result.unique().scalars().all()

        self._cache.clear()
        self._team_meta.clear()

        for agent in agents:
            team = teams.get(agent.team_id)
            if team is None:
                continue

            defn = AgentDefinition(
                id=agent.id,
                contributor_id=agent.contributor_id,
                team_id=agent.team_id,
                team_name=team.name,
                role=agent.role,
                agent_class=agent.agent_class,
                model=agent.model,
                provider=agent.provider.value,
                system_prompt=agent.system_prompt,
                status=agent.status.value,
                total_signals=agent.total_signals,
                correct_signals=agent.correct_signals,
                quarantine_signals_remaining=agent.quarantine_signals_remaining,
                data_keys=team.data_keys or [],
            )

            # Cache encrypted key for contributor agents
            if agent.contributor_id and agent.contributor:
                c = agent.contributor
                if agent.provider.value == "anthropic" and c.api_key_anthropic_enc:
                    defn._api_key_enc = c.api_key_anthropic_enc
                elif agent.provider.value == "openai" and c.api_key_openai_enc:
                    defn._api_key_enc = c.api_key_openai_enc
                elif agent.provider.value == "google" and c.api_key_google_enc:
                    defn._api_key_enc = c.api_key_google_enc

            if agent.team_id not in self._cache:
                self._cache[agent.team_id] = []
            self._cache[agent.team_id].append(defn)

            # Store team metadata for manager lookup
            if agent.team_id not in self._team_meta:
                self._team_meta[agent.team_id] = {
                    "name": team.name,
                    "manager_prompt": team.manager_prompt,
                    "is_system": team.is_system,
                    "weight": team.weight,
                    "data_keys": team.data_keys or [],
                }

        logger.info(
            "agent_registry_loaded",
            total_agents=len(agents),
            teams=len(self._cache),
        )

    def get_team_agents(self, team_id: UUID) -> list[AgentDefinition]:
        """Returns all active agents for a team."""
        return self._cache.get(team_id, [])

    def get_all_teams(self) -> dict[UUID, list[AgentDefinition]]:
        """Returns all teams and their agents."""
        return dict(self._cache)

    def get_team_meta(self, team_id: UUID) -> dict[str, Any] | None:
        """Returns team metadata (name, manager_prompt, etc.)."""
        return self._team_meta.get(team_id)

    def get_api_key(self, agent_def: AgentDefinition) -> str:
        """Get the decrypted API key for an agent.

        Founding/platform agents use settings.get_active_llm_key().
        Contributor agents decrypt from the contributors table.
        """
        if agent_def.contributor_id is None:
            # Founding agent — use platform key
            return settings.get_active_llm_key()

        # Check cache
        if agent_def.contributor_id in self._key_cache:
            return self._key_cache[agent_def.contributor_id]

        # Decrypt
        if agent_def._api_key_enc is None:
            logger.warning("no_api_key_for_agent", agent_id=str(agent_def.id))
            return settings.get_active_llm_key()  # Fallback to platform key

        key = decrypt_api_key(agent_def._api_key_enc)
        self._key_cache[agent_def.contributor_id] = key
        return key

    def instantiate_agent(self, agent_def: AgentDefinition, symbol: str):
        """Create a runnable agent instance.

        For founding agents: imports the Python class, uses its built-in prompt.
        For contributor agents: creates DynamicAgent with DB-stored prompt.
        """
        api_key = self.get_api_key(agent_def)
        provider = LLMProvider(agent_def.provider)

        profile = AgentProfile(
            agent_id=str(agent_def.id),
            team=agent_def.team_name,
            symbol=symbol,
            model=agent_def.model,
            provider=agent_def.provider,
            total_signals=agent_def.total_signals,
            correct_signals=agent_def.correct_signals,
        )

        if agent_def.agent_class and agent_def.agent_class in FOUNDING_AGENT_CLASSES:
            # Founding agent — use the Python class with its built-in prompt
            agent_cls = FOUNDING_AGENT_CLASSES[agent_def.agent_class]
            return agent_cls(profile=profile, api_key=api_key, provider=provider)
        else:
            # Dynamic agent — use DB-stored prompt
            from syndicate.agents.dynamic import DynamicAgent

            return DynamicAgent(
                profile=profile,
                api_key=api_key,
                provider=provider,
                system_prompt_text=agent_def.system_prompt
                or "You are a crypto trading analyst. Analyze the data and provide your directional prediction.",
                team_name=agent_def.team_name,
                data_keys=agent_def.data_keys,
            )

    def get_manager_for_team(
        self,
        team_name: str,
        team_manager_prompt: str | None,
        api_key: str | None = None,
    ):
        """Get a team manager instance.

        For system teams: uses the founding manager class.
        For dynamic teams: creates DynamicTeamManager with DB prompt.
        """
        _api_key = api_key or settings.get_active_llm_key()
        provider = settings.default_llm_provider
        model = settings.default_llm_model

        if team_name in FOUNDING_MANAGER_CLASSES:
            manager_cls = FOUNDING_MANAGER_CLASSES[team_name]
            return manager_cls(api_key=_api_key, provider=provider, model=model)
        else:
            from syndicate.agents.dynamic import DynamicTeamManager

            return DynamicTeamManager(
                api_key=_api_key,
                provider=provider,
                model=model,
                manager_prompt=team_manager_prompt
                or "You are a team manager. Synthesize your agents' signals.",
                team_name=team_name,
            )
