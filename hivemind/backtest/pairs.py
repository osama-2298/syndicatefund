"""Pairs trading -- cointegration-based mean reversion on crypto pairs.

Academic results: Sharpe 3.97, max DD 7.94%, beta 0.09-0.18
Strategy: When the spread between two correlated assets deviates from its mean,
bet on convergence.
"""

from __future__ import annotations

import math


class PairsTrader:
    """Z-score based pairs trading on cointegrated crypto pairs.

    Uses the log spread between two assets and a rolling window to compute
    z-scores. Generates entry/exit signals when the z-score crosses defined
    thresholds.

    Parameters:
        lookback: Rolling window size for mean/std calculation.
        entry_z: Enter when |z| > entry_z.
        exit_z: Exit (take profit) when |z| < exit_z.
        stop_z: Stop loss when |z| > stop_z (spread diverged too much).
    """

    def __init__(
        self,
        lookback: int = 60,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
        stop_z: float = 3.5,
    ) -> None:
        self.lookback = lookback
        self.entry_z = entry_z
        self.exit_z = exit_z
        self.stop_z = stop_z
        self._spread_history: list[float] = []

    def compute_spread(self, price_a: float, price_b: float) -> float:
        """Log spread: ln(price_a) - ln(price_b).

        Using log prices makes the spread stationary when the two assets
        are cointegrated, regardless of their absolute price levels.
        """
        if price_a <= 0 or price_b <= 0:
            return 0.0
        return math.log(price_a) - math.log(price_b)

    def update_and_signal(self, price_a: float, price_b: float) -> dict:
        """Update spread history and generate signal.

        Args:
            price_a: Current price of asset A (e.g. BTC).
            price_b: Current price of asset B (e.g. ETH).

        Returns:
            Dict with:
                z_score: Current z-score of the spread.
                signal: One of "LONG_A_SHORT_B", "SHORT_A_LONG_B", "EXIT", "HOLD".
                spread: Current log spread value.
                mean: Rolling mean of the spread.
                std: Rolling standard deviation of the spread.
        """
        spread = self.compute_spread(price_a, price_b)
        self._spread_history.append(spread)

        if len(self._spread_history) < self.lookback:
            return {
                "z_score": 0,
                "signal": "HOLD",
                "spread": spread,
                "mean": 0,
                "std": 0,
            }

        window = self._spread_history[-self.lookback :]
        mean = sum(window) / len(window)
        std = (sum((x - mean) ** 2 for x in window) / len(window)) ** 0.5

        if std == 0:
            return {
                "z_score": 0,
                "signal": "HOLD",
                "spread": spread,
                "mean": mean,
                "std": 0,
            }

        z = (spread - mean) / std

        signal = "HOLD"
        if abs(z) > self.stop_z:
            signal = "EXIT"  # Stop loss -- spread diverged too much
        elif z > self.entry_z:
            signal = "SHORT_A_LONG_B"  # Spread too high, bet on convergence
        elif z < -self.entry_z:
            signal = "LONG_A_SHORT_B"  # Spread too low, bet on convergence
        elif abs(z) < self.exit_z:
            signal = "EXIT"  # Spread reverted to mean, take profit

        return {
            "z_score": round(z, 3),
            "signal": signal,
            "spread": round(spread, 6),
            "mean": round(mean, 6),
            "std": round(std, 6),
        }

    def reset(self) -> None:
        """Reset the spread history (e.g. for a new backtest run)."""
        self._spread_history.clear()
