"""CLI entry point: python -m hivemind.backtest --start 2025-03-01 --end 2026-03-01 --runs 10"""

from __future__ import annotations

import argparse
import json

from hivemind.backtest.engine import BacktestEngine, BacktestConfig
from hivemind.backtest.walk_forward import WalkForwardConfig, WalkForwardOptimizer, WalkForwardResult
from hivemind.data.models import MarketRegime


def _print_metrics(metrics: dict, header: str = "BACKTEST RESULTS") -> None:
    """Pretty-print a metrics dict."""
    print(f"\n{'=' * 60}")
    print(f"  {header}")
    print(f"{'=' * 60}")
    print(f"  Total Return:      {metrics.get('total_return_pct', 0):>10.2f}%")
    print(f"  Annualised Return: {metrics.get('annualized_return_pct', 0):>10.2f}%")
    print(f"  Sharpe Ratio:      {metrics.get('sharpe_ratio', 0):>10.4f}")
    print(f"  Sortino Ratio:     {metrics.get('sortino_ratio', 0):>10.4f}")
    print(f"  Max Drawdown:      {metrics.get('max_drawdown', 0) * 100:>10.2f}%")
    print(f"  Calmar Ratio:      {metrics.get('calmar_ratio', 0):>10.4f}")
    print(f"  Win Rate:          {metrics.get('win_rate', 0):>10.2f}%")
    print(f"  Profit Factor:     {metrics.get('profit_factor', 0):>10.4f}")
    print(f"  Total Trades:      {int(metrics.get('total_trades', 0)):>10d}")
    print(f"  Avg Trade P&L:     {metrics.get('avg_trade_pnl_pct', 0):>10.4f}%")
    print(f"  vs BTC Hold:       {metrics.get('vs_btc_hold', 0):>10.2f}%")
    print(f"  vs ETH Hold:       {metrics.get('vs_eth_hold', 0):>10.2f}%")
    print(f"  Information Ratio: {metrics.get('information_ratio', 0):>10.4f}")
    print(f"{'=' * 60}")


def _print_monte_carlo(mc: dict) -> None:
    """Pretty-print Monte Carlo results."""
    print(f"\n{'=' * 60}")
    print(f"  MONTE CARLO SIMULATION ({mc['n_simulations']} runs, {mc['n_trades']} trades)")
    print(f"{'=' * 60}")
    print(f"  Median Final Value: ${mc['median_final_value']:>12,.2f}")
    print(f"  5th Percentile:     ${mc['p5_final_value']:>12,.2f}")
    print(f"  25th Percentile:    ${mc['p25_final_value']:>12,.2f}")
    print(f"  75th Percentile:    ${mc['p75_final_value']:>12,.2f}")
    print(f"  95th Percentile:    ${mc['p95_final_value']:>12,.2f}")
    print(f"  Worst Case:         ${mc['worst_final_value']:>12,.2f}")
    print(f"  Best Case:          ${mc['best_final_value']:>12,.2f}")
    print(f"  P(Profitable):      {mc['prob_profitable']:>10.1f}%")
    print(f"  P(Ruin < 50%):      {mc['prob_ruin']:>10.1f}%")
    print(f"{'=' * 60}")


def _print_walk_forward(wf: WalkForwardResult) -> None:
    """Pretty-print walk-forward optimization results."""

    # Per-window summary
    print(f"\n{'=' * 70}")
    print("  WALK-FORWARD OPTIMIZATION — WINDOW RESULTS")
    print(f"{'=' * 70}")

    for w in wf.windows:
        print(
            f"\n  Window {w['window']}: "
            f"{w['train_start']} -> {w['train_end']} (train) | "
            f"{w['test_start']} -> {w['test_end']} (test)"
        )
        print(f"    Best params:  {w['best_params']}")
        print(
            f"    Train metric: {w['best_train_metric']:+.4f}  |  "
            f"Test Sharpe: {w['test_metrics'].get('sharpe_ratio', 0):.4f}  |  "
            f"Test Return: {w['test_metrics'].get('total_return_pct', 0):+.2f}%  |  "
            f"Trades: {w['test_metrics'].get('total_trades', 0)}"
        )

    # Parameter stability
    ps = wf.param_stability
    print(f"\n{'=' * 70}")
    print("  PARAMETER STABILITY")
    print(f"{'=' * 70}")
    print(f"  Verdict: {ps.get('verdict', 'N/A')}")
    print(f"  Avg Stability: {ps.get('avg_stability_pct', 0):.1f}%")

    for param_name, info in ps.get("details", {}).items():
        print(
            f"    {param_name}: most common = {info['most_common']} "
            f"({info['most_common_pct']:.0f}% of windows), "
            f"{info['unique_values']} unique values"
        )
        print(f"      all values: {info['all_values']}")

    # Combined out-of-sample metrics
    _print_metrics(wf.combined_metrics, header="COMBINED OUT-OF-SAMPLE METRICS")
    print(f"  Duration: {wf.duration_secs:.1f}s")
    print(f"  OOS equity curve points: {len(wf.combined_equity)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hivemind Backtester -- walk-forward replay with deterministic signals"
    )
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--runs", type=int, default=1, help="Number of backtest runs (default: 1)")
    parser.add_argument("--capital", type=float, default=100_000.0, help="Initial capital (default: 100000)")
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"], help="Symbols to trade")
    parser.add_argument("--step", type=int, default=24, help="Step size in hours (default: 24)")
    parser.add_argument("--data-dir", default="data/historical", help="Historical data directory")
    parser.add_argument("--monte-carlo", type=int, default=0, help="Number of Monte Carlo simulations (default: 0 = skip)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument(
        "--regime",
        choices=["bull", "bear", "ranging", "crisis"],
        default=None,
        help="Fixed market regime (default: auto-detect)",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch historical data from Binance before running backtest",
    )
    parser.add_argument(
        "--intervals",
        nargs="+",
        default=["1h", "4h", "1d"],
        help="Kline intervals to fetch (default: 1h 4h 1d)",
    )
    parser.add_argument(
        "--walk-forward",
        action="store_true",
        help="Run walk-forward optimization instead of a regular backtest",
    )
    parser.add_argument(
        "--wf-train-days",
        type=int,
        default=180,
        help="Walk-forward: training window in days (default: 180)",
    )
    parser.add_argument(
        "--wf-test-days",
        type=int,
        default=90,
        help="Walk-forward: test window in days (default: 90)",
    )
    parser.add_argument(
        "--wf-step-days",
        type=int,
        default=30,
        help="Walk-forward: step size in days (default: 30)",
    )
    parser.add_argument(
        "--sizing",
        choices=["fixed", "kelly", "vol_target", "adaptive"],
        default="fixed",
        help="Position sizing mode (default: fixed). 'kelly' uses quarter-Kelly from rolling trade history. 'vol_target' targets 25%% annualized vol. 'adaptive' uses min(kelly, vol_target).",
    )
    parser.add_argument(
        "--strategies",
        nargs="+",
        default=["trend_following"],
        choices=["trend_following", "funding_carry", "pairs_btc_eth", "combined"],
        help="Trading strategies to run (default: trend_following). "
             "Options: trend_following, funding_carry, pairs_btc_eth, combined. "
             "Use 'combined' to run all three and average their signals.",
    )
    parser.add_argument(
        "--funding-data-dir",
        default="data/funding_rates",
        help="Directory for funding rate data (default: data/funding_rates)",
    )
    parser.add_argument(
        "--fetch-funding",
        action="store_true",
        help="Fetch funding rate data from Binance Futures before running backtest",
    )

    args = parser.parse_args()

    # Fetch historical data — auto-fetch if no data exists for any symbol
    from hivemind.data.historical import HistoricalDataStore

    store = HistoricalDataStore(storage_dir=args.data_dir)
    need_fetch = args.fetch

    if not need_fetch:
        # Check if data exists for all symbols
        available = store.list_available()
        for sym in args.symbols:
            if sym not in available or "4h" not in available[sym]:
                need_fetch = True
                print(f"No historical data found for {sym}. Auto-fetching...")
                break

    if need_fetch:
        print(f"Fetching historical data for {args.symbols} from {args.start} to {args.end}...")
        print(f"Intervals: {args.intervals}")
        print("This may take a few minutes for large date ranges...\n")
        store.fetch_and_store(
            symbols=args.symbols,
            start_date=args.start,
            end_date=args.end,
            intervals=args.intervals,
        )
        print("Fetch complete.\n")

    # Fetch funding rate data if requested or needed
    needs_funding = (
        "funding_carry" in args.strategies or "combined" in args.strategies
    )
    if args.fetch_funding or needs_funding:
        from hivemind.data.funding_rates import FundingRateStore as _FRS
        funding_store = _FRS(storage_dir=args.funding_data_dir)
        available_funding = funding_store.list_available()
        funding_symbols_needed = [
            s for s in args.symbols if s not in available_funding
        ]

        if args.fetch_funding or funding_symbols_needed:
            fetch_syms = args.symbols if args.fetch_funding else funding_symbols_needed
            if fetch_syms:
                print(f"Fetching funding rates for {fetch_syms} from {args.start} to {args.end}...")
                funding_store.fetch_and_store(
                    symbols=fetch_syms,
                    start_date=args.start,
                    end_date=args.end,
                )
                print("Funding rate fetch complete.\n")

    # Build config
    regime = MarketRegime(args.regime) if args.regime else None

    config = BacktestConfig(
        start_date=args.start,
        end_date=args.end,
        initial_capital=args.capital,
        symbols=args.symbols,
        regime=regime,
        step_hours=args.step,
        storage_dir=args.data_dir,
        sizing_mode=args.sizing,
        strategies=args.strategies,
        funding_rates_dir=args.funding_data_dir,
    )

    engine = BacktestEngine()

    # ── Walk-forward optimization ──
    if args.walk_forward:
        wf_config = WalkForwardConfig(
            train_days=args.wf_train_days,
            test_days=args.wf_test_days,
            step_days=args.wf_step_days,
        )
        optimizer = WalkForwardOptimizer()

        print(
            f"Running walk-forward optimization: {args.start} to {args.end} "
            f"on {args.symbols}..."
        )

        wf_result = optimizer.run(config, wf_config)

        if args.json:
            output = {
                "combined_metrics": wf_result.combined_metrics,
                "param_stability": {
                    k: v for k, v in wf_result.param_stability.items()
                    if k != "details"
                },
                "param_stability_details": {
                    param: {
                        "most_common": info["most_common"],
                        "most_common_pct": info["most_common_pct"],
                        "unique_values": info["unique_values"],
                        "all_values": info["all_values"],
                    }
                    for param, info in wf_result.param_stability.get("details", {}).items()
                },
                "windows": [
                    {
                        "window": w["window"],
                        "train_start": w["train_start"],
                        "train_end": w["train_end"],
                        "test_start": w["test_start"],
                        "test_end": w["test_end"],
                        "best_params": w["best_params"],
                        "best_train_metric": w["best_train_metric"],
                        "test_metrics": w["test_metrics"],
                    }
                    for w in wf_result.windows
                ],
                "duration_secs": wf_result.duration_secs,
            }
            print(json.dumps(output, indent=2, default=str))
        else:
            _print_walk_forward(wf_result)

        return  # Walk-forward complete; skip regular backtest path

    if args.runs > 1:
        print(f"Running {args.runs} backtest runs...")
        multi = engine.run_multi(config, n_runs=args.runs)

        if args.json:
            output = {
                "avg_metrics": multi.avg_metrics,
                "std_metrics": multi.std_metrics,
                "runs": [
                    {
                        "metrics": r.metrics,
                        "duration_secs": r.duration_secs,
                        "n_trades": len(r.trades),
                    }
                    for r in multi.runs
                ],
            }
            print(json.dumps(output, indent=2, default=str))
        else:
            _print_metrics(multi.avg_metrics, header=f"AVERAGED METRICS ({args.runs} runs)")

            # Show standard deviations
            print("\n  Standard Deviations:")
            for key, val in multi.std_metrics.items():
                if isinstance(val, (int, float)):
                    print(f"    {key}: +/- {val:.4f}")

            # Summary of individual runs
            print(f"\n  Individual Runs:")
            for i, run in enumerate(multi.runs):
                ret = run.metrics.get("total_return_pct", 0)
                sharpe = run.metrics.get("sharpe_ratio", 0)
                dd = run.metrics.get("max_drawdown", 0) * 100
                print(f"    Run {i+1}: return={ret:+.2f}%  sharpe={sharpe:.4f}  maxDD={dd:.2f}%  ({run.duration_secs:.1f}s)")

        # Monte Carlo on the first run's trades
        if args.monte_carlo > 0 and multi.runs:
            mc = engine.monte_carlo(
                multi.runs[0].trades,
                n_simulations=args.monte_carlo,
                initial_capital=config.initial_capital,
            )
            if args.json:
                print(json.dumps({"monte_carlo": mc}, indent=2))
            else:
                _print_monte_carlo(mc)
    else:
        print(f"Running backtest: {args.start} to {args.end} on {args.symbols}...")
        print(f"Strategies: {', '.join(args.strategies)}")
        result = engine.run(config)

        if args.json:
            output = {
                "metrics": result.metrics,
                "equity_curve_summary": {
                    "start": result.equity_curve[0] if result.equity_curve else None,
                    "end": result.equity_curve[-1] if result.equity_curve else None,
                    "n_points": len(result.equity_curve),
                },
                "trades": result.trades,
                "duration_secs": result.duration_secs,
            }
            print(json.dumps(output, indent=2, default=str))
        else:
            _print_metrics(result.metrics)
            print(f"\n  Duration: {result.duration_secs:.1f}s")
            print(f"  Equity curve points: {len(result.equity_curve)}")
            print(f"  Total trades executed: {len(result.trades)}")

            # Show equity curve summary
            if result.equity_curve:
                first = result.equity_curve[0]
                last = result.equity_curve[-1]
                print(f"\n  Start: ${first['value']:,.2f} ({first['date'][:10]})")
                print(f"  End:   ${last['value']:,.2f} ({last['date'][:10]})")

            # Show recent trades
            if result.trades:
                print(f"\n  Last 10 trades:")
                for t in result.trades[-10:]:
                    pnl_str = f"  P&L: {t['trade_pnl_pct']:+.2f}%" if t.get("trade_pnl_pct") is not None else ""
                    print(f"    {t['date'][:10]} {t['side']:<5} {t['symbol']:<10} qty={t['quantity']:.6f} @ ${t['price']:,.2f}{pnl_str}")

        # Monte Carlo
        if args.monte_carlo > 0:
            mc = engine.monte_carlo(
                result.trades,
                n_simulations=args.monte_carlo,
                initial_capital=config.initial_capital,
            )
            if args.json:
                print(json.dumps({"monte_carlo": mc}, indent=2))
            else:
                _print_monte_carlo(mc)


if __name__ == "__main__":
    main()
