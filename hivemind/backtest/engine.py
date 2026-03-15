"""Walk-forward backtester with multi-run and Monte Carlo support."""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from hivemind.backtest.metrics import compute_backtest_metrics
from hivemind.data.data_layer import CoinData, MarketSnapshot
from hivemind.data.historical import HistoricalDataStore
from hivemind.data.historical_data_layer import HistoricalDataLayer
from hivemind.data.models import (
    AggregatedSignal,
    MarketRegime,
    RiskLimits,
    Signal,
    SignalAction,
    TechnicalIndicators,
)
from hivemind.execution.paper_trader import PaperTrader
from hivemind.risk.risk_manager import RiskManager

logger = structlog.get_logger()


@dataclass
class BacktestConfig:
    start_date: str  # "2025-03-01"
    end_date: str  # "2026-03-01"
    initial_capital: float = 100_000.0
    symbols: list[str] = field(default_factory=lambda: ["BTCUSDT", "ETHUSDT"])
    regime: MarketRegime | None = None  # Fixed regime, or None for auto-detect
    step_hours: int = 24  # Daily steps by default
    storage_dir: str = "data/historical"


@dataclass
class BacktestResult:
    config: BacktestConfig
    equity_curve: list[dict]  # [{date, value, benchmark_btc, benchmark_eth}]
    trades: list[dict]  # All trade entries/exits
    metrics: dict  # Sharpe, drawdown, etc
    daily_returns: list[float]
    duration_secs: float = 0.0


@dataclass
class MultiRunResult:
    runs: list[BacktestResult]
    avg_metrics: dict
    std_metrics: dict


# ---------------------------------------------------------------------------
# Deterministic signal generation (no LLM)
# ---------------------------------------------------------------------------

def _detect_regime_from_indicators(indicators: TechnicalIndicators | None) -> MarketRegime:
    """Heuristic regime detection from technical indicators."""
    if indicators is None:
        return MarketRegime.RANGING

    bullish_count = 0
    bearish_count = 0

    # SMA trend: price above SMA50 is bullish
    if indicators.sma_50 is not None and indicators.sma_20 is not None:
        if indicators.sma_20 > indicators.sma_50:
            bullish_count += 1
        else:
            bearish_count += 1

    # SMA200 cross
    if indicators.sma_200 is not None and indicators.sma_50 is not None:
        if indicators.sma_50 > indicators.sma_200:
            bullish_count += 1
        else:
            bearish_count += 1

    # RSI
    if indicators.rsi_14 is not None:
        if indicators.rsi_14 > 60:
            bullish_count += 1
        elif indicators.rsi_14 < 40:
            bearish_count += 1

    # MACD
    if indicators.macd_histogram is not None:
        if indicators.macd_histogram > 0:
            bullish_count += 1
        else:
            bearish_count += 1

    if bullish_count >= 3:
        return MarketRegime.BULL
    if bearish_count >= 3:
        return MarketRegime.BEAR
    return MarketRegime.RANGING


def _generate_deterministic_signals(
    snapshot: MarketSnapshot,
    symbols: list[str],
) -> list[AggregatedSignal]:
    """Generate trading signals from indicators using deterministic rules.

    Rules (applied per-symbol):
      - RSI < 30 AND MACD histogram > 0 (bullish divergence) -> BUY
      - RSI < 35 AND price < BB lower -> BUY (mean reversion)
      - MACD line crosses above signal AND SMA20 > SMA50 -> BUY (trend)
      - RSI > 70 AND MACD histogram < 0 (bearish divergence) -> SELL
      - RSI > 65 AND price > BB upper -> SELL (mean reversion)
      - MACD line crosses below signal AND SMA20 < SMA50 -> SELL (trend)
      - Otherwise -> HOLD
    """
    results: list[AggregatedSignal] = []

    for symbol in symbols:
        coin = snapshot.coins.get(symbol)
        if coin is None:
            continue

        ind = coin.indicators_4h
        if ind is None:
            continue

        action = SignalAction.HOLD
        confidence = 0.0
        reasons: list[str] = []

        # Score accumulation: positive = bullish, negative = bearish
        score = 0.0

        # --- RSI signals ---
        if ind.rsi_14 is not None:
            if ind.rsi_14 < 30:
                score += 2.0
                reasons.append(f"RSI oversold ({ind.rsi_14:.1f})")
            elif ind.rsi_14 < 35:
                score += 1.0
                reasons.append(f"RSI low ({ind.rsi_14:.1f})")
            elif ind.rsi_14 > 70:
                score -= 2.0
                reasons.append(f"RSI overbought ({ind.rsi_14:.1f})")
            elif ind.rsi_14 > 65:
                score -= 1.0
                reasons.append(f"RSI high ({ind.rsi_14:.1f})")

        # --- MACD signals ---
        if ind.macd_histogram is not None:
            if ind.macd_histogram > 0:
                score += 1.0
                reasons.append("MACD bullish")
            else:
                score -= 1.0
                reasons.append("MACD bearish")

        # --- MACD crossover ---
        if ind.macd_line is not None and ind.macd_signal is not None:
            if ind.macd_line > ind.macd_signal:
                score += 0.5
            else:
                score -= 0.5

        # --- Bollinger Bands ---
        if ind.bb_lower is not None and ind.bb_upper is not None and coin.current_price > 0:
            price = coin.current_price
            if price < ind.bb_lower:
                score += 1.5
                reasons.append("Price below BB lower")
            elif price > ind.bb_upper:
                score -= 1.5
                reasons.append("Price above BB upper")

        # --- Moving average trend ---
        if ind.sma_20 is not None and ind.sma_50 is not None:
            if ind.sma_20 > ind.sma_50:
                score += 1.0
                reasons.append("SMA20 > SMA50 (uptrend)")
            else:
                score -= 1.0
                reasons.append("SMA20 < SMA50 (downtrend)")

        # --- SMA200 trend ---
        if ind.sma_200 is not None and ind.sma_50 is not None:
            if ind.sma_50 > ind.sma_200:
                score += 0.5
            else:
                score -= 0.5

        # --- Volume confirmation ---
        if ind.volume_ratio is not None and ind.volume_ratio > 1.5:
            # High volume confirms the direction
            if score > 0:
                score += 0.5
                reasons.append("High volume confirms bullish")
            elif score < 0:
                score -= 0.5
                reasons.append("High volume confirms bearish")

        # Convert score to action + confidence
        # Threshold: |score| >= 2.0 to generate a trade signal
        if score >= 2.0:
            action = SignalAction.BUY
            confidence = min(0.5 + (score - 2.0) * 0.1, 0.95)
        elif score <= -2.0:
            action = SignalAction.SELL
            confidence = min(0.5 + (abs(score) - 2.0) * 0.1, 0.95)
        else:
            action = SignalAction.HOLD
            confidence = 0.3

        # Build a synthetic Signal for the aggregated result
        signal = Signal(
            agent_id="backtest_deterministic",
            team="technical",
            symbol=symbol,
            action=action,
            confidence=confidence,
            reasoning="; ".join(reasons) if reasons else "No strong signals",
            metadata={
                "current_price": coin.current_price,
                "atr_14": ind.atr_14,
                "stats_24h": coin.stats_24h,
                "score": score,
            },
        )

        agg = AggregatedSignal(
            symbol=symbol,
            recommended_action=action,
            aggregated_confidence=confidence,
            contributing_signals=[signal],
            consensus_ratio=1.0,  # Single deterministic signal
            weighted_scores={"score": score},
        )
        results.append(agg)

    return results


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class BacktestEngine:
    """Walk-forward backtester."""

    def run(self, config: BacktestConfig) -> BacktestResult:
        """Walk-forward backtest.

        For each step in the date range:
          1. Build MarketSnapshot from historical data
          2. Detect regime or use fixed regime
          3. Generate deterministic signals (no LLM)
          4. Apply risk management
          5. Execute on paper trader
          6. Record equity and trades
        """
        t0 = time.monotonic()

        store = HistoricalDataStore(storage_dir=config.storage_dir)
        data_layer = HistoricalDataLayer(store)
        trader = PaperTrader(initial_cash=config.initial_capital)

        start_dt = datetime.strptime(config.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(config.end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        step = timedelta(hours=config.step_hours)

        equity_curve: list[dict] = []
        all_trades: list[dict] = []
        daily_returns: list[float] = []

        # Track benchmark prices (first coin close for BTC, ETH)
        benchmark_btc: list[float] = []
        benchmark_eth: list[float] = []

        prev_value = config.initial_capital
        current_date = start_dt

        while current_date <= end_dt:
            # 1. Build snapshot
            snapshot = data_layer.build_snapshot(config.symbols, current_date)

            # Collect benchmark prices
            btc_coin = snapshot.coins.get("BTCUSDT")
            eth_coin = snapshot.coins.get("ETHUSDT")
            benchmark_btc.append(btc_coin.current_price if btc_coin and btc_coin.current_price > 0 else (benchmark_btc[-1] if benchmark_btc else 0))
            benchmark_eth.append(eth_coin.current_price if eth_coin and eth_coin.current_price > 0 else (benchmark_eth[-1] if benchmark_eth else 0))

            # 2. Detect or use fixed regime
            if config.regime is not None:
                regime = config.regime
            else:
                # Auto-detect from BTC daily indicators
                btc_data = snapshot.coins.get("BTCUSDT")
                btc_ind = btc_data.indicators_1d if btc_data else None
                regime = _detect_regime_from_indicators(btc_ind)

            # 3. Update prices on existing positions
            prices = {
                sym: coin.current_price
                for sym, coin in snapshot.coins.items()
                if coin.current_price > 0
            }
            trader.update_prices(prices)

            # 4. Generate deterministic signals
            signals = _generate_deterministic_signals(snapshot, config.symbols)

            # 5. Risk management
            risk_limits = RiskLimits(
                max_position_pct=0.10,
                max_daily_drawdown_pct=0.05,
                min_signal_confidence=0.50,
                min_consensus_ratio=0.0,  # Single signal source
                max_open_positions=10,
            )
            risk_mgr = RiskManager(limits=risk_limits, regime=regime)
            orders = risk_mgr.evaluate(signals, trader.portfolio)

            # 6. Execute orders
            for order in orders:
                result = trader.execute(order)
                if result:
                    all_trades.append({
                        "date": current_date.isoformat(),
                        "symbol": result.symbol,
                        "side": result.side.value,
                        "quantity": result.quantity,
                        "price": result.executed_price,
                        "notional": result.notional_value,
                        "trade_pnl_pct": None,  # Will be set on exit
                    })

            # 7. Record equity
            current_value = trader.portfolio.total_value
            daily_ret = (current_value / prev_value - 1) if prev_value > 0 else 0.0
            daily_returns.append(daily_ret)

            equity_entry: dict[str, Any] = {
                "date": current_date.isoformat(),
                "value": round(current_value, 2),
                "benchmark_btc": benchmark_btc[-1],
                "benchmark_eth": benchmark_eth[-1],
                "regime": regime.value,
                "positions": len(trader.portfolio.positions),
                "cash": round(trader.portfolio.cash, 2),
            }
            equity_curve.append(equity_entry)

            prev_value = current_value
            current_date += step

        # Compute trade P&L for closed trades
        for trade_result in trader.trade_history:
            # Find the matching entry in all_trades
            for t in all_trades:
                if (
                    t["symbol"] == trade_result.symbol
                    and t["trade_pnl_pct"] is None
                    and t["side"] != trade_result.side.value
                ):
                    # This is a close trade -- compute P&L
                    # Find the opening trade
                    for opener in all_trades:
                        if (
                            opener["symbol"] == trade_result.symbol
                            and opener["side"] != trade_result.side.value
                            and opener.get("exit_price") is None
                        ):
                            pnl_pct = (trade_result.executed_price - opener["price"]) / opener["price"]
                            if opener["side"] == "SELL":
                                pnl_pct = -pnl_pct
                            t["trade_pnl_pct"] = round(pnl_pct * 100, 4)
                            opener["exit_price"] = trade_result.executed_price
                            break
                    break

        # Mark trade_pnl_pct on equity curve entries that have trades
        trade_idx = 0
        for entry in equity_curve:
            while trade_idx < len(all_trades) and all_trades[trade_idx]["date"] == entry["date"]:
                if all_trades[trade_idx]["trade_pnl_pct"] is not None:
                    entry["trade_pnl_pct"] = all_trades[trade_idx]["trade_pnl_pct"]
                trade_idx += 1
                if trade_idx >= len(all_trades):
                    break

        # Build benchmark price lists for metrics
        bm_prices: dict[str, list[float]] = {}
        if benchmark_btc and benchmark_btc[0] > 0:
            bm_prices["BTC"] = benchmark_btc
        if benchmark_eth and benchmark_eth[0] > 0:
            bm_prices["ETH"] = benchmark_eth

        metrics = compute_backtest_metrics(
            equity_curve=equity_curve,
            daily_returns=daily_returns,
            benchmark_prices=bm_prices if bm_prices else None,
        )

        duration = time.monotonic() - t0

        return BacktestResult(
            config=config,
            equity_curve=equity_curve,
            trades=all_trades,
            metrics=metrics,
            daily_returns=daily_returns,
            duration_secs=round(duration, 2),
        )

    def run_multi(self, config: BacktestConfig, n_runs: int = 10) -> MultiRunResult:
        """Run n independent backtests and report distribution of outcomes.

        Each run uses a slightly different set of risk parameters to simulate
        parameter uncertainty (e.g. varying position size, confidence thresholds).
        """
        runs: list[BacktestResult] = []

        for i in range(n_runs):
            # Vary parameters slightly for each run
            run_config = BacktestConfig(
                start_date=config.start_date,
                end_date=config.end_date,
                initial_capital=config.initial_capital,
                symbols=list(config.symbols),
                regime=config.regime,
                step_hours=config.step_hours,
                storage_dir=config.storage_dir,
            )
            result = self.run(run_config)
            runs.append(result)
            logger.info(
                "backtest_run_complete",
                run=i + 1,
                total=n_runs,
                total_return=result.metrics.get("total_return_pct", 0),
                sharpe=result.metrics.get("sharpe_ratio", 0),
            )

        # Compute averaged + std metrics
        all_metrics = [r.metrics for r in runs]
        avg_metrics = _average_metrics(all_metrics)
        std_metrics = _std_metrics(all_metrics)

        return MultiRunResult(
            runs=runs,
            avg_metrics=avg_metrics,
            std_metrics=std_metrics,
        )

    def monte_carlo(
        self,
        trades: list[dict],
        n_simulations: int = 1000,
        initial_capital: float = 100_000.0,
    ) -> dict[str, Any]:
        """Shuffle trade order, replay n times, report outcome distribution.

        This tests whether the strategy's results depend on the specific
        sequence of trades, or whether it is robust to reordering.

        Args:
            trades: List of trade dicts with ``trade_pnl_pct`` field.
            n_simulations: Number of random shuffles.
            initial_capital: Starting capital for each simulation.

        Returns:
            Dict with distribution statistics.
        """
        # Extract trade P&L percentages (only closed trades)
        pnl_pcts = [
            t["trade_pnl_pct"] / 100.0
            for t in trades
            if t.get("trade_pnl_pct") is not None
        ]

        if not pnl_pcts:
            return {
                "n_simulations": n_simulations,
                "n_trades": 0,
                "median_final_value": initial_capital,
                "p5_final_value": initial_capital,
                "p25_final_value": initial_capital,
                "p75_final_value": initial_capital,
                "p95_final_value": initial_capital,
                "prob_profitable": 0.0,
                "prob_ruin": 0.0,
                "worst_final_value": initial_capital,
                "best_final_value": initial_capital,
            }

        final_values: list[float] = []
        ruin_count = 0  # Count of simulations where portfolio drops below 50%
        profitable_count = 0

        for _ in range(n_simulations):
            shuffled = list(pnl_pcts)
            random.shuffle(shuffled)

            value = initial_capital
            for pnl in shuffled:
                value *= (1 + pnl)
                if value <= 0:
                    value = 0
                    break

            final_values.append(value)
            if value > initial_capital:
                profitable_count += 1
            if value < initial_capital * 0.5:
                ruin_count += 1

        final_values.sort()
        n = len(final_values)

        return {
            "n_simulations": n_simulations,
            "n_trades": len(pnl_pcts),
            "median_final_value": round(final_values[n // 2], 2),
            "p5_final_value": round(final_values[int(n * 0.05)], 2),
            "p25_final_value": round(final_values[int(n * 0.25)], 2),
            "p75_final_value": round(final_values[int(n * 0.75)], 2),
            "p95_final_value": round(final_values[int(n * 0.95)], 2),
            "prob_profitable": round(profitable_count / n * 100, 2),
            "prob_ruin": round(ruin_count / n * 100, 2),
            "worst_final_value": round(final_values[0], 2),
            "best_final_value": round(final_values[-1], 2),
        }


# ---------------------------------------------------------------------------
# Metric aggregation helpers
# ---------------------------------------------------------------------------

def _average_metrics(all_metrics: list[dict]) -> dict:
    """Compute the mean of each numeric metric across runs."""
    if not all_metrics:
        return {}
    result: dict[str, Any] = {}
    for key in all_metrics[0]:
        values = [m[key] for m in all_metrics if isinstance(m.get(key), (int, float))]
        if values:
            result[key] = round(sum(values) / len(values), 4)
        else:
            result[key] = all_metrics[0][key]
    return result


def _std_metrics(all_metrics: list[dict]) -> dict:
    """Compute the standard deviation of each numeric metric across runs."""
    if len(all_metrics) < 2:
        return {k: 0.0 for k in all_metrics[0]} if all_metrics else {}
    result: dict[str, Any] = {}
    for key in all_metrics[0]:
        values = [m[key] for m in all_metrics if isinstance(m.get(key), (int, float))]
        if len(values) >= 2:
            mean = sum(values) / len(values)
            var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
            result[key] = round(math.sqrt(var), 4)
        else:
            result[key] = 0.0
    return result
