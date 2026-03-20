"""Polymarket Weather Oracle API routes."""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from fastapi import APIRouter

from syndicate.polymarket.oracle import get_oracle
from syndicate.polymarket.constants import CITY_STATIONS
from syndicate.polymarket.markets.edge import compute_horizon_hours

logger = structlog.get_logger()

router = APIRouter(prefix="/polymarket", tags=["polymarket"])


@router.get("/status")
async def get_status():
    """Oracle running status, last scan time, portfolio value, uptime."""
    oracle = get_oracle()
    return oracle.status.model_dump(mode="json")


@router.get("/markets")
async def get_markets():
    """All discovered weather markets with current prices."""
    oracle = get_oracle()
    markets = oracle._last_markets

    if not markets:
        return {"markets": [], "count": 0}

    def _sanitize_market(m):
        d = m.model_dump(mode="json")
        # Replace inf/-inf with None (JSON can't serialize infinity)
        for b in d.get("bins", []):
            if b.get("lower") is not None and (b["lower"] == float("inf") or b["lower"] == float("-inf")):
                b["lower"] = None
            if b.get("upper") is not None and (b["upper"] == float("inf") or b["upper"] == float("-inf")):
                b["upper"] = None
        return d

    return {
        "markets": [_sanitize_market(m) for m in markets],
        "count": len(markets),
    }


@router.get("/portfolio")
async def get_portfolio():
    """Current portfolio: cash, positions, P&L, win rate."""
    oracle = get_oracle()
    portfolio = oracle.trader.get_portfolio()
    data = portfolio.model_dump(mode="json")
    # Include computed properties that model_dump doesn't serialize
    data["win_rate"] = portfolio.win_rate
    data["total_value"] = portfolio.total_value
    return data


@router.get("/trades")
async def get_trades():
    """All trades (open + resolved) with P&L and summary stats."""
    oracle = get_oracle()
    portfolio = oracle.trader.get_portfolio()

    open_positions = [p for p in portfolio.positions if not p.resolved]
    resolved_positions = [p for p in portfolio.positions if p.resolved]

    return {
        "open": [p.model_dump(mode="json") for p in open_positions],
        "resolved": [p.model_dump(mode="json") for p in resolved_positions],
        "stats": {
            "total_bets": portfolio.total_bets,
            "wins": portfolio.wins,
            "losses": portfolio.losses,
            "win_rate": portfolio.win_rate,
            "total_pnl": portfolio.total_pnl,
        },
    }


@router.get("/forecasts/{city}")
async def get_forecast(city: str):
    """Latest ensemble forecast for a city.

    Runs a fresh forecast fetch if the oracle has a matching market,
    otherwise returns cached data from the last cycle.
    """
    oracle = get_oracle()

    # Find city config
    config = CITY_STATIONS.get(city)
    if not config:
        # Try case-insensitive / partial match
        for key, cfg in CITY_STATIONS.items():
            if key.lower() == city.lower():
                config = cfg
                city = key
                break
    if not config:
        return {"error": f"Unknown city: {city}", "available": list(CITY_STATIONS.keys())}

    # Find a market for this city to get bins
    market = None
    for m in oracle._last_markets:
        if m.city.lower() == city.lower():
            market = m
            break

    if not market:
        return {
            "city": city,
            "message": "No active market found for this city",
            "station": config.model_dump(),
        }

    # Return market bin data (no live API call — uses cached data from last oracle cycle)
    return {
        "city": city,
        "date": market.date,
        "bins": [
            {"label": b.label, "lower": b.lower, "upper": b.upper, "market_price": b.market_price}
            for b in market.bins
        ],
        "total_volume": market.total_volume,
        "station": config.model_dump(),
    }


@router.get("/opportunities")
async def get_opportunities():
    """Current edge opportunities from the last oracle cycle (no live API calls)."""
    oracle = get_oracle()
    portfolio = oracle.trader.get_portfolio()

    # Return open positions as "opportunities" — these are the edges the oracle found
    open_positions = [p for p in portfolio.positions if not p.resolved]
    opportunities = [
        {
            "city": p.city,
            "date": p.date,
            "bin_label": p.bin_label,
            "model_prob": p.model_prob,
            "market_price": p.entry_price,
            "edge": p.edge_at_entry,
            "quantity": p.quantity,
        }
        for p in open_positions
    ]

    return {
        "opportunities": sorted(opportunities, key=lambda x: x.get("edge", 0), reverse=True),
        "count": len(opportunities),
    }


@router.get("/calibration")
async def get_calibration():
    """Calibration quality metrics: Brier scores, MAE, reliability."""
    try:
        oracle = get_oracle()
        return oracle._calibration_tracker.summary()
    except Exception as e:
        logger.error("calibration_endpoint_failed", error=str(e))
        return {"error": str(e), "records": 0}


@router.get("/calibration/reliability")
async def get_reliability():
    """Reliability diagram data — predicted vs observed frequency."""
    try:
        oracle = get_oracle()
        cal = oracle._calibration_tracker
        return {"reliability": cal.reliability(), "total_records": len(cal._records)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/timing")
async def get_timing():
    """Model run timing info — next release, optimal interval, fresh data window."""
    try:
        from syndicate.polymarket.markets.timing import (
            next_model_release, is_fresh_data_window, optimal_scan_interval
        )
        release = next_model_release()
        return {
            "next_release": {
                "model": release["model"],
                "available_at": release["available_at"].isoformat() if release.get("available_at") else None,
                "minutes_until": round(release.get("minutes_until", 0), 1),
            },
            "is_fresh_window": is_fresh_data_window(),
            "optimal_interval_seconds": optimal_scan_interval(),
        }
    except Exception as e:
        return {"error": str(e)}
