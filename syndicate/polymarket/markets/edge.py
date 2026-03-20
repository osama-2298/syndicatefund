"""Edge detection — find profitable opportunities in weather markets."""

from __future__ import annotations

from datetime import datetime, timezone

import structlog

from syndicate.polymarket.models import BinProbability, MarketAnalysis

log = structlog.get_logger(__name__)

# Edge thresholds by forecast horizon — further out = need more edge
HORIZON_THRESHOLDS = {
    24: 0.08,   # <=24h: 8% minimum edge
    48: 0.12,   # 25-48h: 12%
    72: 0.15,   # 49-72h: 15%
}
MAX_HORIZON_HOURS = 72  # Skip markets >72h out


def compute_horizon_hours(target_date: str) -> float:
    """Compute hours between now and the target date's end (23:59 UTC).

    Args:
        target_date: YYYY-MM-DD string

    Returns:
        Hours until end of target date. Negative if date is in the past.
    """
    now = datetime.now(timezone.utc)
    # Target is end of the resolution day (23:59:59 UTC)
    target_end = datetime.strptime(target_date, "%Y-%m-%d").replace(
        hour=23, minute=59, second=59, tzinfo=timezone.utc,
    )
    delta = target_end - now
    return delta.total_seconds() / 3600.0


def get_min_edge(horizon_hours: float) -> float:
    """Return minimum edge threshold based on forecast horizon.

    Shorter horizons = forecasts are more accurate = lower edge required.
    Beyond MAX_HORIZON_HOURS, returns 1.0 (effectively impossible edge).
    """
    if horizon_hours <= 24:
        return 0.08
    elif horizon_hours <= 48:
        return 0.12
    elif horizon_hours <= 72:
        return 0.15
    else:
        return 1.0  # Effectively skip — forecast too far out


def detect_edges(
    analysis: MarketAnalysis,
) -> list[BinProbability]:
    """Filter bin probabilities to only those with sufficient edge.

    Returns list of BinProbability where:
      - edge >= threshold for this horizon
      - model_prob > market_price (positive edge only)

    Sorted by edge descending (best opportunities first).
    """
    min_edge = get_min_edge(analysis.horizon_hours)

    if analysis.horizon_hours > MAX_HORIZON_HOURS:
        log.info(
            "detect_edges.skipped_horizon",
            city=analysis.city,
            date=analysis.date,
            horizon_hours=round(analysis.horizon_hours, 1),
        )
        return []

    opportunities: list[BinProbability] = []
    for bp in analysis.bin_probabilities:
        if bp.edge >= min_edge and bp.model_prob > bp.market_price:
            opportunities.append(bp)

    # Sort by edge descending — best opportunities first
    opportunities.sort(key=lambda x: x.edge, reverse=True)

    log.info(
        "detect_edges.done",
        city=analysis.city,
        date=analysis.date,
        horizon_hours=round(analysis.horizon_hours, 1),
        min_edge=min_edge,
        n_opportunities=len(opportunities),
        best_edge=round(opportunities[0].edge, 4) if opportunities else 0.0,
    )

    return opportunities


def summarize_opportunities(opportunities: list[BinProbability]) -> str:
    """Human-readable summary of detected edge opportunities.

    Args:
        opportunities: list of BinProbability with sufficient edge, sorted by edge desc

    Returns:
        Multi-line string summary suitable for logging or display.
    """
    if not opportunities:
        return "No edge opportunities found."

    lines = [f"Found {len(opportunities)} opportunity(ies):"]
    for i, bp in enumerate(opportunities, 1):
        lines.append(
            f"  {i}. {bp.label}: "
            f"model={bp.model_prob:.1%} vs market={bp.market_price:.1%} "
            f"-> edge={bp.edge:+.1%}"
        )

    total_edge = sum(bp.edge for bp in opportunities)
    lines.append(f"  Total edge across opportunities: {total_edge:+.1%}")
    return "\n".join(lines)
