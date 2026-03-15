"""
Stock Team Weight Manager — includes news + institutional teams.
"""

from __future__ import annotations

import json
from pathlib import Path

import structlog

logger = structlog.get_logger()

DEFAULT_STOCK_WEIGHTS = {
    "technical": 1.0,
    "sentiment": 1.0,
    "fundamental": 1.0,
    "macro": 1.0,
    "institutional": 1.0,
    "news": 1.0,
}


class StockTeamWeightManager:
    """Persists and manages stock team weight multipliers."""

    def __init__(self, storage_path: str = "data/stocks/team_weights.json") -> None:
        self._path = Path(storage_path)
        self.weights: dict[str, float] = dict(DEFAULT_STOCK_WEIGHTS)
        self._load()

    def get_weight(self, team_name: str) -> float:
        return self.weights.get(team_name, 1.0)

    def apply_ceo_decisions(self, team_actions: list[dict]) -> None:
        for action in team_actions:
            team = action.get("team", "").lower()
            new_weight = action.get("new_weight", 1.0)
            if team in self.weights:
                old = self.weights[team]
                self.weights[team] = max(0.0, min(2.0, float(new_weight)))
                if old != self.weights[team]:
                    logger.info("stock_team_weight_updated", team=team, old=old, new=self.weights[team])
        self._save()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            if isinstance(data, dict):
                self.weights.update(data)
        except Exception as e:
            logger.error("stock_team_weights_load_failed", error=str(e))

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self.weights, indent=2))
