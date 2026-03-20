"""Multi-model ensemble blending — 173 members from GFS + ECMWF IFS + ECMWF AIFS + ICON."""

from __future__ import annotations

import statistics
from collections import defaultdict

import structlog

from syndicate.polymarket.models import EnsembleForecast

log = structlog.get_logger(__name__)


def blend_ensembles(forecast: EnsembleForecast) -> dict:
    """Blend all ensemble members into unified statistics.

    Returns dict with:
      - all_highs: list[float] — all 173 member daily high predictions
      - mean: float
      - std: float
      - model_counts: dict[str, int] — members per model
      - model_means: dict[str, float] — mean per model
      - model_stds: dict[str, float] — std per model
      - agreement: float — 0-1 score of inter-model agreement
    """
    all_highs = forecast.all_highs

    if not all_highs:
        log.warning("blend_ensembles.empty", city=forecast.city, date=forecast.target_date)
        return {
            "all_highs": [],
            "mean": 0.0,
            "std": 0.0,
            "model_counts": {},
            "model_means": {},
            "model_stds": {},
            "agreement": 0.0,
        }

    # Overall stats
    overall_mean = sum(all_highs) / len(all_highs)
    overall_std = statistics.stdev(all_highs) if len(all_highs) > 1 else 0.0

    # Group members by model
    by_model: dict[str, list[float]] = defaultdict(list)
    for member in forecast.members:
        by_model[member.model].append(member.daily_high)

    model_counts: dict[str, int] = {}
    model_means: dict[str, float] = {}
    model_stds: dict[str, float] = {}

    for model, highs in by_model.items():
        model_counts[model] = len(highs)
        model_means[model] = sum(highs) / len(highs)
        model_stds[model] = statistics.stdev(highs) if len(highs) > 1 else 0.0

    # Agreement metric: 1 - (std of model means / overall std)
    # High when all models predict similar means; low when they diverge.
    if len(model_means) <= 1 or overall_std == 0.0:
        # Single model or zero spread — perfect agreement by definition
        agreement = 1.0
    else:
        means_list = list(model_means.values())
        std_of_means = statistics.stdev(means_list)
        agreement = 1.0 - min(1.0, std_of_means / overall_std)

    log.info(
        "blend_ensembles.done",
        city=forecast.city,
        date=forecast.target_date,
        n_members=len(all_highs),
        n_models=len(by_model),
        mean=round(overall_mean, 2),
        std=round(overall_std, 2),
        agreement=round(agreement, 3),
    )

    return {
        "all_highs": all_highs,
        "mean": overall_mean,
        "std": overall_std,
        "model_counts": model_counts,
        "model_means": model_means,
        "model_stds": model_stds,
        "agreement": agreement,
    }
