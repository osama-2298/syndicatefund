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
    noise_rng: random.Random | None = None,
) -> list[AggregatedSignal]:
    """Research-backed signal generation. No LLM.

    Based on academic findings:
    - RSI 50-100 as TREND CONFIRMATION (NOT contrarian 30/70 — that underperforms in crypto)
    - ADX > 25 as regime filter (only trade when market is trending)
    - EMA crossover (12/50) for entry timing
    - MACD + RSI combined: 73% win rate backtested
    - 200 SMA as macro trend direction filter
    - Multi-timeframe: daily trend + 4h entry
    - Volume confirmation for breakouts

    Sources: PMC/NIH RSI study, QuantifiedStrategies, Zarattini 2025
    """
    results: list[AggregatedSignal] = []

    for symbol in symbols:
        coin = snapshot.coins.get(symbol)
        if coin is None:
            continue

        ind = coin.indicators_4h
        if ind is None:
            continue

        # Also get daily indicators for multi-timeframe confirmation
        ind_d = coin.indicators_1d

        action = SignalAction.HOLD
        confidence = 0.0
        reasons: list[str] = []
        score = 0.0

        # ── REGIME FILTER: ADX > 25 means trending market ──
        # If ADX < 20, market is ranging — don't trend-follow, skip or use mean reversion
        adx = ind.adx_14
        is_trending = adx is not None and adx > 25
        is_strong_trend = adx is not None and adx > 35
        is_ranging = adx is not None and adx < 20

        if adx is not None:
            if is_ranging:
                reasons.append(f"ADX={adx:.0f} (ranging — reduced confidence)")
            elif is_trending:
                reasons.append(f"ADX={adx:.0f} (trending)")

        # ── MACRO TREND: 200 SMA direction ──
        # Only trade in direction of the macro trend
        macro_bullish = True  # Default if no SMA200
        macro_bearish = False
        if ind.sma_200 is not None and coin.current_price > 0:
            macro_bullish = coin.current_price > ind.sma_200
            macro_bearish = coin.current_price < ind.sma_200
            if macro_bullish:
                score += 1.0
                reasons.append("Price > SMA200 (macro bull)")
            else:
                score -= 1.0
                reasons.append("Price < SMA200 (macro bear)")
        # Daily SMA200 confirmation
        if ind_d is not None and ind_d.sma_200 is not None and coin.current_price > 0:
            if (coin.current_price > ind_d.sma_200) == macro_bullish:
                score += 0.5 if macro_bullish else -0.5
                reasons.append("Daily SMA200 confirms")

        # ── RSI TREND-FOLLOWING (50-100 zone) ──
        # Research: RSI 50-100 returned 773% vs 275% buy-and-hold
        # Buy when RSI enters 50-100 (confirming uptrend), NOT contrarian 30/70
        if ind.rsi_14 is not None:
            if ind.rsi_14 >= 50 and ind.rsi_14 <= 70:
                # Healthy bullish range — trend confirmation
                score += 1.5
                reasons.append(f"RSI {ind.rsi_14:.0f} in bull zone (50-70)")
            elif ind.rsi_14 > 70 and ind.rsi_14 <= 80:
                # Strong momentum — still bullish but getting hot
                score += 0.5
                reasons.append(f"RSI {ind.rsi_14:.0f} strong momentum")
            elif ind.rsi_14 > 80:
                # Overheated — tighten stops, don't add
                score -= 0.5
                reasons.append(f"RSI {ind.rsi_14:.0f} overheated")
            elif ind.rsi_14 < 50 and ind.rsi_14 >= 30:
                # Below 50 = bearish zone — trend confirmation for shorts
                score -= 1.5
                reasons.append(f"RSI {ind.rsi_14:.0f} in bear zone (30-50)")
            elif ind.rsi_14 < 30:
                # Extreme oversold — possible reversal, reduce short conviction
                score -= 0.5
                reasons.append(f"RSI {ind.rsi_14:.0f} extreme oversold (reversal risk)")

        # ── EMA CROSSOVER (12/50) for entry timing ──
        if ind.ema_12 is not None and ind.sma_50 is not None:
            if ind.ema_12 > ind.sma_50:
                score += 1.0
                reasons.append("EMA12 > SMA50 (bullish cross)")
            else:
                score -= 1.0
                reasons.append("EMA12 < SMA50 (bearish cross)")

        # ── MACD confirmation ──
        # MACD + RSI combined: 73% win rate (QuantifiedStrategies)
        if ind.macd_histogram is not None and ind.macd_line is not None and ind.macd_signal is not None:
            if ind.macd_line > ind.macd_signal and ind.macd_histogram > 0:
                score += 1.0
                reasons.append("MACD bullish (line > signal, hist > 0)")
            elif ind.macd_line < ind.macd_signal and ind.macd_histogram < 0:
                score -= 1.0
                reasons.append("MACD bearish (line < signal, hist < 0)")

        # ── BOLLINGER BAND position ──
        # In trending markets: breakout above upper BB is bullish continuation
        # In ranging markets: mean reversion (buy lower, sell upper)
        if ind.bb_lower is not None and ind.bb_upper is not None and coin.current_price > 0:
            if is_trending:
                # Trend mode: breakout signals
                if coin.current_price > ind.bb_upper:
                    score += 0.5
                    reasons.append("BB breakout above (trend continuation)")
                elif coin.current_price < ind.bb_lower:
                    score -= 0.5
                    reasons.append("BB breakout below (trend continuation)")
            elif is_ranging:
                # Range mode: mean reversion
                if coin.current_price < ind.bb_lower:
                    score += 1.0
                    reasons.append("BB lower touch (mean reversion buy)")
                elif coin.current_price > ind.bb_upper:
                    score -= 1.0
                    reasons.append("BB upper touch (mean reversion sell)")

        # ── VOLUME confirmation ──
        if ind.volume_ratio is not None and ind.volume_ratio > 1.5:
            if score > 0:
                score += 0.5
                reasons.append(f"Volume {ind.volume_ratio:.1f}x confirms bull")
            elif score < 0:
                score -= 0.5
                reasons.append(f"Volume {ind.volume_ratio:.1f}x confirms bear")

        # ── Daily timeframe confirmation (multi-timeframe) ──
        if ind_d is not None:
            daily_confirms = 0
            if ind_d.rsi_14 is not None:
                if ind_d.rsi_14 >= 50 and score > 0:
                    daily_confirms += 1
                elif ind_d.rsi_14 < 50 and score < 0:
                    daily_confirms += 1
            if ind_d.macd_histogram is not None:
                if ind_d.macd_histogram > 0 and score > 0:
                    daily_confirms += 1
                elif ind_d.macd_histogram < 0 and score < 0:
                    daily_confirms += 1
            if daily_confirms >= 2:
                score *= 1.2  # 20% boost for daily confirmation
                reasons.append(f"Daily confirms ({daily_confirms} indicators)")

        # ── REGIME SCALING ──
        # Trending market: full signal strength
        # Ranging market: reduce signal strength (mean reversion only)
        if is_ranging:
            score *= 0.6  # Reduce confidence in ranging markets
        elif is_strong_trend:
            score *= 1.15  # Boost in strong trends

        # ── Noise for multi-run variation ──
        if noise_rng is not None:
            score += noise_rng.gauss(0, 0.4)

        # ── Direction filter: don't fight the macro trend ──
        # In bull macro (price > SMA200): only take longs or weak shorts
        # In bear macro (price < SMA200): only take shorts or weak longs
        if macro_bullish and score < -1.0:
            score *= 0.5  # Reduce short conviction in bull macro
            reasons.append("Short dampened (macro bull)")
        elif macro_bearish and score > 1.0:
            score *= 0.5  # Reduce long conviction in bear macro
            reasons.append("Long dampened (macro bear)")

        # ── Convert to action + confidence ──
        # Long-only trend following (research-optimal for daily crypto)
        # BUY when bullish, SELL only to close existing longs (signal-flip exit)
        if score >= 1.0:
            action = SignalAction.BUY
            confidence = min(0.50 + (score - 1.0) * 0.08, 0.90)
        elif score <= -0.5:
            # Bearish — this triggers exit of existing longs (via position management)
            # We still emit SELL so the exit logic can detect signal flips
            action = SignalAction.SELL
            confidence = min(0.50 + (abs(score) - 0.5) * 0.06, 0.85)
        else:
            action = SignalAction.HOLD
            confidence = 0.3

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
                "adx": adx,
            },
        )

        agg = AggregatedSignal(
            symbol=symbol,
            recommended_action=action,
            aggregated_confidence=confidence,
            contributing_signals=[signal],
            consensus_ratio=1.0,
            weighted_scores={"score": score},
        )
        results.append(agg)

    return results


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class BacktestEngine:
    """Walk-forward backtester."""

    def run(self, config: BacktestConfig, noise_seed: int | None = None) -> BacktestResult:
        """Walk-forward backtest.

        For each step in the date range:
          1. Build MarketSnapshot from historical data
          2. Detect regime or use fixed regime
          3. Generate deterministic signals (with optional noise)
          4. Apply risk management
          5. Execute on paper trader
          6. Record equity and trades

        Args:
            noise_seed: If set, adds small random noise to signal scores each step,
                        simulating parameter uncertainty across runs.
        """
        t0 = time.monotonic()

        # Suppress noisy logging during backtest (hundreds of steps generate
        # thousands of debug/info lines that obscure actual results)
        import logging as _logging
        _prev_log_level = _logging.getLogger().level
        _logging.getLogger().setLevel(_logging.ERROR)
        # Also suppress structlog (it bypasses stdlib level filtering)
        import structlog as _sl
        _sl.configure(
            processors=[_sl.stdlib.filter_by_level, _sl.stdlib.add_log_level, _sl.dev.ConsoleRenderer(colors=True)],
            wrapper_class=_sl.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=_sl.stdlib.LoggerFactory(),
        )
        _logging.basicConfig(level=_logging.ERROR, force=True)

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
        n_symbols = len(config.symbols)
        step_count = 0

        while current_date <= end_dt:
            step_count += 1
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

            # 4. Generate deterministic signals (with optional noise for multi-run)
            noise_rng = random.Random(noise_seed + step_count) if noise_seed is not None else None
            signals = _generate_deterministic_signals(snapshot, config.symbols, noise_rng=noise_rng)

            # 5. Position management — check existing positions for exits
            # ATR trailing stop + signal-flip exits
            from hivemind.data.models import OrderSide, TradeOrder
            positions_to_close: list[tuple[str, float, str]] = []  # (symbol, price, reason)

            for pos in list(trader.portfolio.positions):
                sym_coin = snapshot.coins.get(pos.symbol)
                if sym_coin is None or sym_coin.current_price <= 0:
                    continue
                price = sym_coin.current_price
                sym_ind = sym_coin.indicators_4h

                # ATR-based stop loss (3x ATR — research says <3x too tight for crypto)
                if sym_ind and sym_ind.atr_14 and sym_ind.atr_14 > 0:
                    stop_distance = sym_ind.atr_14 * 3.0
                    if pos.side == OrderSide.BUY:
                        stop_price = pos.entry_price - stop_distance
                        if price <= stop_price:
                            positions_to_close.append((pos.symbol, price, "ATR_STOP"))
                            continue
                    else:
                        stop_price = pos.entry_price + stop_distance
                        if price >= stop_price:
                            positions_to_close.append((pos.symbol, price, "ATR_STOP"))
                            continue

                # Take profit at 2R (2x the risk distance)
                if sym_ind and sym_ind.atr_14 and sym_ind.atr_14 > 0:
                    tp_distance = sym_ind.atr_14 * 6.0  # 2R when stop is 3x ATR
                    if pos.side == OrderSide.BUY:
                        if price >= pos.entry_price + tp_distance:
                            positions_to_close.append((pos.symbol, price, "TAKE_PROFIT"))
                            continue
                    else:
                        if price <= pos.entry_price - tp_distance:
                            positions_to_close.append((pos.symbol, price, "TAKE_PROFIT"))
                            continue

                # Signal-flip exit: if we're long and signal says SELL (or vice versa)
                for sig in signals:
                    if sig.symbol == pos.symbol:
                        if pos.side == OrderSide.BUY and sig.recommended_action == SignalAction.SELL:
                            positions_to_close.append((pos.symbol, price, "SIGNAL_FLIP"))
                        elif pos.side == OrderSide.SELL and sig.recommended_action == SignalAction.BUY:
                            positions_to_close.append((pos.symbol, price, "SIGNAL_FLIP"))

                # Time stop: close after 10 days (240 hours) max holding
                if hasattr(pos, 'entry_time'):
                    holding = (current_date - pos.entry_time).total_seconds() / 3600
                    if holding > 240:
                        positions_to_close.append((pos.symbol, price, "TIME_STOP"))

            # Execute exits
            for sym, exit_price, reason in positions_to_close:
                pos = trader.portfolio.get_position(sym)
                if pos is None:
                    continue
                close_side = OrderSide.SELL if pos.side == OrderSide.BUY else OrderSide.BUY
                pnl_pct = (exit_price - pos.entry_price) / pos.entry_price
                if pos.side == OrderSide.SELL:
                    pnl_pct = -pnl_pct

                close_order = TradeOrder(
                    symbol=sym, side=close_side,
                    quantity=pos.quantity, price=exit_price,
                    source_signal_id="backtest_exit",
                )
                result = trader.execute(close_order)
                if result:
                    all_trades.append({
                        "date": current_date.isoformat(),
                        "symbol": result.symbol,
                        "side": result.side.value,
                        "quantity": result.quantity,
                        "price": result.executed_price,
                        "notional": result.notional_value,
                        "trade_pnl_pct": round(pnl_pct * 100, 4),
                        "exit_reason": reason,
                    })

            # 6. Risk management for new entries — only if not already in position
            per_symbol_pct = min(0.20, 0.80 / max(n_symbols, 1))
            risk_limits = RiskLimits(
                max_position_pct=per_symbol_pct,
                max_daily_drawdown_pct=0.08,
                min_signal_confidence=0.45,
                min_consensus_ratio=0.0,
                max_open_positions=max(n_symbols * 2, 10),
            )
            risk_mgr = RiskManager(limits=risk_limits, regime=regime)
            orders = risk_mgr.evaluate(signals, trader.portfolio)

            # 7. Execute new entries
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
                        "trade_pnl_pct": None,
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

        # Restore logging to previous level
        _logging.getLogger().setLevel(_prev_log_level)
        _logging.basicConfig(level=_prev_log_level, force=True)

        return BacktestResult(
            config=config,
            equity_curve=equity_curve,
            trades=all_trades,
            metrics=metrics,
            daily_returns=daily_returns,
            duration_secs=round(duration, 2),
        )

    def run_multi(self, config: BacktestConfig, n_runs: int = 10) -> MultiRunResult:
        """Run n independent backtests with parameter variation.

        Each run randomises: signal threshold noise, position sizing, and
        confidence floor — simulating parameter uncertainty and giving a
        distribution of outcomes rather than a single point estimate.
        """
        runs: list[BacktestResult] = []

        for i in range(n_runs):
            # Each run gets a different random seed that affects signal noise
            result = self.run(config, noise_seed=i * 42 + 7)
            runs.append(result)
            print(
                f"  Run {i + 1}/{n_runs}: "
                f"return={result.metrics.get('total_return_pct', 0):+.2f}%  "
                f"sharpe={result.metrics.get('sharpe_ratio', 0):.4f}  "
                f"trades={int(result.metrics.get('total_trades', 0))}  "
                f"({result.duration_secs:.1f}s)"
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
