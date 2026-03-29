"""
DATA.md Auto-Updater — keeps the master knowledge base current.

This module is responsible for periodically updating the DATA.md file
with the latest market intelligence so that all agents have access to
current macro conditions, recent events, and updated sector dynamics.

It can be triggered:
  1. On a schedule (daily/weekly via the pipeline or cron)
  2. Manually via the API endpoint POST /api/v1/data/refresh
  3. Programmatically by calling refresh_data_file()

The updater APPENDS a dated "LATEST UPDATES" section to DATA.md
rather than rewriting the entire file, preserving the core reference
material while adding fresh context.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

DATA_FILE = Path(__file__).resolve().parents[2] / "DATA.md"


def refresh_data_file(
    market_snapshot: dict[str, Any] | None = None,
    macro_summary: str | None = None,
    sector_alerts: list[dict[str, str]] | None = None,
    crypto_signals: dict[str, Any] | None = None,
    custom_notes: str | None = None,
) -> bool:
    """
    Update DATA.md with the latest market intelligence.

    This function appends or replaces the "LATEST UPDATES" section at the
    bottom of DATA.md with fresh data. The core reference material above
    that section is never modified.

    Parameters
    ----------
    market_snapshot : dict, optional
        Current market conditions (VIX, DXY, 10Y yield, S&P level, etc.)
    macro_summary : str, optional
        Plain-text summary of current macro regime and recent events.
    sector_alerts : list[dict], optional
        List of sector-specific alerts, each with 'sector', 'event', 'impact'.
    crypto_signals : dict, optional
        Current crypto on-chain signals (BTC dominance, funding rates, etc.)
    custom_notes : str, optional
        Any additional analyst notes to include.

    Returns
    -------
    bool
        True if the file was successfully updated.
    """
    try:
        if not DATA_FILE.exists():
            logger.error("data_file_missing", path=str(DATA_FILE))
            return False

        content = DATA_FILE.read_text(encoding="utf-8")

        # Remove previous LATEST UPDATES section if present
        marker = "---\n\n# LATEST UPDATES"
        if marker in content:
            content = content[: content.index(marker)]

        # Build the update section
        now = datetime.now(timezone.utc)
        update_lines = [
            "---",
            "",
            "# LATEST UPDATES",
            f"*Auto-updated: {now.strftime('%Y-%m-%d %H:%M UTC')}*",
            "",
        ]

        # Market snapshot
        if market_snapshot:
            update_lines.append("## Current Market Conditions")
            update_lines.append("")
            update_lines.append("| Metric | Value |")
            update_lines.append("|--------|-------|")
            for key, val in market_snapshot.items():
                label = key.replace("_", " ").title()
                update_lines.append(f"| {label} | {val} |")
            update_lines.append("")

        # Macro summary
        if macro_summary:
            update_lines.append("## Macro Regime Summary")
            update_lines.append("")
            update_lines.append(macro_summary)
            update_lines.append("")

        # Sector alerts
        if sector_alerts:
            update_lines.append("## Active Sector Alerts")
            update_lines.append("")
            update_lines.append("| Sector | Event | Impact |")
            update_lines.append("|--------|-------|--------|")
            for alert in sector_alerts:
                update_lines.append(
                    f"| {alert.get('sector', 'N/A')} "
                    f"| {alert.get('event', 'N/A')} "
                    f"| {alert.get('impact', 'N/A')} |"
                )
            update_lines.append("")

        # Crypto signals
        if crypto_signals:
            update_lines.append("## Current Crypto On-Chain Signals")
            update_lines.append("")
            update_lines.append("| Signal | Value | Interpretation |")
            update_lines.append("|--------|-------|----------------|")
            for key, val in crypto_signals.items():
                if isinstance(val, dict):
                    value = val.get("value", "N/A")
                    interp = val.get("interpretation", "")
                else:
                    value = val
                    interp = ""
                label = key.replace("_", " ").title()
                update_lines.append(f"| {label} | {value} | {interp} |")
            update_lines.append("")

        # Custom notes
        if custom_notes:
            update_lines.append("## Analyst Notes")
            update_lines.append("")
            update_lines.append(custom_notes)
            update_lines.append("")

        # Write back
        updated = content.rstrip() + "\n\n" + "\n".join(update_lines) + "\n"
        DATA_FILE.write_text(updated, encoding="utf-8")

        logger.info(
            "data_file_updated",
            path=str(DATA_FILE),
            sections_added=sum([
                bool(market_snapshot),
                bool(macro_summary),
                bool(sector_alerts),
                bool(crypto_signals),
                bool(custom_notes),
            ]),
        )

        # Reload the in-memory knowledge base so agents pick up changes
        try:
            from syndicate.agents.base import reload_data_kb
            reload_data_kb()
            logger.info("data_kb_reloaded_in_memory")
        except ImportError:
            pass

        return True

    except Exception as e:
        logger.error("data_file_update_failed", error=str(e))
        return False


def build_snapshot_from_pipeline(
    fear_greed: dict | None = None,
    global_market: dict | None = None,
    portfolio_value: float | None = None,
) -> dict[str, Any]:
    """
    Build a market_snapshot dict from pipeline data for refresh_data_file().

    Call this at the end of each pipeline cycle to auto-update DATA.md.
    """
    snapshot: dict[str, Any] = {}

    if fear_greed:
        snapshot["fear_greed_index"] = fear_greed.get("value", "N/A")
        snapshot["fear_greed_label"] = fear_greed.get("value_classification", "N/A")

    if global_market:
        snapshot["total_crypto_mcap"] = global_market.get(
            "total_market_cap_usd", "N/A"
        )
        snapshot["btc_dominance"] = global_market.get("btc_dominance_pct", "N/A")

    if portfolio_value is not None:
        snapshot["portfolio_value"] = f"${portfolio_value:,.2f}"

    return snapshot
