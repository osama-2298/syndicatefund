"""Temperature laddering — spread bets across adjacent bins to reduce variance.

Instead of betting everything on the single best-edge bin, spread capital
across the best bin and its neighbors. This captures the forecast's
uncertainty and increases the probability of at least one bin hitting.

Proven strategy used by neobrother ($20K+ profit) and other top traders.
"""

from __future__ import annotations

import structlog

from syndicate.polymarket.models import BinProbability

log = structlog.get_logger(__name__)

# Minimum USDC per ladder leg — skip legs below this
MIN_LEG_AMOUNT = 5.0


def _find_neighbors(
    center: BinProbability,
    all_bin_probs: list[BinProbability],
) -> tuple[BinProbability | None, BinProbability | None]:
    """Find left (index-1) and right (index+1) neighbors of the center bin.

    Skips neighbors whose market_price is 0 (resolved bins).

    Returns:
        (left_neighbor, right_neighbor) — either may be None.
    """
    by_index = {bp.bin_index: bp for bp in all_bin_probs}
    left = by_index.get(center.bin_index - 1)
    right = by_index.get(center.bin_index + 1)

    # Exclude resolved bins (market_price == 0)
    if left is not None and left.market_price == 0:
        left = None
    if right is not None and right.market_price == 0:
        right = None

    return left, right


def _has_positive_edge(bp: BinProbability) -> bool:
    """Return True if the bin has positive edge (model_prob > market_price)."""
    return bp.model_prob > bp.market_price


def _kelly_fraction(bp: BinProbability) -> float:
    """Compute raw Kelly fraction for a single bin.

    Kelly = (model_prob - market_price) / (1 - market_price)
    """
    if bp.market_price >= 1.0 or bp.model_prob <= bp.market_price:
        return 0.0
    return (bp.model_prob - bp.market_price) / (1.0 - bp.market_price)


def ladder_allocation(
    opportunities: list[BinProbability],
    all_bin_probs: list[BinProbability],
    total_amount: float,
    scheme: str = "gradient",  # "gradient" (50/25/25), "equal" (33/33/33), "kelly"
) -> list[tuple[BinProbability, float]]:
    """Allocate capital across the best bin and its adjacent neighbors.

    Args:
        opportunities: Bins that passed edge detection (sorted by edge desc)
        all_bin_probs: All bin probabilities (to find neighbors)
        total_amount: Total USDC to allocate
        scheme: Allocation scheme

    Returns:
        List of (BinProbability, amount) tuples to bet on
    """
    if not opportunities or total_amount <= 0:
        return []

    center = opportunities[0]
    left, right = _find_neighbors(center, all_bin_probs)

    # Filter neighbors: only include if they have positive edge
    if left is not None and not _has_positive_edge(left):
        left = None
    if right is not None and not _has_positive_edge(right):
        right = None

    # Determine allocation weights based on scheme and available neighbors
    legs: list[tuple[BinProbability, float]] = []

    if left is None and right is None:
        # No neighbors with edge — 100% on center
        legs.append((center, total_amount))

    elif left is not None and right is not None:
        # Both neighbors have edge
        if scheme == "gradient":
            weight_list = [(center, 0.50), (left, 0.25), (right, 0.25)]
        elif scheme == "equal":
            weight_list = [(center, 1 / 3), (left, 1 / 3), (right, 1 / 3)]
        elif scheme == "kelly":
            kf_center = _kelly_fraction(center)
            kf_left = _kelly_fraction(left)
            kf_right = _kelly_fraction(right)
            total_kf = kf_center + kf_left + kf_right
            if total_kf <= 0:
                legs.append((center, total_amount))
                return _apply_minimum(legs)
            weight_list = [
                (center, kf_center / total_kf),
                (left, kf_left / total_kf),
                (right, kf_right / total_kf),
            ]
        else:
            # Unknown scheme — fall back to gradient
            weight_list = [(center, 0.50), (left, 0.25), (right, 0.25)]

        for bp, weight in weight_list:
            legs.append((bp, total_amount * weight))

    else:
        # Only one neighbor has edge — center=67%, neighbor=33%
        neighbor = left if left is not None else right
        assert neighbor is not None

        if scheme == "kelly":
            kf_center = _kelly_fraction(center)
            kf_neighbor = _kelly_fraction(neighbor)
            total_kf = kf_center + kf_neighbor
            if total_kf <= 0:
                legs.append((center, total_amount))
                return _apply_minimum(legs)
            legs.append((center, total_amount * kf_center / total_kf))
            legs.append((neighbor, total_amount * kf_neighbor / total_kf))
        else:
            legs.append((center, total_amount * 0.67))
            legs.append((neighbor, total_amount * 0.33))

    result = _apply_minimum(legs)

    log.info(
        "ladder_allocation",
        scheme=scheme,
        center_bin=center.label,
        total_amount=round(total_amount, 2),
        n_legs=len(result),
        legs=[
            {"bin": bp.label, "amount": round(amt, 2)}
            for bp, amt in result
        ],
    )

    return result


def _apply_minimum(
    legs: list[tuple[BinProbability, float]],
) -> list[tuple[BinProbability, float]]:
    """Remove legs below the minimum amount threshold.

    Args:
        legs: List of (BinProbability, amount) tuples.

    Returns:
        Filtered list with legs below MIN_LEG_AMOUNT removed.
    """
    return [(bp, amt) for bp, amt in legs if amt >= MIN_LEG_AMOUNT]
