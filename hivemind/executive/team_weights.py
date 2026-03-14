"""
Team Weight Manager — persists CEO capital allocation decisions.

When the CEO says "INCREASE_CAPITAL for Technical team (weight 1.3)",
this module stores that weight and feeds it into the Signal Aggregator.

Weights are multipliers on top of each agent's base weight:
- 1.0 = normal influence
- 1.5 = 50% more influence (promoted team)
- 0.5 = 50% less influence (underperforming team)
- 0.0 = fired (signals ignored entirely)
"""

from __future__ import annotations

import json
from pathlib import Path

import structlog

logger = structlog.get_logger()

DEFAULT_WEIGHTS = {
    "technical": 1.0,
    "sentiment": 1.0,
    "fundamental": 1.0,
    "macro": 1.0,
    "onchain": 1.0,
}


class TeamWeightManager:
    """Persists and manages team weight multipliers."""

    def __init__(self, storage_path: str = "data/team_weights.json") -> None:
        self._path = Path(storage_path)
        self.weights: dict[str, float] = dict(DEFAULT_WEIGHTS)
        self._load()

    def get_weight(self, team_name: str) -> float:
        """Get the weight multiplier for a team."""
        return self.weights.get(team_name, 1.0)

    def apply_ceo_decisions(self, team_actions: list[dict]) -> None:
        """
        Apply CEO post-cycle team weight decisions.
        team_actions is a list of {team, action, new_weight, reason}.
        """
        for action in team_actions:
            team = action.get("team", "").lower()
            new_weight = action.get("new_weight", 1.0)
            decision = action.get("action", "MAINTAIN")

            if team in self.weights:
                old = self.weights[team]
                self.weights[team] = max(0.0, min(2.0, float(new_weight)))
                if old != self.weights[team]:
                    logger.info(
                        "team_weight_updated",
                        team=team,
                        old_weight=old,
                        new_weight=self.weights[team],
                        decision=decision,
                    )

        self._save()

    def is_fired(self, team_name: str) -> bool:
        """Check if a team has been fired (weight = 0)."""
        return self.weights.get(team_name, 1.0) <= 0.0

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            if isinstance(data, dict):
                self.weights.update(data)
        except Exception as e:
            logger.error("team_weights_load_failed", error=str(e))

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self.weights, indent=2))
