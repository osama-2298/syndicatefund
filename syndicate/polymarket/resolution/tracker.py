"""Resolution tracking — check resolved markets and compute P&L."""

from __future__ import annotations

import re

import structlog
from datetime import datetime, timezone

from syndicate.polymarket.execution.paper_trader import WeatherPaperTrader
from syndicate.polymarket.models import TemperatureBin, TemperatureUnit, WeatherMarket
from syndicate.polymarket.constants import CITY_STATIONS

logger = structlog.get_logger()


async def check_resolutions(
    trader: WeatherPaperTrader,
    markets: list[WeatherMarket],
) -> list[dict]:
    """Check if any open positions have resolved.

    For each unresolved position:
    1. Check if the market date has passed
    2. Fetch actual temperature from Wunderground
    3. Determine which bin the actual temp falls in
    4. Resolve the position (won/lost)

    Returns list of resolution results.
    """
    # Import here to avoid circular imports and allow the module to be
    # optional if wunderground isn't available yet.
    from syndicate.polymarket.data.wunderground import fetch_actual_high

    results: list[dict] = []
    portfolio = trader.get_portfolio()

    for pos in portfolio.positions:
        if pos.resolved:
            continue

        # Check if date has passed (need at least 1 day after for WU data)
        target = datetime.strptime(pos.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if now < target.replace(hour=23, minute=59):
            continue  # Market day hasn't ended yet

        # Find city config
        city_key = pos.city
        config = CITY_STATIONS.get(city_key)
        if not config:
            # Try partial match
            for key, cfg in CITY_STATIONS.items():
                if key.lower() in city_key.lower() or city_key.lower() in key.lower():
                    config = cfg
                    break
        if not config:
            logger.warning("unknown_city_for_resolution", city=pos.city)
            continue

        # Fetch actual temperature
        actual = await fetch_actual_high(
            icao=config.icao,
            wunderground_path=config.wunderground_url,
            date=pos.date,
            unit=config.unit,
        )
        if actual is None:
            logger.info("actual_temp_not_available", city=pos.city, date=pos.date)
            continue

        # Find the market to determine which bin won
        market = None
        for m in markets:
            if m.condition_id == pos.condition_id:
                market = m
                break

        if market:
            won = _actual_in_bin_from_market(actual, pos.bin_label, market.bins)
        else:
            # Determine from position data alone
            won = _actual_in_bin(actual, pos.bin_label, config.unit)

        # Resolve
        pnl = trader.resolve_position(pos.condition_id, won)
        results.append({
            "city": pos.city,
            "date": pos.date,
            "bin_label": pos.bin_label,
            "actual_high": actual,
            "won": won,
            "pnl": pnl,
            "entry_price": pos.entry_price,
            "quantity": pos.quantity,
        })

        # Feed resolution data to calibration tracker
        try:
            from syndicate.polymarket.resolution.calibration import CalibrationTracker

            cal = CalibrationTracker()
            # Find which bin index won
            winning_bin = -1
            for b in (market.bins if market else []):
                if b.lower <= actual < b.upper:
                    winning_bin = b.index
                    break
            if winning_bin >= 0:
                cal.record(
                    city=pos.city,
                    date=pos.date,
                    horizon_hours=0,  # Not available at resolution time
                    forecast_mean=0,  # Would need to store this at bet time
                    forecast_std=0,
                    bin_probabilities=[],
                    actual_high=actual,
                    winning_bin_index=winning_bin,
                )
        except Exception:
            pass  # Don't let calibration tracking break resolution

        logger.info(
            "position_resolved",
            city=pos.city, date=pos.date, bin=pos.bin_label,
            actual=actual, won=won, pnl=round(pnl, 2),
        )

    return results


# ── Helpers ───────────────────────────────────────────────────────────────


def _parse_bin_bounds(bin_label: str) -> tuple[float, float]:
    """Parse a bin label like '40-41F', '>=90F', '<30C', '15-16C' into (lower, upper).

    Returns (lower_inclusive, upper_exclusive). Uses -inf / inf for open-ended bins.
    """
    label = bin_label.strip()

    # Strip unit suffix (F or C)
    label_clean = re.sub(r"[FC°]$", "", label, flags=re.IGNORECASE)

    # ">=N" or ">N" — open upper bound
    m = re.match(r"^>=?\s*(-?\d+\.?\d*)$", label_clean)
    if m:
        return float(m.group(1)), float("inf")

    # "<=N" or "<N" — open lower bound
    m = re.match(r"^<=?\s*(-?\d+\.?\d*)$", label_clean)
    if m:
        return float("-inf"), float(m.group(1)) + 1  # exclusive upper

    # "N-M" range
    m = re.match(r"^(-?\d+\.?\d*)\s*[-–]\s*(-?\d+\.?\d*)$", label_clean)
    if m:
        lo = float(m.group(1))
        hi = float(m.group(2))
        return lo, hi + 1  # upper exclusive (e.g., "40-41" means [40, 42))

    # Single number "N" — treat as [N, N+1)
    m = re.match(r"^(-?\d+\.?\d*)$", label_clean)
    if m:
        val = float(m.group(1))
        return val, val + 1

    # Fallback: can't parse
    return float("-inf"), float("inf")


def _actual_in_bin(actual: float, bin_label: str, unit: TemperatureUnit) -> bool:
    """Parse bin label and check if actual temperature falls within.

    Args:
        actual: Actual high temperature observed.
        bin_label: Label like "40-41F", ">=90F", "<30C".
        unit: Temperature unit (used for context, not conversion).

    Returns:
        True if actual falls within the parsed bin bounds.
    """
    lower, upper = _parse_bin_bounds(bin_label)
    return lower <= actual < upper


def _actual_in_bin_from_market(
    actual: float,
    bin_label: str,
    bins: list[TemperatureBin],
) -> bool:
    """Use the market's bin definitions to check if actual falls in the named bin.

    Finds the bin matching bin_label and checks actual against its lower/upper bounds.

    Args:
        actual: Actual high temperature observed.
        bin_label: Label of the position's bin.
        bins: All bins from the market definition.

    Returns:
        True if actual falls within the matching bin's bounds.
    """
    for b in bins:
        if b.label == bin_label:
            return b.lower <= actual < b.upper

    # Label not found in market bins — fall back to string parsing
    lower, upper = _parse_bin_bounds(bin_label)
    return lower <= actual < upper
