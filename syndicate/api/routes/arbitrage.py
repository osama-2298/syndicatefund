"""
Arbitrage API routes — exposes arbitrage engine status, positions, opportunities,
and live cross-exchange funding rate data.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Query

from syndicate.config import settings

router = APIRouter(tags=["arbitrage"])


# ── Funding Rate Scan Endpoints ──


@router.get("/arbitrage/funding-rates")
async def funding_rate_scan():
    """Get the latest cross-exchange funding rate comparison.

    Returns rates from Binance, OKX, Bybit, and Bitget with spread analysis.
    """
    path = Path(settings.funding_rate_scan_path)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {"status": "no_scan_yet", "opportunities": [], "all_rates": []}


@router.post("/arbitrage/funding-rates/scan")
async def trigger_funding_rate_scan():
    """Trigger an immediate funding rate scan across all exchanges.

    This runs synchronously and returns the results.
    Use sparingly — respects exchange rate limits.
    """
    from syndicate.data.funding_arb_scanner import FundingArbScanner

    with FundingArbScanner() as scanner:
        result = scanner.scan()
    return result


def _load_arb_portfolio() -> dict:
    """Load arbitrage portfolio state from JSON."""
    path = Path(settings.arb_portfolio_state_path)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {"cash": settings.arb_initial_cash, "positions": [], "total_realized_pnl": 0}


def _load_arb_opportunities() -> list[dict]:
    """Load recent arbitrage opportunities from JSON."""
    path = Path(settings.arb_opportunities_path)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return []


@router.get("/arbitrage/status")
async def arbitrage_status():
    """Get overall arbitrage engine status."""
    portfolio = _load_arb_portfolio()
    positions = portfolio.get("positions", [])
    open_positions = [p for p in positions if p.get("status") == "open"]

    by_strategy = {}
    for strat in ["funding_rate", "cross_exchange", "stat_arb"]:
        strat_positions = [p for p in positions if p.get("strategy") == strat]
        strat_open = [p for p in strat_positions if p.get("status") == "open"]
        by_strategy[strat] = {
            "total_positions": len(strat_positions),
            "open_positions": len(strat_open),
            "total_pnl": sum(_position_pnl(p) for p in strat_positions),
        }

    return {
        "enabled": settings.arb_enabled,
        "paper_mode": settings.arb_paper_trading,
        "strategies": {
            "funding_rate": {"enabled": settings.arb_funding_rate_enabled},
            "stat_arb": {"enabled": settings.arb_stat_arb_enabled},
            "cross_exchange": {"enabled": settings.arb_cross_exchange_enabled},
        },
        "portfolio": {
            "cash": portfolio.get("cash", 0),
            "total_value": portfolio.get("cash", 0) + sum(
                _position_unrealized(p) for p in open_positions
            ),
            "open_positions": len(open_positions),
            "total_realized_pnl": portfolio.get("total_realized_pnl", 0),
            "total_funding_collected": portfolio.get("total_funding_collected", 0),
            "total_fees_paid": portfolio.get("total_fees_paid", 0),
            "drawdown_pct": portfolio.get("drawdown_pct", 0),
        },
        "by_strategy": by_strategy,
    }


@router.get("/arbitrage/portfolio")
async def arbitrage_portfolio():
    """Get full arbitrage portfolio state."""
    return _load_arb_portfolio()


@router.get("/arbitrage/positions")
async def arbitrage_positions(
    strategy: str | None = Query(None),
    status: str | None = Query(None, regex="^(open|closed|liquidated)$"),
    limit: int = Query(50, ge=1, le=200),
):
    """Get arbitrage positions with optional filtering."""
    portfolio = _load_arb_portfolio()
    positions = portfolio.get("positions", [])

    if strategy:
        positions = [p for p in positions if p.get("strategy") == strategy]
    if status:
        positions = [p for p in positions if p.get("status") == status]

    # Sort by opened_at descending
    positions.sort(key=lambda p: p.get("opened_at", ""), reverse=True)

    return {
        "total": len(positions),
        "positions": positions[:limit],
    }


@router.get("/arbitrage/opportunities")
async def arbitrage_opportunities(
    strategy: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """Get recent arbitrage opportunities (acted on or not)."""
    opportunities = _load_arb_opportunities()

    if strategy:
        opportunities = [o for o in opportunities if o.get("strategy") == strategy]

    # Most recent first
    opportunities.sort(key=lambda o: o.get("detected_at", ""), reverse=True)

    return {
        "total": len(opportunities),
        "opportunities": opportunities[:limit],
    }


@router.get("/arbitrage/stats")
async def arbitrage_stats():
    """Get aggregated arbitrage statistics."""
    portfolio = _load_arb_portfolio()
    positions = portfolio.get("positions", [])
    opportunities = _load_arb_opportunities()

    total_positions = len(positions)
    closed = [p for p in positions if p.get("status") == "closed"]
    winners = [p for p in closed if _position_pnl(p) > 0]

    total_pnl = sum(_position_pnl(p) for p in positions)
    total_funding = portfolio.get("total_funding_collected", 0)
    total_fees = portfolio.get("total_fees_paid", 0)

    initial_cash = settings.arb_initial_cash
    current_value = portfolio.get("cash", initial_cash)
    return_pct = ((current_value - initial_cash) / initial_cash) * 100 if initial_cash else 0

    return {
        "total_positions": total_positions,
        "open_positions": len([p for p in positions if p.get("status") == "open"]),
        "closed_positions": len(closed),
        "win_rate": len(winners) / max(len(closed), 1),
        "total_pnl_usd": round(total_pnl, 2),
        "total_funding_collected": round(total_funding, 2),
        "total_fees_paid": round(total_fees, 2),
        "net_return_pct": round(return_pct, 2),
        "total_opportunities_detected": len(opportunities),
        "by_strategy": {
            strat: {
                "positions": len([p for p in positions if p.get("strategy") == strat]),
                "pnl": round(sum(_position_pnl(p) for p in positions if p.get("strategy") == strat), 2),
                "opportunities": len([o for o in opportunities if o.get("strategy") == strat]),
            }
            for strat in ["funding_rate", "cross_exchange", "stat_arb"]
        },
    }


def _position_pnl(position: dict) -> float:
    """Extract total PnL from a position dict."""
    funding = position.get("funding_collected_usd", 0) or 0
    fees = position.get("fees_paid_usd", 0) or 0

    # Calculate leg PnLs
    leg_a = position.get("leg_a", {})
    leg_b = position.get("leg_b", {})

    pnl_a = _leg_pnl(leg_a)
    pnl_b = _leg_pnl(leg_b)

    return pnl_a + pnl_b + funding - fees


def _position_unrealized(position: dict) -> float:
    """Calculate unrealized PnL for an open position."""
    if position.get("status") != "open":
        return 0
    return _position_pnl(position)


def _leg_pnl(leg: dict) -> float:
    """Calculate PnL for a single leg."""
    entry = leg.get("entry_price", 0) or 0
    current = leg.get("exit_price") or leg.get("current_price") or entry
    qty = leg.get("quantity", 0) or 0
    side = leg.get("side", "BUY")

    if side == "BUY":
        return (current - entry) * qty
    return (entry - current) * qty
