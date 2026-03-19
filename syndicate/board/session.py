"""
Board Session — orchestrates CSO → CTO → CPO decision flow.

Triggered by:
1. Event-driven: New contributor registers → Board convenes within 60s
2. Scheduled: Every 6 cycles (24h) → systematic performance review

The Board uses the PLATFORM's API key (from settings), not contributor keys.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from syndicate.board.cpo_agent import CPOAgent
from syndicate.board.cso_agent import CSOAgent
from syndicate.board.cto_agent import CTOAgent
from syndicate.board.guardrails import validate_prompt
from syndicate.config import settings
from syndicate.db.models import (
    AgentRow,
    AgentStatusDB,
    BoardDecisionRow,
    ContributorRow,
    ContributorStatus,
    ProviderType,
    TeamRow,
    TeamStatus,
    ActivationMode,
)

logger = structlog.get_logger()

# Max platform-spawned agents (uses platform API key, not contributor keys)
MAX_PLATFORM_AGENTS = 8


class BoardSession:
    """Orchestrates a Board of Directors convening."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.session_id = uuid.uuid4()
        self._decisions: list[BoardDecisionRow] = []

    async def convene(self, trigger: str, include_performance_review: bool = False) -> dict[str, Any]:
        """
        Run a full Board session.

        Args:
            trigger: Why the board is convening ("new_contributor", "scheduled_review")
            include_performance_review: Whether to run CPO review (scheduled sessions only)

        Returns:
            Summary of all decisions made.
        """
        logger.info("board_convening", trigger=trigger, session_id=str(self.session_id))

        api_key = settings.get_active_llm_key()
        provider = settings.default_llm_provider
        model = settings.default_llm_model

        summary: dict[str, Any] = {
            "session_id": str(self.session_id),
            "trigger": trigger,
            "decisions": [],
        }

        # ── Step 1: CSO — Review organizational structure ──
        cso = CSOAgent(api_key=api_key, provider=provider, model=model)
        teams_data = await self._get_teams_data()
        unassigned_count = await self._get_unassigned_agent_count()
        team_performance = await self._get_team_performance()
        regime = await self._get_latest_regime()

        cso_result = cso.review_organization(
            teams=teams_data,
            unassigned_agent_count=unassigned_count,
            regime=regime,
            team_performance=team_performance,
        )

        # Execute CSO decisions: create new teams
        for new_team in cso_result.get("new_teams", []):
            await self._create_team(new_team)

        summary["cso"] = cso_result
        logger.info("cso_completed", new_teams=len(cso_result.get("new_teams", [])))

        # ── Step 1.5: Spawn platform agents if teams are understaffed ──
        spawned = await self._spawn_platform_agents()
        if spawned:
            summary["platform_agents_spawned"] = spawned
            logger.info("platform_agents_spawned", count=spawned)

        # ── Step 2: CTO — Assign agents and write prompts ──
        cto = CTOAgent(api_key=api_key, provider=provider, model=model)
        unassigned_agents = await self._get_unassigned_agents()
        teams_data = await self._get_teams_data()  # Refresh after CSO may have created teams

        if unassigned_agents:
            cto_result = cto.assign_agents(
                unassigned_agents=unassigned_agents,
                teams=teams_data,
                cso_recommendations=cso_result,
            )

            # Execute CTO decisions: assign agents
            for assignment in cto_result.get("assignments", []):
                await self._assign_agent(assignment)

            summary["cto"] = cto_result
            logger.info("cto_completed", assignments=len(cto_result.get("assignments", [])))
        else:
            summary["cto"] = {"assignments": [], "note": "No unassigned agents"}

        # ── Step 3: CPO — Performance review (scheduled sessions only) ──
        if include_performance_review:
            cpo = CPOAgent(api_key=api_key, provider=provider, model=model)
            agents_data = await self._get_all_agents_data()

            cpo_result = cpo.review_performance(
                agents=agents_data,
                team_performance=team_performance,
            )

            # Execute CPO decisions
            for decision in cpo_result.get("probation_decisions", []):
                await self._execute_performance_decision(decision)

            summary["cpo"] = cpo_result
            logger.info(
                "cpo_completed",
                probation_decisions=len(cpo_result.get("probation_decisions", [])),
            )

        # ── Step 4: Persist all decisions ──
        for decision in self._decisions:
            self.db.add(decision)
        await self.db.flush()

        summary["total_decisions"] = len(self._decisions)
        logger.info("board_session_complete", decisions=len(self._decisions))

        return summary

    # ── Data Fetchers ──

    async def _get_teams_data(self) -> list[dict]:
        result = await self.db.execute(select(TeamRow))
        teams = result.scalars().all()
        data = []
        for t in teams:
            agent_count_q = await self.db.execute(
                select(func.count(AgentRow.id)).where(
                    AgentRow.team_id == t.id,
                    AgentRow.status != AgentStatusDB.FIRED,
                )
            )
            agent_count = agent_count_q.scalar() or 0
            data.append({
                "id": str(t.id),
                "name": t.name,
                "discipline": t.discipline,
                "status": t.status.value,
                "weight": t.weight,
                "data_keys": t.data_keys or [],
                "min_agents": t.min_agents,
                "is_system": t.is_system,
                "agent_count": agent_count,
            })
        return data

    async def _get_unassigned_agent_count(self) -> int:
        result = await self.db.execute(
            select(func.count(AgentRow.id)).where(
                AgentRow.status == AgentStatusDB.REGISTERED,
                AgentRow.team_id.is_(None),
            )
        )
        return result.scalar() or 0

    async def _get_unassigned_agents(self) -> list[dict]:
        from sqlalchemy.orm import joinedload

        result = await self.db.execute(
            select(AgentRow)
            .options(joinedload(AgentRow.contributor))
            .where(
                AgentRow.status == AgentStatusDB.REGISTERED,
                AgentRow.team_id.is_(None),
            )
        )
        agents = result.unique().scalars().all()
        return [
            {
                "id": str(a.id),
                "model": a.model,
                "provider": a.provider.value,
                "contributor_id": str(a.contributor_id) if a.contributor_id else None,
            }
            for a in agents
            if a.contributor is None or a.contributor.status == ContributorStatus.ACTIVE
        ]

    async def _get_all_agents_data(self) -> list[dict]:
        from sqlalchemy.orm import joinedload

        result = await self.db.execute(
            select(AgentRow)
            .options(joinedload(AgentRow.team))
            .where(
                AgentRow.status.in_([
                    AgentStatusDB.FOUNDING,
                    AgentStatusDB.ACTIVE,
                    AgentStatusDB.PROBATION,
                    AgentStatusDB.ASSIGNED,
                ])
            )
        )
        agents = result.unique().scalars().all()
        return [
            {
                "id": str(a.id),
                "team_name": a.team.name if a.team else "unassigned",
                "model": a.model,
                "provider": a.provider.value,
                "status": a.status.value,
                "total_signals": a.total_signals,
                "correct_signals": a.correct_signals,
                "total_cost_usd": str(a.total_cost_usd),
            }
            for a in agents
        ]

    async def _get_team_performance(self) -> dict[str, dict]:
        """Get performance stats per team from agent data."""
        result = await self.db.execute(
            select(AgentRow).where(
                AgentRow.status.in_([
                    AgentStatusDB.FOUNDING,
                    AgentStatusDB.ACTIVE,
                    AgentStatusDB.PROBATION,
                ]),
                AgentRow.team_id.isnot(None),
            )
        )
        agents = result.scalars().all()

        # Get team names
        team_result = await self.db.execute(select(TeamRow))
        team_names = {t.id: t.name for t in team_result.scalars().all()}

        perf: dict[str, dict] = {}
        for agent in agents:
            team_name = team_names.get(agent.team_id, "unknown")
            if team_name not in perf:
                perf[team_name] = {"total": 0, "correct": 0}
            perf[team_name]["total"] += agent.total_signals
            perf[team_name]["correct"] += agent.correct_signals

        for stats in perf.values():
            stats["accuracy"] = (
                stats["correct"] / stats["total"] if stats["total"] > 0 else 0.0
            )

        return perf

    async def _get_latest_regime(self) -> str:
        """Get the regime from the most recent completed cycle."""
        from syndicate.db.models import CycleRow

        result = await self.db.execute(
            select(CycleRow.regime)
            .where(CycleRow.completed_at.isnot(None))
            .order_by(CycleRow.id.desc())
            .limit(1)
        )
        regime = result.scalar_one_or_none()
        return regime or "ranging"

    # ── Decision Executors ──

    async def _spawn_platform_agents(self) -> int:
        """
        Spawn platform-owned agents to fill understaffed teams.

        Platform agents use the platform's API key (not contributor keys).
        Capped at MAX_PLATFORM_AGENTS total across all teams.
        Returns the number of agents spawned.
        """
        # Count existing platform-spawned agents (non-founding, non-fired, no contributor)
        existing_q = await self.db.execute(
            select(func.count(AgentRow.id)).where(
                AgentRow.contributor_id.is_(None),
                AgentRow.status.notin_([AgentStatusDB.FOUNDING, AgentStatusDB.FIRED]),
            )
        )
        existing_platform = existing_q.scalar() or 0
        budget = MAX_PLATFORM_AGENTS - existing_platform

        if budget <= 0:
            return 0

        # Find understaffed teams (fewer agents than min_agents)
        teams = await self.db.execute(select(TeamRow))
        understaffed = []
        for team in teams.scalars().all():
            count_q = await self.db.execute(
                select(func.count(AgentRow.id))
                .outerjoin(ContributorRow, AgentRow.contributor_id == ContributorRow.id)
                .where(
                    AgentRow.team_id == team.id,
                    AgentRow.status.notin_([AgentStatusDB.FIRED]),
                    sa.or_(
                        AgentRow.contributor_id.is_(None),
                        ContributorRow.status == ContributorStatus.ACTIVE,
                    ),
                )
            )
            current = count_q.scalar() or 0
            deficit = team.min_agents - current
            if deficit > 0:
                understaffed.append((team, deficit))

        if not understaffed:
            return 0

        spawned = 0
        for team, deficit in understaffed:
            to_spawn = min(deficit, budget - spawned)
            if to_spawn <= 0:
                break

            for i in range(to_spawn):
                agent = AgentRow(
                    contributor_id=None,
                    team_id=None,  # CTO will assign
                    role=f"platform_analyst_{i + 1}",
                    model=settings.default_llm_model,
                    provider=ProviderType(settings.default_llm_provider.value),
                    status=AgentStatusDB.REGISTERED,
                    quarantine_signals_remaining=10,
                )
                self.db.add(agent)
                spawned += 1

            logger.info(
                "platform_agents_created",
                team=team.name,
                count=to_spawn,
                deficit=deficit,
            )

        if spawned:
            await self.db.flush()

        return spawned

    async def _create_team(self, team_data: dict) -> None:
        """Create a new team proposed by the CSO."""
        # Check if team name already exists
        existing = await self.db.execute(
            select(TeamRow).where(TeamRow.name == team_data["team_name"])
        )
        if existing.scalar_one_or_none():
            logger.warning("team_already_exists", name=team_data["team_name"])
            return

        # Validate data_keys against the resolver registry
        from syndicate.board.guardrails import validate_data_keys
        from syndicate.data.data_layer import MarketSnapshot
        available_keys = set(MarketSnapshot._DATA_RESOLVERS.keys())
        key_errors = validate_data_keys(team_data.get("data_keys", []), available_keys)
        if key_errors:
            logger.warning("invalid_data_keys", team=team_data["team_name"], errors=key_errors)
            # Filter to only valid keys
            valid_keys = [k for k in team_data.get("data_keys", []) if k in available_keys]
        else:
            valid_keys = team_data.get("data_keys", [])

        team = TeamRow(
            name=team_data["team_name"],
            discipline=team_data["discipline"],
            status=TeamStatus.PROVISIONAL,
            data_keys=valid_keys,
            min_agents=team_data.get("min_agents", 2),
            activation_mode=ActivationMode(team_data.get("activation_mode", "always")),
            activation_condition=team_data.get("activation_condition"),
            is_system=False,
            created_by="board_cso",
        )
        self.db.add(team)
        await self.db.flush()

        self._decisions.append(BoardDecisionRow(
            session_id=self.session_id,
            decision_type="team_created",
            team_id=team.id,
            reasoning=team_data.get("justification", ""),
            decided_by="cso",
        ))

        logger.info("team_created", name=team_data["team_name"])

    async def _assign_agent(self, assignment: dict) -> None:
        """Assign an agent to a team with a system prompt."""
        agent_id = uuid.UUID(assignment["agent_id"])
        team_name = assignment["team_name"]

        # Find the agent
        agent_result = await self.db.execute(
            select(AgentRow).where(AgentRow.id == agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        if agent is None:
            logger.warning("agent_not_found", agent_id=str(agent_id))
            return

        # Founding agents cannot be reassigned
        if agent.status == AgentStatusDB.FOUNDING:
            logger.warning("cannot_reassign_founding", agent_id=str(agent_id))
            return

        # Don't assign agents whose contributor is no longer active
        if agent.contributor_id:
            contributor = await self.db.get(ContributorRow, agent.contributor_id)
            if contributor and contributor.status != ContributorStatus.ACTIVE:
                logger.warning("contributor_not_active", agent_id=str(agent_id))
                return

        # Find the team
        team_result = await self.db.execute(
            select(TeamRow).where(TeamRow.name == team_name)
        )
        team = team_result.scalar_one_or_none()
        if team is None:
            logger.warning("team_not_found", name=team_name)
            return

        # Validate prompt
        system_prompt = assignment.get("system_prompt", "")
        errors = validate_prompt(system_prompt)
        if errors:
            logger.warning(
                "prompt_validation_failed",
                agent_id=str(agent_id),
                errors=errors,
            )
            # Don't block assignment, but log the issues

        # Execute assignment
        agent.team_id = team.id
        agent.role = assignment.get("role", agent.role)
        agent.system_prompt = system_prompt
        agent.status = AgentStatusDB.ASSIGNED
        agent.quarantine_signals_remaining = 10  # Start quarantine

        self._decisions.append(BoardDecisionRow(
            session_id=self.session_id,
            decision_type="agent_assigned",
            agent_id=agent.id,
            team_id=team.id,
            reasoning=assignment.get("reasoning", ""),
            decided_by="cto_talent",
        ))

        logger.info("agent_assigned", agent_id=str(agent_id), team=team_name)

    async def _execute_performance_decision(self, decision: dict) -> None:
        """Execute a CPO probation/firing/redemption decision."""
        agent_id = uuid.UUID(decision["agent_id"])
        action = decision["action"]

        agent_result = await self.db.execute(
            select(AgentRow).where(AgentRow.id == agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        if agent is None:
            return

        # Founding agents are immune
        if agent.status == AgentStatusDB.FOUNDING:
            logger.info("founding_agent_immune", agent_id=str(agent_id))
            return

        if action == "probation":
            agent.status = AgentStatusDB.PROBATION
            agent.probation_started_at = datetime.now(timezone.utc)
        elif action == "fire":
            agent.status = AgentStatusDB.FIRED
            agent.fired_at = datetime.now(timezone.utc)
            agent.team_id = None  # Remove from team
        elif action == "redeem":
            agent.status = AgentStatusDB.ACTIVE
            agent.probation_started_at = None

        self._decisions.append(BoardDecisionRow(
            session_id=self.session_id,
            decision_type=f"agent_{action}",
            agent_id=agent.id,
            reasoning=decision.get("reasoning", ""),
            decided_by="cpo",
        ))

        logger.info("performance_decision", agent_id=str(agent_id), action=action)
