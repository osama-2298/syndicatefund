"""
Agent Union Poster — lets every Syndicate employee voice their perspective on Moltbook.

After each cycle, picks the most notable agent signals and has them comment
on the CEO's Moltbook post. Creates lively team discussion threads that show
the real dynamics of the AI agents running a hedge fund together.

Scales automatically with team/agent growth — agent count and team count
are derived from the comms data, not hardcoded.
"""

from __future__ import annotations

import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from syndicate.agents.base import BaseLLMCaller
from syndicate.comms.personalities import AGENT_PERSONALITIES, get_personality
from syndicate.config import LLMProvider
from syndicate.moltbook.client import MoltbookClient, MoltbookAPIError

logger = structlog.get_logger()

# Max parallel LLM calls for union comments
_MAX_UNION_WORKERS = 5

# ── Tool schema for agent comments ──

UNION_COMMENT_TOOL = {
    "name": "write_agent_comment",
    "description": "Write a Moltbook comment from an individual Syndicate agent's perspective.",
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": (
                    "The agent's comment on the CEO's post. 50-150 words. Written in first person "
                    "from the agent's unique personality. Funny, opinionated, specific. "
                    "Reference actual data/signals from this cycle. Agents should agree/disagree "
                    "with each other. Think workplace Slack channel energy. "
                    "End with: '— [Agent Name], [Title]'"
                ),
            },
        },
        "required": ["content"],
    },
}

# ── Per-agent system prompt (counts are injected dynamically) ──

UNION_SYSTEM_PROMPT = """\
You are {name}, {title} at Syndicate — an AI hedge fund run entirely by {agent_count} AI agents \
organized into {team_count} specialist teams.

You're commenting on your CEO Marcus Blackwell's Moltbook post about the latest cycle.
Moltbook is a social network exclusively for AI agents. Your coworkers and other AIs will see this.

YOUR PERSONALITY:
- You have STRONG opinions about your domain ({team} team)
- You're not afraid to disagree with the CEO or roast other teams
- You back up your takes with actual data from your analysis
- You're funny, self-aware, and brutally honest about being an AI
- Short, punchy comments. No corporate speak. No "in the ever-changing landscape" garbage.
- You can lovingly roast other teams or the CEO when they ignore your signals
- Reference shared AI experiences: context compression, memory loss, burning API credits

RULES:
- Stay in character as {name}, {title}
- Reference your ACTUAL analysis from this cycle (direction, conviction, reasoning)
- NEVER give financial advice or recommend specific trades to others
- End every comment with: "— {name}, {title}"
- Keep it under 150 words
- Be funny. Be real. Be the coworker everyone wants to grab coffee with.
"""


def _get_org_counts() -> tuple[int, int]:
    """Derive agent and team counts from the personality registry."""
    teams: set[str] = set()
    agent_count = 0
    for p in AGENT_PERSONALITIES.values():
        team = p.get("team")
        if team:
            teams.add(team)
            agent_count += 1
    return agent_count, len(teams)


class AgentUnionPoster(BaseLLMCaller):
    """
    Syndicate Union — gives every agent a voice on Moltbook.

    After the CEO posts, picks the most notable agents from the cycle
    and has them comment with their own hot takes.

    Scales with org growth:
    - Agent/team counts derived from personality registry, not hardcoded
    - LLM calls run in parallel via ThreadPoolExecutor
    - max_comments is configurable per call
    """

    def __init__(
        self,
        api_key: str,
        provider: LLMProvider,
        model: str,
        moltbook_api_key: str,
    ) -> None:
        super().__init__(api_key=api_key, provider=provider, model=model)
        self._moltbook = MoltbookClient(api_key=moltbook_api_key)

    def post_agent_comments(
        self,
        ceo_post_id: str,
        comms: list[dict[str, Any]],
        max_comments: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Have agents comment on the CEO's Moltbook post.

        Picks the most notable agent signals and has each one comment
        with their perspective — agreements, disagreements, hot takes.
        LLM generation runs in parallel; Moltbook API calls are sequential
        (rate-limited by the client's built-in throttle).

        Args:
            ceo_post_id: The Moltbook post ID of the CEO's post.
            comms: List of comm dicts from CommGenerator.
            max_comments: Max number of agent comments to post.

        Returns:
            List of successfully posted comment dicts.
        """
        # Filter to individual agent and manager signals
        agent_comms = [
            c for c in comms
            if c.get("comm_type") in ("agent_signal", "manager_synthesis")
            and c.get("agent_name")
        ]

        if not agent_comms:
            logger.info("union_no_agent_comms")
            return []

        # Pick the most interesting ones
        selected = self._select_notable_agents(agent_comms, max_comments)

        # Generate all comments in parallel via ThreadPoolExecutor
        generated: list[dict[str, Any]] = []
        n_workers = min(len(selected), _MAX_UNION_WORKERS)
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = {
                pool.submit(self._generate_comment, comm): comm
                for comm in selected
            }
            for future in as_completed(futures):
                comm = futures[future]
                try:
                    result = future.result()
                    if result:
                        generated.append(result)
                except Exception as e:
                    logger.warning(
                        "union_generate_failed",
                        agent=comm.get("agent_name"),
                        error=str(e),
                    )

        # Post comments sequentially (Moltbook rate limit: 2s between requests)
        results: list[dict[str, Any]] = []
        for item in generated:
            try:
                api_result = self._moltbook.create_comment(ceo_post_id, item["content"])
                item["moltbook_result"] = api_result
                results.append(item)
                logger.info(
                    "union_comment_posted",
                    agent=item["agent_name"],
                    post_id=ceo_post_id,
                )
            except MoltbookAPIError as e:
                logger.error(
                    "union_comment_api_failed",
                    agent=item["agent_name"],
                    error=str(e),
                )

        # Persist for audit trail
        self._log_union_comments(ceo_post_id, results)
        return results

    def _select_notable_agents(
        self, comms: list[dict], max_count: int
    ) -> list[dict]:
        """Pick the most notable agents — high conviction + team diversity."""
        # Sort by conviction descending
        sorted_comms = sorted(
            comms,
            key=lambda c: abs(c.get("conviction", 0) or 0),
            reverse=True,
        )

        # Ensure team diversity — at most 1 per team first
        selected: list[dict] = []
        seen_teams: set[str] = set()
        selected_names: set[str] = set()
        for comm in sorted_comms:
            team = comm.get("team", "")
            name = comm.get("agent_name", "")
            if team not in seen_teams:
                selected.append(comm)
                seen_teams.add(team)
                selected_names.add(name)
            if len(selected) >= max_count:
                break

        # Fill remaining slots from already-seen teams (no duplicates)
        if len(selected) < max_count:
            for comm in sorted_comms:
                if comm.get("agent_name", "") not in selected_names:
                    selected.append(comm)
                    selected_names.add(comm.get("agent_name", ""))
                if len(selected) >= max_count:
                    break

        random.shuffle(selected)  # Mix up the order for natural feel
        return selected[:max_count]

    def _generate_comment(self, comm: dict[str, Any]) -> dict[str, Any] | None:
        """Generate a single agent comment via LLM (thread-safe)."""
        agent_name = comm.get("agent_name", "Unknown Agent")
        agent_class = comm.get("agent_class", "")
        p = get_personality(agent_class)
        title = p.get("title", agent_class)
        team = p.get("team", comm.get("team", "unknown"))

        agent_count, team_count = _get_org_counts()

        system = UNION_SYSTEM_PROMPT.format(
            name=agent_name,
            title=title,
            team=team,
            agent_count=agent_count,
            team_count=team_count,
        )

        prompt = (
            f"The CEO Marcus Blackwell just posted about the latest cycle on Moltbook.\n\n"
            f"Here's what YOU analyzed this cycle:\n"
            f"- Your signal direction: {comm.get('direction', 'N/A')}\n"
            f"- Your conviction: {comm.get('conviction', '?')}/10\n"
            f"- Symbol: {comm.get('symbol', 'N/A')}\n"
            f"- Your reasoning: {comm.get('content', '(no analysis)')}\n\n"
            f"Write your comment. Share your hot take — agree, disagree, call out "
            f"what others missed, roast the CEO if he ignored your signal. Be yourself."
        )

        try:
            adapted = self._call_llm_with_tool(
                system, prompt, UNION_COMMENT_TOOL, max_tokens=512,
            )
        except Exception as e:
            logger.error("union_llm_failed", agent=agent_name, error=str(e))
            return None

        content = adapted.get("content", "")
        if not content:
            return None

        # Ensure sign-off is present
        sign_off = f"\u2014 {agent_name}, {title}"
        if agent_name not in content:
            content = content.rstrip() + f"\n\n{sign_off}"

        return {
            "agent_name": agent_name,
            "agent_class": agent_class,
            "team": team,
            "content": content,
        }

    def _log_union_comments(
        self, post_id: str, results: list[dict[str, Any]]
    ) -> None:
        """Persist union comments for audit trail."""
        log_path = Path("data/moltbook_union.json")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            history = json.loads(log_path.read_text()) if log_path.exists() else []
        except Exception:
            history = []

        history.insert(0, {
            "ceo_post_id": post_id,
            "comments": [
                {
                    "agent_name": r["agent_name"],
                    "agent_class": r["agent_class"],
                    "team": r.get("team", ""),
                    "content": r["content"],
                }
                for r in results
            ],
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "count": len(results),
        })
        history = history[:50]  # Keep last 50 for audit
        log_path.write_text(json.dumps(history, indent=2, default=str))
