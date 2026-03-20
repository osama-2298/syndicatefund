"""Ensemble -> bin probability distribution via member counting + calibrated CDF."""

from __future__ import annotations

import math

import structlog
from scipy.stats import norm

from syndicate.polymarket.models import BinProbability, EnsembleForecast, TemperatureBin

log = structlog.get_logger(__name__)

# Minimum probability floor per bin — prevents 0% on bins that could still hit
PROB_FLOOR = 0.01


def compute_bin_probabilities(
    forecast: EnsembleForecast,
    bins: list[TemperatureBin],
) -> list[BinProbability]:
    """Count fraction of ensemble members falling into each temperature bin.

    Phase 1: Raw member counting with 1% floor.
    Phase 2 will add EMOS calibration before counting.

    Args:
        forecast: EnsembleForecast with all 173 members
        bins: list of TemperatureBin from the market definition

    Returns:
        list of BinProbability with model_prob set, market_price from bins
    """
    all_highs = forecast.all_highs
    total = len(all_highs)

    if total == 0:
        log.warning(
            "compute_bin_probabilities.no_members",
            city=forecast.city,
            date=forecast.target_date,
        )
        # Return uniform distribution with floor
        n_bins = len(bins)
        uniform_prob = 1.0 / n_bins if n_bins > 0 else 0.0
        return [
            BinProbability(
                bin_index=b.index,
                label=b.label,
                model_prob=uniform_prob,
                market_price=b.market_price,
                edge=uniform_prob - b.market_price,
            )
            for b in bins
        ]

    # Count members in each bin
    raw_probs: list[float] = []
    for b in bins:
        count = 0
        for t in all_highs:
            # lower is inclusive, upper is exclusive
            # -inf lower: any value < upper counts
            # +inf upper: any value >= lower counts
            if b.lower <= t < b.upper:
                count += 1
        raw_prob = count / total
        raw_probs.append(max(PROB_FLOOR, raw_prob))

    # Normalize to sum to 1.0
    total_prob = sum(raw_probs)
    if total_prob > 0:
        normalized = [p / total_prob for p in raw_probs]
    else:
        normalized = raw_probs

    # Build BinProbability objects
    result: list[BinProbability] = []
    for b, prob in zip(bins, normalized):
        result.append(
            BinProbability(
                bin_index=b.index,
                label=b.label,
                model_prob=round(prob, 6),
                market_price=b.market_price,
                edge=round(prob - b.market_price, 6),
            )
        )

    log.info(
        "compute_bin_probabilities.done",
        city=forecast.city,
        date=forecast.target_date,
        n_members=total,
        n_bins=len(bins),
        top_bin=max(result, key=lambda x: x.model_prob).label if result else None,
    )

    return result


def compute_bin_probabilities_calibrated(
    forecast: EnsembleForecast,
    bins: list[TemperatureBin],
    calibrated_mean: float,
    calibrated_std: float,
) -> list[BinProbability]:
    """Compute bin probabilities using calibrated Gaussian CDF integration.

    Instead of counting members, integrates the calibrated N(mean, std)
    distribution between each bin's boundaries.

    P(bin_i) = CDF(upper_i) - CDF(lower_i)

    Args:
        forecast: EnsembleForecast (used for metadata: city, date).
        bins: list of TemperatureBin from the market definition.
        calibrated_mean: EMOS-calibrated distribution mean.
        calibrated_std: EMOS-calibrated distribution standard deviation.

    Returns:
        list of BinProbability with model_prob set, market_price from bins.
    """
    if calibrated_std <= 0:
        # Degenerate case — point forecast, assign all probability to the bin
        # containing the mean
        log.warning(
            "compute_bin_probabilities_calibrated.zero_std",
            city=forecast.city,
            date=forecast.target_date,
            mean=calibrated_mean,
        )
        raw_probs: list[float] = []
        for b in bins:
            if b.lower <= calibrated_mean < b.upper:
                raw_probs.append(1.0)
            else:
                raw_probs.append(PROB_FLOOR)

        # Normalize
        total_prob = sum(raw_probs)
        normalized = [p / total_prob for p in raw_probs]

        return [
            BinProbability(
                bin_index=b.index,
                label=b.label,
                model_prob=round(prob, 6),
                market_price=b.market_price,
                edge=round(prob - b.market_price, 6),
            )
            for b, prob in zip(bins, normalized)
        ]

    # Integrate calibrated Gaussian CDF across each bin
    dist = norm(loc=calibrated_mean, scale=calibrated_std)
    raw_probs = []

    for b in bins:
        # Handle -inf and +inf boundaries
        lower_cdf = 0.0 if math.isinf(b.lower) and b.lower < 0 else dist.cdf(b.lower)
        upper_cdf = 1.0 if math.isinf(b.upper) and b.upper > 0 else dist.cdf(b.upper)

        prob = upper_cdf - lower_cdf
        raw_probs.append(max(PROB_FLOOR, prob))

    # Normalize to sum to 1.0
    total_prob = sum(raw_probs)
    if total_prob > 0:
        normalized = [p / total_prob for p in raw_probs]
    else:
        normalized = raw_probs

    # Build BinProbability objects
    result: list[BinProbability] = []
    for b, prob in zip(bins, normalized):
        result.append(
            BinProbability(
                bin_index=b.index,
                label=b.label,
                model_prob=round(prob, 6),
                market_price=b.market_price,
                edge=round(prob - b.market_price, 6),
            )
        )

    log.info(
        "compute_bin_probabilities_calibrated.done",
        city=forecast.city,
        date=forecast.target_date,
        calibrated_mean=round(calibrated_mean, 2),
        calibrated_std=round(calibrated_std, 2),
        n_bins=len(bins),
        top_bin=max(result, key=lambda x: x.model_prob).label if result else None,
    )

    return result
