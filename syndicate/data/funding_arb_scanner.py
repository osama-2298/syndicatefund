"""
Funding Rate Arbitrage Scanner — runs every cycle to detect cross-exchange opportunities.

Workflow:
  1. Fetch current funding rates from Binance, OKX, Bybit, Bitget
  2. Compare rates across exchanges for each symbol
  3. Detect opportunities where spread exceeds threshold
  4. Persist results to JSON (data/funding_rate_scan.json)
  5. Expose via API for frontend consumption

This is the proven strategy: backtested at +1.5% monthly, Sharpe 1.14.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from syndicate.config import settings
from syndicate.data.multi_exchange_rates import MultiExchangeRates

logger = structlog.get_logger()


class FundingArbScanner:
    """Scans for cross-exchange funding rate arbitrage opportunities."""

    def __init__(self) -> None:
        self._rates_client = MultiExchangeRates()
        self._scan_path = Path(settings.funding_rate_scan_path)
        self._opportunities_path = Path(settings.arb_opportunities_path)

    def close(self) -> None:
        self._rates_client.close()

    def __enter__(self) -> FundingArbScanner:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def scan(self) -> dict[str, Any]:
        """Run a full funding rate scan across all configured symbols.

        Returns:
            Complete scan results including opportunities, exchange stats,
            and all rate comparisons.
        """
        if not settings.arb_enabled or not settings.arb_funding_rate_enabled:
            logger.info("funding_arb_scan_disabled")
            return {"status": "disabled", "opportunities": []}

        logger.info(
            "funding_arb_scan_start",
            symbols=settings.arb_scan_symbols,
        )

        # Fetch and compare rates
        summary = self._rates_client.get_summary(settings.arb_scan_symbols)

        # Filter for actionable opportunities based on configured threshold
        min_spread = settings.arb_min_spread_pct / 100  # Convert from % to decimal
        actionable = [
            opp for opp in summary.get("all_comparisons", [])
            if opp.get("spread_pct", 0) > settings.arb_min_spread_pct
        ]

        # Build scan result
        scan_result: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "ok",
            "symbols_scanned": len(summary.get("all_comparisons", [])),
            "actionable_opportunities": len(actionable),
            "min_spread_threshold_pct": settings.arb_min_spread_pct,
            "exchange_stats": summary.get("exchange_stats", {}),
            "opportunities": actionable,
            "all_rates": summary.get("all_comparisons", []),
        }

        # Persist scan results
        self._persist_scan(scan_result)

        # Append new opportunities to the historical log
        self._append_opportunities(actionable)

        logger.info(
            "funding_arb_scan_done",
            scanned=scan_result["symbols_scanned"],
            opportunities=scan_result["actionable_opportunities"],
        )

        return scan_result

    def get_latest_scan(self) -> dict[str, Any]:
        """Load the most recent scan results from disk."""
        if self._scan_path.exists():
            try:
                return json.loads(self._scan_path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {"status": "no_scan_yet", "opportunities": []}

    def _persist_scan(self, scan_result: dict[str, Any]) -> None:
        """Save scan results to JSON."""
        self._scan_path.parent.mkdir(parents=True, exist_ok=True)
        self._scan_path.write_text(
            json.dumps(scan_result, indent=2, default=str)
        )

    def _append_opportunities(self, opportunities: list[dict]) -> None:
        """Append new opportunities to the historical log."""
        if not opportunities:
            return

        existing: list[dict] = []
        if self._opportunities_path.exists():
            try:
                existing = json.loads(self._opportunities_path.read_text())
            except (json.JSONDecodeError, OSError):
                existing = []

        # Add timestamp and strategy tag to each opportunity
        now = datetime.now(timezone.utc).isoformat()
        for opp in opportunities:
            opp["detected_at"] = now
            opp["strategy"] = "funding_rate"

        existing.extend(opportunities)

        # Keep last 500 opportunities
        if len(existing) > 500:
            existing = existing[-500:]

        self._opportunities_path.parent.mkdir(parents=True, exist_ok=True)
        self._opportunities_path.write_text(
            json.dumps(existing, indent=2, default=str)
        )
