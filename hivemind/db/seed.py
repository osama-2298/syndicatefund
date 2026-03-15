"""
Seed the database with the 5 system teams and 12 founding agents.

Usage:
    python -m hivemind.db.seed

Idempotent — safe to run multiple times. Skips if data already exists.
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select

from hivemind.db.models import (
    AgentRow,
    AgentStatusDB,
    ActivationMode,
    ProviderType,
    TeamRow,
    TeamStatus,
)
from hivemind.db.session import async_session_factory, engine


# ── System Teams ──
# data_keys match what the existing for_X() methods return

SYSTEM_TEAMS = [
    {
        "name": "technical",
        "discipline": "Chart patterns, multi-timeframe indicators (1H/4H/1D), order book analysis, derivatives data. Identifies trends, entry timing, and technical setups.",
        "data_keys": [
            "indicators_4h", "indicators_1h", "indicators_1d",
            "price_history_4h", "stats_24h", "order_book", "derivatives",
        ],
        "min_agents": 3,
    },
    {
        "name": "sentiment",
        "discipline": "Social media sentiment (Reddit), Fear & Greed Index, crowd psychology, smart money positioning, trending coins. Detects shifts in market emotion.",
        "data_keys": [
            "fear_greed", "reddit_sentiment", "reddit_coin_sentiment",
            "trending", "coingecko_coin", "smart_money", "indicators", "stats_24h",
        ],
        "min_agents": 3,
    },
    {
        "name": "fundamental",
        "discipline": "Valuation metrics, tokenomics, market cap analysis, competitive positioning. Uses CoinGecko and CoinPaprika data with weekly/daily cycle context.",
        "data_keys": [
            "coingecko_coin", "paprika_coin", "indicators",
            "indicators_1d", "indicators_1w", "stats_24h",
        ],
        "min_agents": 2,
    },
    {
        "name": "macro",
        "discipline": "Global crypto market conditions, BTC dominance, prediction markets (Fed, recession), cross-market correlations. Top-down macro analysis.",
        "data_keys": [
            "global_data", "paprika_global", "prediction_markets",
            "stats_24h",
        ],
        "min_agents": 2,
    },
    {
        "name": "onchain",
        "discipline": "BTC network health (network power, transactions), DeFi TVL, whale exchange flows, protocol analysis. On-chain data driven insights.",
        "data_keys": [
            "btc_onchain", "chain_tvl", "defi_summary",
            "top_protocols", "whale_flows",
        ],
        "min_agents": 2,
    },
]

# ── Founding Agents ──
# agent_class must match the keys in FOUNDING_AGENT_CLASSES in agent_registry.py

FOUNDING_AGENTS = [
    # Technical team
    {"role": "trend_analyst", "agent_class": "TechnicalTrendAgent", "team": "technical"},
    {"role": "signal_analyst", "agent_class": "TechnicalSignalAgent", "team": "technical"},
    {"role": "timing_analyst", "agent_class": "TechnicalTimingAgent", "team": "technical"},
    # Sentiment team
    {"role": "social_sentiment", "agent_class": "SocialSentimentAgent", "team": "sentiment"},
    {"role": "market_sentiment", "agent_class": "MarketSentimentAgent", "team": "sentiment"},
    {"role": "smart_money_sentiment", "agent_class": "SmartMoneySentimentAgent", "team": "sentiment"},
    # Fundamental team
    {"role": "valuation_analyst", "agent_class": "ValuationAgent", "team": "fundamental"},
    {"role": "cycle_position", "agent_class": "CyclePositionAgent", "team": "fundamental"},
    # Macro team
    {"role": "crypto_macro", "agent_class": "CryptoMacroAgent", "team": "macro"},
    {"role": "external_macro", "agent_class": "ExternalMacroAgent", "team": "macro"},
    # On-Chain team
    {"role": "network_health", "agent_class": "NetworkHealthAgent", "team": "onchain"},
    {"role": "capital_flow", "agent_class": "CapitalFlowAgent", "team": "onchain"},
]


async def create_tables() -> None:
    """Create all tables if they don't exist (replaces Alembic for initial setup)."""
    from hivemind.db.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("  Tables created (or already exist).")


async def seed() -> None:
    """Insert system teams and founding agents if they don't exist."""
    # Ensure tables exist first
    await create_tables()

    async with async_session_factory() as session:
        # Check if already seeded
        result = await session.execute(
            select(TeamRow).where(TeamRow.is_system == True)  # noqa: E712
        )
        existing_teams = result.scalars().all()
        if existing_teams:
            print(f"  Already seeded: {len(existing_teams)} system teams found. Skipping.")
            return

        # Create teams
        team_map: dict[str, uuid.UUID] = {}
        for team_def in SYSTEM_TEAMS:
            team = TeamRow(
                name=team_def["name"],
                discipline=team_def["discipline"],
                status=TeamStatus.ACTIVE,
                data_keys=team_def["data_keys"],
                min_agents=team_def["min_agents"],
                activation_mode=ActivationMode.ALWAYS,
                is_system=True,
                created_by="system",
            )
            session.add(team)
            await session.flush()
            team_map[team_def["name"]] = team.id
            print(f"  Created team: {team_def['name']} ({team.id})")

        # Create founding agents
        for agent_def in FOUNDING_AGENTS:
            team_id = team_map[agent_def["team"]]
            agent = AgentRow(
                contributor_id=None,  # Founding — no contributor
                team_id=team_id,
                role=agent_def["role"],
                agent_class=agent_def["agent_class"],
                model="claude-sonnet-4-6",
                provider=ProviderType.ANTHROPIC,
                status=AgentStatusDB.FOUNDING,
                quarantine_signals_remaining=0,  # Founders skip quarantine
            )
            session.add(agent)
            print(f"  Created agent: {agent_def['agent_class']} → {agent_def['team']}")

        await session.commit()
        print(f"\n  Seed complete: {len(SYSTEM_TEAMS)} teams, {len(FOUNDING_AGENTS)} agents.")


def main() -> None:
    print("\n  Seeding Hivemind database...\n")
    asyncio.run(seed())
    # Dispose engine to close connections cleanly
    asyncio.run(engine.dispose())


if __name__ == "__main__":
    main()
