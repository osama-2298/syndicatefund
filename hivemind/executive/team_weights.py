"""
Team Weight Manager — persists CEO capital allocation decisions.

When the CEO says "INCREASE_CAPITAL for Technical team (weight 1.3)",
this module stores that weight and feeds it into the Signal Aggregator.

Weights are multipliers on top of each agent's base weight:
- 1.0 = normal influence
- 1.5 = 50% more influence (promoted team)
- 0.5 = 50% less influence (underperforming team)
- 0.0 = fired (signals ignored entirely)

Also provides PhaseWeightManager — 4-phase progressive weight learning
based on total closed trades:
  Phase 1 (0-30):    Equal weights (insufficient data)
  Phase 2 (30-100):  Shrunk IC-weighted (James-Stein toward equal)
  Phase 3 (100-500): Full IC-weighted
  Phase 4 (500+):    IC + Thompson Sampling hybrid
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


# ─── 4-Phase Progressive Weight Learning ──────────────────────────


TEAMS = list(DEFAULT_WEIGHTS.keys())


class PhaseWeightManager:
    """4-phase progressive team weight learning.

    Phases based on total closed trades:
      0-30:   Equal weights (insufficient data)
      30-100: Shrunk IC-weighted (James-Stein toward equal)
      100-500: Full IC-weighted
      500+:   IC + Thompson Sampling hybrid

    CEO decisions always override (can fire/promote regardless of phase).
    """

    def __init__(self, storage_path: str = "data/phase_weights.json") -> None:
        self.adaptive = AdaptiveTeamWeights()
        self._path = Path(storage_path)
        self._ic_weights: dict[str, float] = {}
        self._phase: int = 1
        self._total_trades: int = 0
        self._load()

    # ─── Public API ────────────────────────────────────────────────

    def update_from_tracker(self, tracker, total_closed_trades: int) -> None:
        """Recompute weights based on current phase and tracker data.

        Args:
            tracker: A PerformanceTracker instance (has compute_ic()).
            total_closed_trades: Number of closed trades in the ledger.
        """
        self._total_trades = total_closed_trades
        self._phase = self._determine_phase(total_closed_trades)

        if self._phase >= 2:
            ic_data = tracker.compute_ic()
            team_ics = ic_data.get("by_team", {})
            self._ic_weights = self._compute_ic_weights(team_ics)

        self._save()
        logger.info(
            "phase_weights_updated",
            phase=self._phase,
            total_trades=total_closed_trades,
            ic_weights=self._ic_weights if self._phase >= 2 else {},
        )

    def get_weights(self, ceo_weights: dict[str, float]) -> dict[str, float]:
        """Get final weights, respecting CEO overrides.

        CEO firing (weight <= 0) is absolute.  Other explicit CEO adjustments
        are blended multiplicatively with the phase-derived base weight.

        Args:
            ceo_weights: Current CEO team weight overrides from TeamWeightManager.

        Returns:
            Final weight dict ready for the SignalAggregator.
        """
        base = self._get_phase_weights()

        for team, ceo_w in ceo_weights.items():
            if ceo_w <= 0:
                # CEO fired this team — hard override regardless of phase
                base[team] = 0.0
            elif ceo_w != 1.0:
                # CEO explicitly adjusted — blend with phase weights
                base[team] = round(base.get(team, 1.0) * ceo_w, 3)

        return base

    @property
    def phase(self) -> int:
        """Current learning phase (1-4)."""
        return self._phase

    @property
    def total_trades(self) -> int:
        """Number of closed trades the phase was computed from."""
        return self._total_trades

    # ─── Phase Logic ───────────────────────────────────────────────

    @staticmethod
    def _determine_phase(n: int) -> int:
        if n < 30:
            return 1
        if n < 100:
            return 2
        if n < 500:
            return 3
        return 4

    def _get_phase_weights(self) -> dict[str, float]:
        if self._phase == 1:
            return {t: 1.0 for t in TEAMS}

        if self._phase == 2:
            # James-Stein shrinkage toward equal weights.
            # Shrinkage decreases linearly from 1.0 at 30 trades to 0.0 at 100.
            shrinkage = max(0.0, 1.0 - (self._total_trades - 30) / 70.0)
            weights: dict[str, float] = {}
            for t in TEAMS:
                ic_w = self._ic_weights.get(t, 1.0)
                weights[t] = round((1.0 - shrinkage) * ic_w + shrinkage * 1.0, 3)
            return weights

        if self._phase == 3:
            # Full IC-weighted — no shrinkage
            if self._ic_weights:
                return {t: round(self._ic_weights.get(t, 1.0), 3) for t in TEAMS}
            return {t: 1.0 for t in TEAMS}

        # Phase 4: IC + Thompson Sampling hybrid
        thompson = self.adaptive.get_expected_weights()
        weights = {}
        for t in TEAMS:
            ic_w = self._ic_weights.get(t, 1.0)
            ts_w = thompson.get(t, 0.5)
            # Normalize Thompson weight to same scale as IC weight (0.5 to 1.5)
            ts_normalized = 0.5 + ts_w
            weights[t] = round(0.6 * ic_w + 0.4 * ts_normalized, 3)
        return weights

    @staticmethod
    def _compute_ic_weights(team_ics: dict[str, float]) -> dict[str, float]:
        """Convert per-team IC values to weight multipliers.

        Formula: weight = 1.0 + IC * 10, clamped to [0.3, 2.0].
        IC > 0.10  => weight ~ 2.0 (strong edge)
        IC ~ 0     => weight ~ 1.0 (neutral)
        IC < -0.07 => weight ~ 0.3 (suppressed, not killed)
        """
        weights: dict[str, float] = {}
        for team, ic in team_ics.items():
            w = max(0.3, min(2.0, 1.0 + ic * 10))
            weights[team] = round(w, 3)

        # Default weight for teams not in IC data
        for team in TEAMS:
            if team not in weights:
                weights[team] = 1.0

        return weights

    # ─── Persistence ───────────────────────────────────────────────

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            if isinstance(data, dict):
                self._phase = data.get("phase", 1)
                self._total_trades = data.get("total_trades", 0)
                self._ic_weights = data.get("ic_weights", {})
        except Exception as e:
            logger.error("phase_weights_load_failed", error=str(e))

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "phase": self._phase,
            "total_trades": self._total_trades,
            "ic_weights": self._ic_weights,
        }
        self._path.write_text(json.dumps(data, indent=2))
