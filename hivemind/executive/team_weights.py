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
import random
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


class AdaptiveTeamWeights:
    """Discounted Thompson Sampling for adaptive team weighting.

    Beta distribution parameters per team (alpha=wins, beta=losses).
    Discount factor forgets ~50% after 23 cycles (0.97^23 ≈ 0.50).
    CEO decisions still override via TeamWeightManager, but base weights
    adapt automatically.
    """

    def __init__(
        self,
        teams: list[str] | None = None,
        discount: float = 0.97,
        storage_path: str = "data/adaptive_weights.json",
    ) -> None:
        self.teams = teams or ["technical", "sentiment", "fundamental", "macro", "onchain"]
        self.posteriors: dict[str, dict[str, float]] = {
            team: {"alpha": 1.0, "beta": 1.0} for team in self.teams
        }
        self.discount = discount
        self._path = Path(storage_path)
        self._load()

    def update(self, team: str, outcome: bool) -> None:
        """Update team posterior with new trade outcome.

        Args:
            team: Team name (e.g. "technical").
            outcome: True if trade was profitable, False if loss.
        """
        if team not in self.posteriors:
            self.posteriors[team] = {"alpha": 1.0, "beta": 1.0}
        # Discount existing observations (recent matters more)
        self.posteriors[team]["alpha"] *= self.discount
        self.posteriors[team]["beta"] *= self.discount
        # Add new observation
        if outcome:
            self.posteriors[team]["alpha"] += 1
        else:
            self.posteriors[team]["beta"] += 1
        self._save()

    def sample_weights(self) -> dict[str, float]:
        """Thompson sampling: sample from each team's posterior."""
        weights = {}
        for team, params in self.posteriors.items():
            weights[team] = random.betavariate(
                max(params["alpha"], 0.01),
                max(params["beta"], 0.01),
            )
        return weights

    def get_expected_weights(self) -> dict[str, float]:
        """Deterministic expected value (alpha / (alpha + beta)) for display."""
        weights = {}
        for team, params in self.posteriors.items():
            total = params["alpha"] + params["beta"]
            weights[team] = params["alpha"] / max(total, 0.01)
        return weights

    def _load(self) -> None:
        """Load posteriors from JSON file."""
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            if isinstance(data, dict):
                for team, params in data.items():
                    if isinstance(params, dict) and "alpha" in params and "beta" in params:
                        self.posteriors[team] = {
                            "alpha": float(params["alpha"]),
                            "beta": float(params["beta"]),
                        }
        except Exception as e:
            logger.error("adaptive_weights_load_failed", error=str(e))

    def _save(self) -> None:
        """Save posteriors to JSON file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self.posteriors, indent=2))
