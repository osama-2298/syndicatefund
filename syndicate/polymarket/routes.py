"""Polymarket Weather Oracle API routes."""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from fastapi import APIRouter

from syndicate.polymarket.oracle import get_oracle
from syndicate.polymarket.constants import CITY_STATIONS
from syndicate.polymarket.markets.edge import detect_edges, compute_horizon_hours
from syndicate.polymarket.forecast.ensemble import blend_ensembles
from syndicate.polymarket.forecast.probability import compute_bin_probabilities
from syndicate.polymarket.models import MarketAnalysis

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

    return {
        "markets": [m.model_dump(mode="json") for m in markets],
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

    # Fetch fresh ensemble forecast
    try:
        from syndicate.polymarket.data.open_meteo import fetch_ensemble_forecast

        forecast = await fetch_ensemble_forecast(
            city=city,
            lat=config.latitude,
            lon=config.longitude,
            unit=config.unit,
            target_date=market.date,
        )

        blend = blend_ensembles(forecast)
        bin_probs = compute_bin_probabilities(forecast, market.bins)

        return {
            "city": city,
            "date": market.date,
            "n_members": len(forecast.members),
            "mean": round(blend["mean"], 2),
            "std": round(blend["std"], 2),
            "agreement": round(blend["agreement"], 3),
            "model_counts": blend["model_counts"],
            "model_means": {k: round(v, 2) for k, v in blend["model_means"].items()},
            "bin_probabilities": [bp.model_dump() for bp in bin_probs],
        }
    except Exception as e:
        logger.error("forecast_endpoint_failed", city=city, error=str(e))
        return {"city": city, "error": str(e)}


@router.get("/opportunities")
async def get_opportunities():
    """Current edge opportunities — bins where model_prob > market_price by threshold."""
    oracle = get_oracle()
    opportunities: list[dict] = []

    for market in oracle._last_markets:
        config = CITY_STATIONS.get(market.city)
        if not config:
            continue

        horizon = compute_horizon_hours(market.date)
        if horizon < 0 or horizon > oracle.settings.polymarket_max_horizon_hours:
            continue

        try:
            from syndicate.polymarket.data.open_meteo import fetch_ensemble_forecast

            forecast = await fetch_ensemble_forecast(
                city=market.city,
                lat=config.latitude,
                lon=config.longitude,
                unit=config.unit,
                target_date=market.date,
            )
            if not forecast.members:
                continue

            bin_probs = compute_bin_probabilities(forecast, market.bins)
            blend = blend_ensembles(forecast)

            analysis = MarketAnalysis(
                condition_id=market.condition_id,
                city=market.city,
                date=market.date,
                horizon_hours=horizon,
                forecast_mean=blend["mean"],
                forecast_std=blend["std"],
                bin_probabilities=bin_probs,
                best_edge=max((bp.edge for bp in bin_probs), default=0),
                best_edge_bin=(
                    max(bin_probs, key=lambda bp: bp.edge).bin_index
                    if bin_probs
                    else 0
                ),
                analyzed_at=datetime.now(timezone.utc),
            )

            edges = detect_edges(analysis)
            for e in edges:
                opportunities.append({
                    "city": market.city,
                    "date": market.date,
                    "condition_id": market.condition_id,
                    "horizon_hours": round(horizon, 1),
                    **e.model_dump(),
                })

        except Exception as exc:
            logger.error(
                "opportunities_endpoint_failed",
                city=market.city,
                date=market.date,
                error=str(exc),
            )

    return {
        "opportunities": sorted(opportunities, key=lambda x: x["edge"], reverse=True),
        "count": len(opportunities),
    }


@router.get("/calibration")
async def get_calibration():
    """Calibration quality metrics: Brier scores, MAE, reliability."""
    try:
        from syndicate.polymarket.resolution.calibration import CalibrationTracker
        cal = CalibrationTracker()
        return cal.summary()
    except Exception as e:
        logger.error("calibration_endpoint_failed", error=str(e))
        return {"error": str(e), "records": 0}


@router.get("/calibration/reliability")
async def get_reliability():
    """Reliability diagram data — predicted vs observed frequency."""
    try:
        from syndicate.polymarket.resolution.calibration import CalibrationTracker
        cal = CalibrationTracker()
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
