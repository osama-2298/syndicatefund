"""Calibration tracking — Brier scores, reliability, and accuracy metrics.

Tracks forecast quality over time to:
1. Detect when calibration degrades
2. Provide data for the dashboard
3. Guide model weighting decisions
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import structlog
from pydantic import BaseModel

from syndicate.polymarket.config import PolymarketSettings

logger = structlog.get_logger()


# ── Data Model ───────────────────────────────────────────────────────────────


class CalibrationRecord(BaseModel):
    """A single resolved forecast used for calibration tracking."""

    city: str
    date: str
    horizon_hours: float
    forecast_mean: float
    forecast_std: float
    bin_probs: list[float]  # model probability for each bin, same order as market bins
    actual_high: float
    winning_bin: int  # index of bin that won
    recorded_at: datetime


# ── Tracker ──────────────────────────────────────────────────────────────────


class CalibrationTracker:
    """Tracks forecast calibration quality."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self._records: list[CalibrationRecord] = []
        self._path = (
            storage_path
            or PolymarketSettings().polymarket_data_dir / "calibration.json"
        )
        self._load()

    # ── Recording ────────────────────────────────────────────────────────

    def record(
        self,
        city: str,
        date: str,
        horizon_hours: float,
        forecast_mean: float,
        forecast_std: float,
        bin_probabilities: list[dict],  # [{bin_index, label, model_prob}]
        actual_high: float,
        winning_bin_index: int,
    ) -> None:
        """Record a resolved forecast for calibration tracking.

        Args:
            city: City name.
            date: Market target date (YYYY-MM-DD).
            horizon_hours: Hours between forecast and target date.
            forecast_mean: Ensemble mean forecast.
            forecast_std: Ensemble standard deviation.
            bin_probabilities: List of dicts with bin_index, label, model_prob.
            actual_high: Actual observed high temperature.
            winning_bin_index: Index of the bin that actually won.
        """
        # Convert bin_probabilities list[dict] to ordered list[float]
        bin_probs: list[float] = []
        if bin_probabilities:
            # Sort by bin_index and extract model_prob
            sorted_bins = sorted(bin_probabilities, key=lambda b: b.get("bin_index", 0))
            bin_probs = [b.get("model_prob", 0.0) for b in sorted_bins]

        rec = CalibrationRecord(
            city=city,
            date=date,
            horizon_hours=horizon_hours,
            forecast_mean=forecast_mean,
            forecast_std=forecast_std,
            bin_probs=bin_probs,
            actual_high=actual_high,
            winning_bin=winning_bin_index,
            recorded_at=datetime.now(timezone.utc),
        )
        self._records.append(rec)
        self._save()

        logger.info(
            "calibration.recorded",
            city=city,
            date=date,
            winning_bin=winning_bin_index,
            total_records=len(self._records),
        )

    # ── Brier Score ──────────────────────────────────────────────────────

    def brier_score(self, last_n: int = 0) -> float:
        """Compute Brier score across all records (or last N).

        Brier = (1/N) * sum((forecast_prob_of_winning_bin - 1)^2)
        For each resolved market, we take the probability we assigned to
        the bin that actually won, and compute (prob - 1)^2.
        Lower is better. Perfect = 0, random for 11 bins ~ 0.83.

        Args:
            last_n: If > 0, only use the most recent N records.

        Returns:
            Brier score, or 1.0 if no valid records.
        """
        records = self._records[-last_n:] if last_n > 0 else self._records
        if not records:
            return 1.0

        total = 0.0
        count = 0
        for rec in records:
            if rec.winning_bin < 0:
                continue
            if rec.bin_probs and 0 <= rec.winning_bin < len(rec.bin_probs):
                prob = rec.bin_probs[rec.winning_bin]
            else:
                prob = 0.0
            total += (prob - 1.0) ** 2
            count += 1

        return total / count if count > 0 else 1.0

    def brier_by_city(self) -> dict[str, float]:
        """Brier score per city.

        Returns:
            Mapping of city name to Brier score.
        """
        by_city: dict[str, list[CalibrationRecord]] = defaultdict(list)
        for rec in self._records:
            by_city[rec.city].append(rec)

        result: dict[str, float] = {}
        for city, recs in by_city.items():
            total = 0.0
            count = 0
            for rec in recs:
                if rec.winning_bin < 0:
                    continue
                if rec.bin_probs and 0 <= rec.winning_bin < len(rec.bin_probs):
                    prob = rec.bin_probs[rec.winning_bin]
                else:
                    prob = 0.0
                total += (prob - 1.0) ** 2
                count += 1
            result[city] = total / count if count > 0 else 1.0

        return result

    def brier_by_horizon(
        self, buckets: list[int] | None = None,
    ) -> dict[str, float]:
        """Brier score by horizon bucket (0-24h, 24-48h, 48-72h).

        Args:
            buckets: Horizon boundaries in hours. Defaults to [24, 48, 72].

        Returns:
            Mapping of bucket label to Brier score.
        """
        if buckets is None:
            buckets = [24, 48, 72]

        by_bucket: dict[str, list[CalibrationRecord]] = defaultdict(list)
        for rec in self._records:
            label = self._horizon_bucket_label(rec.horizon_hours, buckets)
            by_bucket[label].append(rec)

        result: dict[str, float] = {}
        for label, recs in by_bucket.items():
            total = 0.0
            count = 0
            for rec in recs:
                if rec.winning_bin < 0:
                    continue
                if rec.bin_probs and 0 <= rec.winning_bin < len(rec.bin_probs):
                    prob = rec.bin_probs[rec.winning_bin]
                else:
                    prob = 0.0
                total += (prob - 1.0) ** 2
                count += 1
            result[label] = total / count if count > 0 else 1.0

        return result

    @staticmethod
    def _horizon_bucket_label(hours: float, buckets: list[int]) -> str:
        """Map a horizon in hours to a bucket label like '0-24h'."""
        prev = 0
        for boundary in sorted(buckets):
            if hours <= boundary:
                return f"{prev}-{boundary}h"
            prev = boundary
        return f">{buckets[-1]}h"

    # ── Reliability ──────────────────────────────────────────────────────

    def reliability(self, n_bins: int = 10) -> list[dict]:
        """Reliability diagram data.

        Groups predictions by confidence level and computes observed
        frequency of winning. A well-calibrated model has
        predicted_prob ~ observed_freq for every bucket.

        Args:
            n_bins: Number of confidence bins.

        Returns:
            List of {predicted_prob, observed_freq, count}.
        """
        bin_width = 1.0 / n_bins
        # Each bin collects (predicted_prob, was_correct)
        bin_data: list[list[tuple[float, bool]]] = [[] for _ in range(n_bins)]

        for rec in self._records:
            if not rec.bin_probs or rec.winning_bin < 0:
                continue
            for i, prob in enumerate(rec.bin_probs):
                was_correct = i == rec.winning_bin
                bin_idx = min(int(prob / bin_width), n_bins - 1)
                bin_data[bin_idx].append((prob, was_correct))

        result: list[dict] = []
        for i, entries in enumerate(bin_data):
            if not entries:
                continue
            avg_predicted = sum(p for p, _ in entries) / len(entries)
            observed_freq = sum(1 for _, c in entries if c) / len(entries)
            result.append({
                "predicted_prob": round(avg_predicted, 4),
                "observed_freq": round(observed_freq, 4),
                "count": len(entries),
            })

        return result

    # ── MAE ──────────────────────────────────────────────────────────────

    def mae(self) -> float:
        """Mean absolute error: |forecast_mean - actual|.

        Returns:
            MAE across all records with nonzero forecast_mean, or 0.0
            if no qualifying records.
        """
        errors: list[float] = []
        for rec in self._records:
            # Skip records where forecast_mean wasn't available
            if rec.forecast_mean == 0.0 and rec.forecast_std == 0.0:
                continue
            errors.append(abs(rec.forecast_mean - rec.actual_high))

        return sum(errors) / len(errors) if errors else 0.0

    # ── Per-Model Accuracy ───────────────────────────────────────────────

    def model_accuracy(self) -> dict[str, float]:
        """Per-model MAE if available from per-model means.

        Note: Per-model means are not stored in CalibrationRecord by default.
        This method returns the overall MAE as a baseline. Extend
        CalibrationRecord with per-model data for richer analysis.

        Returns:
            Dict with "overall" MAE.
        """
        return {"overall": self.mae()}

    # ── Summary ──────────────────────────────────────────────────────────

    def summary(self) -> dict:
        """Full calibration summary for the dashboard.

        Returns:
            Dict with all calibration metrics.
        """
        return {
            "total_records": len(self._records),
            "brier_score": round(self.brier_score(), 4),
            "brier_last_50": round(self.brier_score(last_n=50), 4),
            "brier_by_city": {
                k: round(v, 4) for k, v in self.brier_by_city().items()
            },
            "brier_by_horizon": {
                k: round(v, 4) for k, v in self.brier_by_horizon().items()
            },
            "mae": round(self.mae(), 2),
            "model_accuracy": {
                k: round(v, 2) for k, v in self.model_accuracy().items()
            },
            "reliability": self.reliability(),
        }

    # ── Persistence ──────────────────────────────────────────────────────

    def save(self) -> None:
        """Persist records to JSON (public alias for _save)."""
        self._save()

    def load(self) -> None:
        """Load records from JSON (public alias for _load)."""
        self._load()

    def _save(self) -> None:
        """Persist records to JSON."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = [rec.model_dump(mode="json") for rec in self._records]
            self._path.write_text(json.dumps(payload, indent=2, default=str))
        except Exception:
            logger.warning(
                "calibration.save_failed",
                path=str(self._path),
                exc_info=True,
            )

    def _load(self) -> None:
        """Load records from JSON."""
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text())
            self._records = [CalibrationRecord.model_validate(r) for r in raw]
            logger.info(
                "calibration.loaded",
                path=str(self._path),
                records=len(self._records),
            )
        except Exception:
            logger.warning(
                "calibration.load_failed",
                path=str(self._path),
                exc_info=True,
            )
            self._records = []
