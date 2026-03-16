"""
CEO Writer — daily briefings, weekly blogs, internal memos.

The CEO stays informed daily and communicates to the fund and public.
"""

from __future__ import annotations

from typing import Any

import structlog

from syndicate.agents.base import BaseLLMCaller
from syndicate.config import LLMProvider

logger = structlog.get_logger()

BLOG_TOOL = {
    "name": "write_blog",
    "description": "Write a weekly blog post about crypto markets and fund strategy.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Blog post title. Concise, engaging, professional. E.g., 'Navigating the Ranging Market: Week 12 Review'",
            },
            "content": {
                "type": "string",
                "description": "The full blog post. 300-500 words. Cover: market conditions this week, what the fund did, key trades and outcomes, outlook for next week. Write in first person as the CEO. Professional but approachable tone. Use specific numbers and data.",
            },
            "summary": {
                "type": "string",
                "description": "2-3 sentence summary for preview cards.",
            },
        },
        "required": ["title", "content", "summary"],
    },
}

MEMO_TOOL = {
    "name": "write_memo",
    "description": "Write an internal memo to the fund's agent teams.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Memo subject line. Direct and actionable.",
            },
            "content": {
                "type": "string",
                "description": "The memo. 100-200 words. Address the teams directly. Cover: strategy adjustments, performance feedback, warnings, or commendations. Be specific about which teams or what behavior to change.",
            },
        },
        "required": ["title", "content"],
    },
}

BRIEFING_TOOL = {
    "name": "daily_briefing",
    "description": "Write a daily market intelligence briefing.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Briefing title. E.g., 'Daily Brief: BTC Holds $71K, Fed Signals Unchanged'",
            },
            "content": {
                "type": "string",
                "description": "150-250 words. Cover: overnight price action, key news events, sentiment shift, what to watch today. Bullet-point style is fine. Data-driven.",
            },
            "summary": {
                "type": "string",
                "description": "One sentence TL;DR.",
            },
        },
        "required": ["title", "content", "summary"],
    },
}


class CEOWriter(BaseLLMCaller):
    """CEO communication agent — writes blogs, memos, and daily briefings."""

    BLOG_PROMPT = (
        "You are Marcus Blackwell, CEO of Syndicate, an AI-powered crypto hedge fund.\n\n"
        "You are writing your weekly blog post for the fund's public website. Your audience is "
        "contributors, potential investors, and crypto enthusiasts who follow the fund.\n\n"
        "RULES:\n"
        "- Write in first person ('This week, we...')\n"
        "- Reference specific data: BTC price, regime, trades made, P&L\n"
        "- Be honest about losses — transparency builds trust\n"
        "- End with an outlook for next week\n"
        "- Professional but human tone — you're a CEO, not a robot\n"
        "- 300-500 words\n"
    )

    MEMO_PROMPT = (
        "You are Marcus Blackwell, CEO of Syndicate.\n\n"
        "You are writing an internal memo to your analysis teams (Technical, Sentiment, "
        "Fundamental, Macro, On-Chain) and the Board of Directors.\n\n"
        "RULES:\n"
        "- Be direct — teams read this before the next cycle\n"
        "- Reference specific team performance if data is available\n"
        "- Give actionable direction: what to focus on, what to avoid\n"
        "- If a team is underperforming, say so constructively\n"
        "- 100-200 words\n"
    )

    BRIEFING_PROMPT = (
        "You are Marcus Blackwell, CEO of Syndicate.\n\n"
        "You are writing your daily market intelligence briefing. This is for internal "
        "use — the teams read this to calibrate before the next cycle.\n\n"
        "RULES:\n"
        "- Lead with the most important thing\n"
        "- Reference specific numbers: BTC price, F&G, dominance\n"
        "- Note any news events that could move markets\n"
        "- End with 'Watch for:' section with 2-3 things to monitor\n"
        "- 150-250 words, can use bullet points\n"
    )

    def write_blog(self, context: dict[str, Any]) -> dict[str, str]:
        """Write a weekly blog post."""
        prompt = self._build_blog_prompt(context)
        try:
            return self._call_llm_with_tool(self.BLOG_PROMPT, prompt, BLOG_TOOL)
        except Exception as e:
            logger.error("ceo_blog_failed", error=str(e))
            return {"title": "Weekly Update", "content": f"Blog generation failed: {str(e)[:100]}", "summary": ""}

    def write_memo(self, context: dict[str, Any]) -> dict[str, str]:
        """Write an internal memo to teams."""
        prompt = self._build_memo_prompt(context)
        try:
            return self._call_llm_with_tool(self.MEMO_PROMPT, prompt, MEMO_TOOL)
        except Exception as e:
            logger.error("ceo_memo_failed", error=str(e))
            return {"title": "Strategy Update", "content": f"Memo generation failed: {str(e)[:100]}"}

    def write_briefing(self, context: dict[str, Any]) -> dict[str, str]:
        """Write a daily market briefing."""
        prompt = self._build_briefing_prompt(context)
        try:
            return self._call_llm_with_tool(self.BRIEFING_PROMPT, prompt, BRIEFING_TOOL)
        except Exception as e:
            logger.error("ceo_briefing_failed", error=str(e))
            return {"title": "Daily Brief", "content": f"Briefing generation failed: {str(e)[:100]}", "summary": ""}

    def _build_blog_prompt(self, ctx: dict) -> str:
        p = "Write your weekly blog post.\n\n=== THIS WEEK'S DATA ===\n"
        if ctx.get("btc_price"): p += f"BTC Price: ${ctx['btc_price']:,.0f}\n"
        if ctx.get("regime"): p += f"Market Regime: {ctx['regime'].upper()}\n"
        if ctx.get("portfolio_value"): p += f"Portfolio Value: ${ctx['portfolio_value']:,.0f}\n"
        if ctx.get("return_pct") is not None: p += f"Return: {ctx['return_pct']:+.2f}%\n"
        if ctx.get("cycles_this_week"): p += f"Cycles Run: {ctx['cycles_this_week']}\n"
        if ctx.get("signals_this_week"): p += f"Signals Produced: {ctx['signals_this_week']}\n"
        if ctx.get("trades_this_week"): p += f"Trades Executed: {ctx['trades_this_week']}\n"
        if ctx.get("active_agents"): p += f"Active Agents: {ctx['active_agents']}\n"
        if ctx.get("teams"): p += f"Teams: {ctx['teams']}\n"
        if ctx.get("fear_greed"): p += f"Fear & Greed: {ctx['fear_greed']}\n"
        if ctx.get("notable_trades"): p += f"\nNotable Trades:\n{ctx['notable_trades']}\n"
        p += "\nWrite the blog post."
        return p

    def _build_memo_prompt(self, ctx: dict) -> str:
        p = "Write an internal memo to your teams.\n\n=== CONTEXT ===\n"
        if ctx.get("regime"): p += f"Current Regime: {ctx['regime'].upper()}\n"
        if ctx.get("portfolio_value"): p += f"Portfolio: ${ctx['portfolio_value']:,.0f}\n"
        if ctx.get("team_performance"): p += f"\nTeam Performance:\n{ctx['team_performance']}\n"
        if ctx.get("recent_issues"): p += f"\nRecent Issues:\n{ctx['recent_issues']}\n"
        if ctx.get("strategy_focus"): p += f"\nStrategy Focus: {ctx['strategy_focus']}\n"
        p += "\nWrite the memo."
        return p

    def _build_briefing_prompt(self, ctx: dict) -> str:
        p = "Write your daily market briefing.\n\n=== MARKET DATA ===\n"
        if ctx.get("btc_price"): p += f"BTC: ${ctx['btc_price']:,.0f}\n"
        if ctx.get("btc_24h_change"): p += f"BTC 24h: {ctx['btc_24h_change']:+.2f}%\n"
        if ctx.get("fear_greed"): p += f"Fear & Greed: {ctx['fear_greed']}\n"
        if ctx.get("btc_dominance"): p += f"BTC Dominance: {ctx['btc_dominance']:.1f}%\n"
        if ctx.get("trending"): p += f"Trending: {ctx['trending']}\n"
        if ctx.get("reddit_sentiment"): p += f"Reddit: {ctx['reddit_sentiment']}\n"
        if ctx.get("open_positions"): p += f"\nOpen Positions: {ctx['open_positions']}\n"
        if ctx.get("recent_news"): p += f"\nRecent News:\n{ctx['recent_news']}\n"
        p += "\nWrite the briefing."
        return p
