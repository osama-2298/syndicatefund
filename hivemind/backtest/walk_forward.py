"""Walk-forward optimization — prevents overfitting by training on rolling windows.

Instead of optimizing parameters on the full dataset (overfitting guaranteed),
walk-forward:
1. Train on window [0, T]
2. Test on [T, T+test_period]
3. Advance: Train on [step, T+step], Test on [T+step, T+step+test_period]
4. Repeat until end of data
5. Concatenate all out-of-sample test periods -> the "true" backtest result

This validates that the strategy works on unseen data.
"""

from __future__ import annotations

import itertools
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from hivemind.backtest.engine import BacktestConfig, BacktestEngine, BacktestResult
from hivemind.backtest.metrics import compute_backtest_metrics


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class WalkForwardConfig:
    """Parameters controlling the walk-forward optimisation loop."""

    train_days: int = 180  # 6 months training window
    test_days: int = 90    # 3 months test window
    step_days: int = 30    # Advance 1 month between windows

    # Parameters to optimize (with candidate values)
    param_grid: dict = field(default_factory=lambda: {
        "signal_threshold": [0.5, 0.75, 1.0, 1.25, 1.5],
        "atr_stop_mult": [2.0, 2.5, 3.0, 3.5, 4.0],
        "atr_tp_mult": [4.0, 5.0, 6.0, 8.0],
    })

    # Metric to optimise on during the training window
    optimization_metric: str = "sharpe_ratio"


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

@dataclass
class WalkForwardResult:
    """Aggregated results from all walk-forward windows."""

    windows: list[dict]             # Per-window details
    combined_equity: list[dict]     # Concatenated out-of-sample equity curve
    combined_metrics: dict          # Metrics computed on the combined OOS curve
    param_stability: dict           # How stable optimal params are across windows
    duration_secs: float = 0.0


# ---------------------------------------------------------------------------
# Optimizer
# ---------------------------------------------------------------------------

class WalkForwardOptimizer:
    """Run walk-forward optimization over rolling train/test windows."""

    def __init__(self) -> None:
        self._engine = BacktestEngine()

    # -- public API ---------------------------------------------------------

    def run(
        self,
        base_config: BacktestConfig,
        wf_config: WalkForwardConfig,
    ) -> WalkForwardResult:
        """Execute the full walk-forward loop.

        For each rolling window:
        1. Grid-search over ``wf_config.param_grid`` on the *training* period,
           selecting the parameter combo with the best ``optimization_metric``.
        2. Run a single backtest on the *test* period using those optimal params.
        3. Record the out-of-sample test result (the unbiased performance estimate).

        Finally, concatenate all test-period equity curves and compute combined
        metrics to produce a single, debiased performance report.
        """
        t0 = time.monotonic()

        start_dt = datetime.strptime(base_config.start_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc,
        )
        end_dt = datetime.strptime(base_config.end_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc,
        )

        train_delta = timedelta(days=wf_config.train_days)
        test_delta = timedelta(days=wf_config.test_days)
        step_delta = timedelta(days=wf_config.step_days)

        # Build the list of (train_start, train_end, test_start, test_end) windows
        windows_spec: list[tuple[datetime, datetime, datetime, datetime]] = []
        cursor = start_dt

        while cursor + train_delta + test_delta <= end_dt + timedelta(days=1):
            train_start = cursor
            train_end = cursor + train_delta
            test_start = train_end
            test_end = min(train_end + test_delta, end_dt)
            windows_spec.append((train_start, train_end, test_start, test_end))
            cursor += step_delta

        if not windows_spec:
            raise ValueError(
                f"Date range {base_config.start_date} -> {base_config.end_date} is "
                f"too short for train_days={wf_config.train_days} + "
                f"test_days={wf_config.test_days}. Need at least "
                f"{wf_config.train_days + wf_config.test_days} days."
            )

        # Expand the full parameter grid once
        param_combos = _expand_grid(wf_config.param_grid)
        n_combos = len(param_combos)
        n_windows = len(windows_spec)

        print(
            f"Walk-forward: {n_windows} windows, "
            f"{n_combos} param combos each, "
            f"optimising on {wf_config.optimization_metric}"
        )
        print(f"  Train: {wf_config.train_days}d  |  Test: {wf_config.test_days}d  |  Step: {wf_config.step_days}d")
        print()

        # Run each window
        window_results: list[dict] = []

        for idx, (train_s, train_e, test_s, test_e) in enumerate(windows_spec):
            win_t0 = time.monotonic()

            print(
                f"  Window {idx + 1}/{n_windows}: "
                f"train {train_s.strftime('%Y-%m-%d')} -> {train_e.strftime('%Y-%m-%d')}  |  "
                f"test {test_s.strftime('%Y-%m-%d')} -> {test_e.strftime('%Y-%m-%d')}"
            )

            # 1. Optimise on training period
            best_params, best_train_metric = self._optimize_window(
                base_config, train_s, train_e, param_combos, wf_config.optimization_metric,
            )

            # 2. Test with best params
            test_result = self._test_window(base_config, test_s, test_e, best_params)

            test_sharpe = test_result.metrics.get("sharpe_ratio", 0.0)
            test_return = test_result.metrics.get("total_return_pct", 0.0)

            win_dur = time.monotonic() - win_t0
            print(
                f"    Best params: {best_params}  "
                f"(train {wf_config.optimization_metric}={best_train_metric:+.4f})"
            )
            print(
                f"    Test: sharpe={test_sharpe:.4f}  "
                f"return={test_return:+.2f}%  "
                f"trades={test_result.metrics.get('total_trades', 0)}  "
                f"({win_dur:.1f}s)"
            )

            window_results.append({
                "window": idx + 1,
                "train_start": train_s.strftime("%Y-%m-%d"),
                "train_end": train_e.strftime("%Y-%m-%d"),
                "test_start": test_s.strftime("%Y-%m-%d"),
                "test_end": test_e.strftime("%Y-%m-%d"),
                "best_params": best_params,
                "best_train_metric": round(best_train_metric, 4),
                "test_metrics": test_result.metrics,
                "test_equity": test_result.equity_curve,
                "test_trades": test_result.trades,
                "test_daily_returns": test_result.daily_returns,
            })

        # 3. Concatenate all out-of-sample equity curves
        combined_equity, combined_returns = self._combine_oos_results(
            window_results, base_config.initial_capital,
        )

        # 4. Compute combined metrics
        combined_metrics = compute_backtest_metrics(
            equity_curve=combined_equity,
            daily_returns=combined_returns,
            benchmark_prices=None,
        )

        # 5. Assess parameter stability
        param_stability = self._compute_param_stability(window_results)

        duration = time.monotonic() - t0

        return WalkForwardResult(
            windows=window_results,
            combined_equity=combined_equity,
            combined_metrics=combined_metrics,
            param_stability=param_stability,
            duration_secs=round(duration, 2),
        )

    # -- internal methods ---------------------------------------------------

    def _optimize_window(
        self,
        base_config: BacktestConfig,
        train_start: datetime,
        train_end: datetime,
        param_combos: list[dict],
        metric: str,
    ) -> tuple[dict, float]:
        """Grid search over param combos on the training window.

        Returns (best_params_dict, best_metric_value).
        """
        best_params: dict = {}
        best_metric_val = -float("inf")

        for combo in param_combos:
            cfg = self._make_config(base_config, train_start, train_end, combo)
            try:
                result = self._engine.run(cfg)
            except Exception:
                # If a particular param combo causes an error, skip it
                continue

            val = result.metrics.get(metric, -float("inf"))
            # For max_drawdown, lower is better — negate so argmax still works
            if metric == "max_drawdown":
                val = -val

            if val > best_metric_val:
                best_metric_val = val
                best_params = combo

        # Un-negate if we were optimising drawdown
        if metric == "max_drawdown":
            best_metric_val = -best_metric_val

        # Fall back to defaults if nothing worked
        if not best_params:
            best_params = {
                "signal_threshold": 1.0,
                "exit_threshold": -0.5,
                "atr_stop_mult": 3.0,
                "atr_tp_mult": 6.0,
            }
            best_metric_val = 0.0

        return best_params, best_metric_val

    def _test_window(
        self,
        base_config: BacktestConfig,
        test_start: datetime,
        test_end: datetime,
        params: dict,
    ) -> BacktestResult:
        """Run a single backtest on the test window with fixed params."""
        cfg = self._make_config(base_config, test_start, test_end, params)
        return self._engine.run(cfg)

    def _make_config(
        self,
        base_config: BacktestConfig,
        start_dt: datetime,
        end_dt: datetime,
        strategy_params: dict,
    ) -> BacktestConfig:
        """Create a new BacktestConfig for a specific window + param set."""
        # Merge provided strategy params with defaults
        merged_params = {
            "signal_threshold": 1.0,
            "exit_threshold": -0.5,
            "atr_stop_mult": 3.0,
            "atr_tp_mult": 6.0,
        }
        merged_params.update(strategy_params)

        return BacktestConfig(
            start_date=start_dt.strftime("%Y-%m-%d"),
            end_date=end_dt.strftime("%Y-%m-%d"),
            initial_capital=base_config.initial_capital,
            symbols=list(base_config.symbols),
            regime=base_config.regime,
            step_hours=base_config.step_hours,
            storage_dir=base_config.storage_dir,
            strategy_params=merged_params,
        )

    def _combine_oos_results(
        self,
        window_results: list[dict],
        initial_capital: float,
    ) -> tuple[list[dict], list[float]]:
        """Concatenate out-of-sample equity curves, chaining the final equity
        of each window into the starting equity of the next.

        Returns (combined_equity_curve, combined_daily_returns).
        """
        combined_equity: list[dict] = []
        combined_returns: list[float] = []

        # Current capital carries forward across windows
        running_capital = initial_capital

        for wr in window_results:
            test_eq = wr["test_equity"]
            test_rets = wr["test_daily_returns"]

            if not test_eq:
                continue

            # Scale this window's equity curve so it starts at running_capital
            window_start_val = test_eq[0]["value"]
            if window_start_val <= 0:
                window_start_val = initial_capital

            scale = running_capital / window_start_val

            for entry in test_eq:
                scaled_entry = dict(entry)
                scaled_entry["value"] = round(entry["value"] * scale, 2)
                combined_equity.append(scaled_entry)

            combined_returns.extend(test_rets)

            # Update running capital to the end of this window
            if test_eq:
                running_capital = test_eq[-1]["value"] * scale

        return combined_equity, combined_returns

    def _compute_param_stability(self, window_results: list[dict]) -> dict:
        """Assess how stable the optimal parameters are across windows.

        If the same params win most windows, the strategy is robust.
        If params change wildly, it is likely overfit.

        Returns a dict with per-parameter stability info and an overall verdict.
        """
        if not window_results:
            return {"verdict": "no_data", "details": {}}

        # Collect winning values per parameter
        param_values: dict[str, list[Any]] = {}
        for wr in window_results:
            bp = wr["best_params"]
            for key, val in bp.items():
                param_values.setdefault(key, []).append(val)

        details: dict[str, dict] = {}
        stability_scores: list[float] = []

        for param_name, values in param_values.items():
            counter = Counter(values)
            total = len(values)
            most_common_val, most_common_count = counter.most_common(1)[0]
            unique_count = len(counter)

            # Stability score: fraction of windows that chose the most-common value
            stability = most_common_count / total

            details[param_name] = {
                "most_common": most_common_val,
                "most_common_pct": round(stability * 100, 1),
                "unique_values": unique_count,
                "all_values": values,
            }
            stability_scores.append(stability)

        # Overall verdict
        avg_stability = sum(stability_scores) / len(stability_scores) if stability_scores else 0
        if avg_stability >= 0.7:
            verdict = "STABLE — optimal params are consistent across windows (robust strategy)"
        elif avg_stability >= 0.4:
            verdict = "MODERATE — some parameter variation across windows (proceed with caution)"
        else:
            verdict = "UNSTABLE — optimal params change wildly across windows (likely overfit)"

        return {
            "verdict": verdict,
            "avg_stability_pct": round(avg_stability * 100, 1),
            "details": details,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _expand_grid(param_grid: dict[str, list]) -> list[dict]:
    """Expand a parameter grid into a list of all combinations.

    Example::

        _expand_grid({"a": [1, 2], "b": [3, 4]})
        # [{"a": 1, "b": 3}, {"a": 1, "b": 4}, {"a": 2, "b": 3}, {"a": 2, "b": 4}]
    """
    if not param_grid:
        return [{}]

    keys = list(param_grid.keys())
    value_lists = [param_grid[k] for k in keys]

    combos: list[dict] = []
    for vals in itertools.product(*value_lists):
        combos.append(dict(zip(keys, vals)))

    return combos
