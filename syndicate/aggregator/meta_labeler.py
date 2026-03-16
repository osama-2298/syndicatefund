"""Meta-labeling — Lopez de Prado secondary classifier.

Separates direction prediction from bet sizing:
1. Primary model predicts direction (the agents/aggregator)
2. Meta-labeler predicts probability that the primary signal is correct
3. Meta-label probability becomes position size multiplier

Needs ~100+ trades to train. Returns multiplier=1.0 until sufficient data.
"""

from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


class MetaLabeler:
    """Secondary classifier predicting whether signals will be profitable."""

    def __init__(self, storage_path: str = "data/meta_labeler.json", min_samples: int = 100):
        self._path = Path(storage_path)
        self._min_samples = min_samples
        self._feature_history: list[dict] = []
        self._model_weights: dict[str, float] | None = None
        self._load()

    def extract_features(self, aggregated_signal, market_data: dict | None = None) -> dict:
        """Extract features for meta-labeling from an aggregated signal."""
        features = {
            "confidence": aggregated_signal.aggregated_confidence,
            "consensus": aggregated_signal.consensus_ratio,
            "decision_quality": (
                1.0 if aggregated_signal.weighted_scores.get("_decision_quality") == "HIGH_CONVICTION"
                else 0.5 if aggregated_signal.weighted_scores.get("_decision_quality") == "MODERATE"
                else 0.0
            ),
            "polarization": aggregated_signal.weighted_scores.get("_polarization", 0.0),
            "directional_strength": aggregated_signal.weighted_scores.get("_directional_strength", 0.0),
            "close_call": 1.0 if aggregated_signal.weighted_scores.get("_close_call", False) else 0.0,
            "n_signals": len(aggregated_signal.contributing_signals),
            "baseline_agrees": 1.0 if aggregated_signal.weighted_scores.get("_baseline_agrees", True) else 0.0,
        }
        return features

    def predict(self, features: dict) -> float:
        """Returns probability that the signal will be profitable (0-1).

        Used as position size multiplier. Returns 1.0 if model not yet trained.
        """
        if self._model_weights is None or len(self._feature_history) < self._min_samples:
            return 1.0  # Pass-through until enough data

        # Simple logistic regression prediction
        z = self._model_weights.get("intercept", 0.0)
        for feat_name, feat_val in features.items():
            if feat_name in self._model_weights:
                z += self._model_weights[feat_name] * feat_val

        # Sigmoid
        prob = 1.0 / (1.0 + math.exp(-z))
        return prob

    def record_outcome(self, features: dict, profitable: bool):
        """Record a trade outcome for future training."""
        record = {**features, "outcome": 1.0 if profitable else 0.0}
        self._feature_history.append(record)
        self._save()

        # Auto-retrain if we have enough data
        if len(self._feature_history) >= self._min_samples and len(self._feature_history) % 20 == 0:
            self.train()

    def train(self):
        """Train logistic regression on accumulated trade outcomes.

        Uses simple gradient descent — no sklearn dependency required.
        Walk-forward: train on older 80%, validate on recent 20%.
        """
        if len(self._feature_history) < self._min_samples:
            logger.info("meta_labeler_insufficient_data", n_samples=len(self._feature_history), min_required=self._min_samples)
            return

        # Split train/validation (80/20)
        split = int(len(self._feature_history) * 0.8)
        train_data = self._feature_history[:split]
        val_data = self._feature_history[split:]

        # Feature names (excluding outcome)
        feat_names = [k for k in train_data[0].keys() if k != "outcome"]

        # Initialize weights
        weights = {name: 0.0 for name in feat_names}
        weights["intercept"] = 0.0
        lr = 0.01

        # Simple gradient descent (100 epochs)
        for epoch in range(100):
            for record in train_data:
                # Forward pass
                z = weights["intercept"]
                for name in feat_names:
                    z += weights[name] * record.get(name, 0.0)
                pred = 1.0 / (1.0 + math.exp(-max(-20, min(20, z))))

                # Gradient
                error = record["outcome"] - pred
                weights["intercept"] += lr * error
                for name in feat_names:
                    weights[name] += lr * error * record.get(name, 0.0)

        # Validate
        correct = 0
        for record in val_data:
            z = weights["intercept"]
            for name in feat_names:
                z += weights[name] * record.get(name, 0.0)
            pred = 1.0 / (1.0 + math.exp(-max(-20, min(20, z))))
            predicted_class = 1 if pred > 0.5 else 0
            if predicted_class == int(record["outcome"]):
                correct += 1

        val_accuracy = correct / max(len(val_data), 1)
        logger.info("meta_labeler_trained",
                    train_samples=len(train_data),
                    val_samples=len(val_data),
                    val_accuracy=round(val_accuracy, 3))

        # Only use the model if it beats random (>55%)
        if val_accuracy > 0.55:
            self._model_weights = weights
        else:
            logger.warning("meta_labeler_not_useful", val_accuracy=val_accuracy)
            self._model_weights = None

        self._save()

    def _load(self):
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            self._feature_history = data.get("history", [])
            self._model_weights = data.get("weights")
        except Exception as e:
            logger.error("meta_labeler_load_failed", error=str(e))

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "history": self._feature_history[-5000:],  # Keep last 5000 records
            "weights": self._model_weights,
        }
        self._path.write_text(json.dumps(data, indent=2, default=str))
