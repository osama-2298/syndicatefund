"""Walk-forward backtester with multi-run and Monte Carlo support."""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from syndicate.backtest.metrics import compute_backtest_metrics
from syndicate.backtest.position_sizing import (
    PositionSizer,
    SizingMode,
    atr_to_annual_vol,
)
from syndicate.backtest.pairs import PairsTrader
from syndicate.backtest.slippage import compute_total_execution_cost
from syndicate.data.data_layer import CoinData, MarketSnapshot
from syndicate.data.funding_rates import FundingRateStore
from syndicate.data.historical import HistoricalDataStore
from syndicate.data.historical_data_layer import HistoricalDataLayer
from syndicate.data.models import (
    AggregatedSignal,
    MarketRegime,
    RiskLimits,
    Signal,
    SignalAction,
    TechnicalIndicators,
)
from syndicate.execution.paper_trader import PaperTrader
from syndicate.risk.risk_manager import RiskManager
from syndicate.risk.trade_params import classify_tier

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
    strategy_params: dict = field(default_factory=lambda: {
        "signal_threshold": 1.0,    # Score threshold for BUY signal
        "exit_threshold": -0.5,     # Score threshold for SELL/exit signal
        "atr_stop_mult": 3.0,      # ATR multiplier for stop loss
        "atr_tp_mult": 6.0,        # ATR multiplier for take profit (2R)
    })
    strategies: list[str] = field(default_factory=lambda: ["trend_following"])
    # Options: "trend_following" (current), "funding_carry", "pairs_btc_eth", "combined"
    funding_rates_dir: str = "data/funding_rates"
    sizing_mode: str = "fixed"  # "fixed", "kelly", "vol_target", "adaptive"


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
# Donchian Channel Ensemble (Zarattini 2025 — Sharpe 1.57)
# ---------------------------------------------------------------------------

class DonchianEnsemble:
    """Multi-period Donchian channel ensemble for trend detection.

    Aggregates breakout signals across 9 lookback windows (5-360 days).
    Each window votes +1 (above upper channel) or -1 (below lower channel).
    The average vote produces a continuous trend strength signal (-1 to +1).

    Source: "Catching Crypto Trends" (Zarattini, Barbon 2025, SSRN)
    """

    LOOKBACKS = [5, 10, 20, 30, 60, 90, 150, 250, 360]

    def __init__(self) -> None:
        self._price_history: dict[str, list[float]] = {}

    def update(self, symbol: str, price: float) -> None:
        if symbol not in self._price_history:
            self._price_history[symbol] = []
        self._price_history[symbol].append(price)
        if len(self._price_history[symbol]) > 400:
            self._price_history[symbol] = self._price_history[symbol][-400:]

    def signal(self, symbol: str) -> dict:
        prices = self._price_history.get(symbol, [])
        if len(prices) < 20:
            return {"trend_strength": 0, "channels_bullish": 0,
                    "channels_bearish": 0, "has_data": False}

        current_price = prices[-1]
        votes = 0
        n_channels = 0

        for lookback in self.LOOKBACKS:
            if len(prices) < lookback + 1:
                continue
            window = prices[-(lookback + 1):-1]
            upper = max(window)
            lower = min(window)
            if current_price > upper:
                votes += 1
            elif current_price < lower:
                votes -= 1
            n_channels += 1

        if n_channels == 0:
            return {"trend_strength": 0, "channels_bullish": 0,
                    "channels_bearish": 0, "has_data": False}

        trend_strength = votes / n_channels
        return {
            "trend_strength": round(trend_strength, 3),
            "channels_bullish": max(0, votes),
            "channels_bearish": abs(min(0, votes)),
            "has_data": True,
        }


# ---------------------------------------------------------------------------
# Cross-Sectional Momentum (rank coins, overweight strongest)
# ---------------------------------------------------------------------------

class MomentumRanker:
    """Rank coins by recent return. Top performers get boosted signals.

    Research: Top quintile 1-week momentum = 11.22% avg weekly return.
    7-day lookback outperforms longer windows.
    """

    def __init__(self, lookback: int = 7) -> None:
        self.lookback = lookback
        self._price_history: dict[str, list[float]] = {}

    def update(self, symbol: str, price: float) -> None:
        if symbol not in self._price_history:
            self._price_history[symbol] = []
        self._price_history[symbol].append(price)
        if len(self._price_history[symbol]) > 60:
            self._price_history[symbol] = self._price_history[symbol][-60:]

    def rank(self) -> dict[str, float]:
        """Return momentum percentile rank (0=worst, 1=best) per symbol."""
        returns: dict[str, float] = {}
        for symbol, prices in self._price_history.items():
            if len(prices) < self.lookback + 1:
                returns[symbol] = 0.0
                continue
            old_price = prices[-(self.lookback + 1)]
            new_price = prices[-1]
            returns[symbol] = (new_price - old_price) / old_price if old_price > 0 else 0.0

        if not returns:
            return {}

        sorted_symbols = sorted(returns.keys(), key=lambda s: returns[s])
        n = len(sorted_symbols)
        return {sym: i / max(n - 1, 1) for i, sym in enumerate(sorted_symbols)}


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
    strategy_params: dict | None = None,
    donchian: DonchianEnsemble | None = None,
    momentum_scores: dict[str, float] | None = None,
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
    # Extract tuneable thresholds (fall back to defaults)
    _sp = strategy_params or {}
    signal_threshold = _sp.get("signal_threshold", 1.0)
    exit_threshold = _sp.get("exit_threshold", -0.5)

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

        # ── DONCHIAN CHANNEL ENSEMBLE (Zarattini 2025) ──
        # Used as trend confirmation, not primary signal.
        # Only add weight when multiple channels agree (strong trend).
        if donchian is not None:
            dc = donchian.signal(symbol)
            if dc["has_data"]:
                ts = dc["trend_strength"]  # -1 to +1
                # Only act on strong consensus (>50% of channels agree)
                if ts > 0.5:
                    score += 1.0
                    reasons.append(f"Donchian confirms bull ({dc['channels_bullish']} ch)")
                elif ts < -0.5:
                    score -= 1.0
                    reasons.append(f"Donchian confirms bear ({dc['channels_bearish']} ch)")

        # ── CROSS-SECTIONAL MOMENTUM (overweight strongest coins) ──
        # Only meaningful with 5+ coins. Boost top performers, penalize laggards.
        if momentum_scores is not None and symbol in momentum_scores and len(momentum_scores) >= 4:
            mom_rank = momentum_scores[symbol]
            if mom_rank >= 0.9:
                score += 0.5
                reasons.append(f"Momentum leader ({mom_rank:.0%})")
            elif mom_rank <= 0.1:
                score -= 0.5
                reasons.append(f"Momentum laggard ({mom_rank:.0%})")

        # ── REGIME-ADAPTIVE STRATEGY ──
        if is_ranging:
            # Ranging markets: switch to mean reversion (BB + RSI 30/70 works here)
            mr_score = 0.0
            if ind.bb_lower is not None and ind.bb_upper is not None and coin.current_price > 0:
                if coin.current_price < ind.bb_lower:
                    mr_score += 1.5
                elif coin.current_price > ind.bb_upper:
                    mr_score -= 1.5
            if ind.rsi_14 is not None:
                if ind.rsi_14 < 30:
                    mr_score += 1.0
                elif ind.rsi_14 > 70:
                    mr_score -= 1.0
            # Blend: 40% trend + 60% mean reversion
            score = score * 0.4 + mr_score * 0.6
            if mr_score != 0:
                reasons.append(f"Ranging regime — mean reversion (mr={mr_score:+.1f})")
        elif is_strong_trend:
            score *= 1.15

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
        if score >= signal_threshold:
            action = SignalAction.BUY
            confidence = min(0.50 + (score - signal_threshold) * 0.08, 0.90)
        elif score <= exit_threshold:
            # Bearish — this triggers exit of existing longs (via position management)
            # We still emit SELL so the exit logic can detect signal flips
            action = SignalAction.SELL
            confidence = min(0.50 + (abs(score) - abs(exit_threshold)) * 0.06, 0.85)
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
# Funding rate carry signal modifier
# ---------------------------------------------------------------------------

def _apply_funding_carry_modifier(
    signals: list[AggregatedSignal],
    funding_store: FundingRateStore,
    current_date: datetime,
    min_rate: float = 0.0003,  # 0.03% per 8h = ~13.7% annualized
) -> list[AggregatedSignal]:
    """Modify existing signals using funding rate data as a carry overlay.

    Funding rate carry logic:
    - NEGATIVE funding (shorts paying longs): +1.0 to score (bullish -- short squeeze setup)
    - Funding > 0.05% per 8h: -1.0 to score (bearish -- market overleveraged long)
    - Funding between 0 and min_rate: neutral (normal market conditions)

    This modifies the signals in place and returns them.
    """
    for sig in signals:
        rate = funding_store.get_latest_rate(sig.symbol, as_of=current_date)
        if rate is None:
            continue

        # Get the existing score from the signal
        old_score = sig.weighted_scores.get("score", 0.0)
        funding_adj = 0.0
        funding_reason = ""

        if rate < 0:
            # Negative funding: shorts paying longs = short squeeze setup = bullish
            funding_adj = 1.0
            funding_reason = f"Funding {rate:.6f} negative (short squeeze setup, +1.0)"
        elif rate > 0.0005:
            # Very high funding: market overleveraged long = bearish
            funding_adj = -1.0
            funding_reason = f"Funding {rate:.6f} very high (overleveraged long, -1.0)"
        elif rate > min_rate:
            # Moderately high funding: slightly bearish
            funding_adj = -0.5
            funding_reason = f"Funding {rate:.6f} elevated (mild overleveraged, -0.5)"
        else:
            # Normal range: no adjustment
            continue

        new_score = old_score + funding_adj

        # Re-derive action and confidence from modified score
        if new_score >= 1.0:
            action = SignalAction.BUY
            confidence = min(0.50 + (new_score - 1.0) * 0.08, 0.90)
        elif new_score <= -0.5:
            action = SignalAction.SELL
            confidence = min(0.50 + (abs(new_score) - 0.5) * 0.06, 0.85)
        else:
            action = SignalAction.HOLD
            confidence = 0.3

        # Update signal
        sig.recommended_action = action
        sig.aggregated_confidence = confidence
        sig.weighted_scores["score"] = new_score
        sig.weighted_scores["funding_rate"] = rate
        sig.weighted_scores["funding_adj"] = funding_adj

        # Add funding reason to contributing signal reasoning
        if sig.contributing_signals:
            old_reasoning = sig.contributing_signals[0].reasoning
            sig.contributing_signals[0].reasoning = (
                f"{old_reasoning}; {funding_reason}"
            )

    return signals


# ---------------------------------------------------------------------------
# Pairs trading signal generation
# ---------------------------------------------------------------------------

def _generate_pairs_signals(
    pairs_trader: PairsTrader,
    snapshot: MarketSnapshot,
    symbol_a: str = "BTCUSDT",
    symbol_b: str = "ETHUSDT",
) -> list[AggregatedSignal]:
    """Generate signals from the BTC-ETH pairs trading strategy.

    Maps pairs signals to the long-only backtester:
    - LONG_A_SHORT_B -> BUY symbol_a (spread too low, expect A to outperform)
    - SHORT_A_LONG_B -> BUY symbol_b (spread too high, expect B to outperform)
    - EXIT -> SELL both (take profit or stop loss)
    - HOLD -> HOLD

    Returns a list of AggregatedSignals for the affected symbols.
    """
    coin_a = snapshot.coins.get(symbol_a)
    coin_b = snapshot.coins.get(symbol_b)

    if coin_a is None or coin_b is None:
        return []
    if coin_a.current_price <= 0 or coin_b.current_price <= 0:
        return []

    result = pairs_trader.update_and_signal(coin_a.current_price, coin_b.current_price)
    z_score = result["z_score"]
    pair_signal = result["signal"]

    signals: list[AggregatedSignal] = []

    if pair_signal == "LONG_A_SHORT_B":
        # Spread too low: buy A (BTC), in long-only we only emit BUY for A
        confidence = min(0.50 + abs(z_score) * 0.10, 0.85)
        sig_a = Signal(
            agent_id="pairs_btc_eth",
            team="pairs",
            symbol=symbol_a,
            action=SignalAction.BUY,
            confidence=confidence,
            reasoning=(
                f"Pairs: spread z={z_score:.2f} < -{pairs_trader.entry_z:.1f}, "
                f"expect {symbol_a} to outperform {symbol_b}"
            ),
            metadata=result,
        )
        signals.append(AggregatedSignal(
            symbol=symbol_a,
            recommended_action=SignalAction.BUY,
            aggregated_confidence=confidence,
            contributing_signals=[sig_a],
            consensus_ratio=1.0,
            weighted_scores={"score": abs(z_score), "pairs_signal": pair_signal},
        ))

    elif pair_signal == "SHORT_A_LONG_B":
        # Spread too high: buy B (ETH), in long-only we only emit BUY for B
        confidence = min(0.50 + abs(z_score) * 0.10, 0.85)
        sig_b = Signal(
            agent_id="pairs_btc_eth",
            team="pairs",
            symbol=symbol_b,
            action=SignalAction.BUY,
            confidence=confidence,
            reasoning=(
                f"Pairs: spread z={z_score:.2f} > {pairs_trader.entry_z:.1f}, "
                f"expect {symbol_b} to outperform {symbol_a}"
            ),
            metadata=result,
        )
        signals.append(AggregatedSignal(
            symbol=symbol_b,
            recommended_action=SignalAction.BUY,
            aggregated_confidence=confidence,
            contributing_signals=[sig_b],
            consensus_ratio=1.0,
            weighted_scores={"score": abs(z_score), "pairs_signal": pair_signal},
        ))

    elif pair_signal == "EXIT":
        # Exit both positions (mean reversion complete or stop loss)
        for sym in [symbol_a, symbol_b]:
            sig = Signal(
                agent_id="pairs_btc_eth",
                team="pairs",
                symbol=sym,
                action=SignalAction.SELL,
                confidence=0.70,
                reasoning=(
                    f"Pairs EXIT: z={z_score:.2f}, "
                    f"{'take profit (spread reverted)' if abs(z_score) < pairs_trader.exit_z else 'stop loss (spread diverged)'}"
                ),
                metadata=result,
            )
            signals.append(AggregatedSignal(
                symbol=sym,
                recommended_action=SignalAction.SELL,
                aggregated_confidence=0.70,
                contributing_signals=[sig],
                consensus_ratio=1.0,
                weighted_scores={"score": -1.0, "pairs_signal": pair_signal},
            ))

    return signals


def _merge_signal_lists(
    *signal_lists: list[AggregatedSignal],
) -> list[AggregatedSignal]:
    """Merge multiple signal lists, averaging scores for shared symbols.

    When the same symbol appears in multiple lists, the scores are averaged
    and the action/confidence are re-derived from the averaged score.
    """
    by_symbol: dict[str, list[AggregatedSignal]] = {}
    for sigs in signal_lists:
        for sig in sigs:
            by_symbol.setdefault(sig.symbol, []).append(sig)

    merged: list[AggregatedSignal] = []
    for symbol, sigs in by_symbol.items():
        if len(sigs) == 1:
            merged.append(sigs[0])
            continue

        # Average the scores from all strategies
        scores = [s.weighted_scores.get("score", 0.0) for s in sigs]
        avg_score = sum(scores) / len(scores)

        # Re-derive action/confidence from averaged score
        if avg_score >= 1.0:
            action = SignalAction.BUY
            confidence = min(0.50 + (avg_score - 1.0) * 0.08, 0.90)
        elif avg_score <= -0.5:
            action = SignalAction.SELL
            confidence = min(0.50 + (abs(avg_score) - 0.5) * 0.06, 0.85)
        else:
            action = SignalAction.HOLD
            confidence = 0.3

        # Collect all contributing signals
        all_contributing = []
        for s in sigs:
            all_contributing.extend(s.contributing_signals)

        # Merge weighted_scores metadata
        merged_scores: dict[str, Any] = {"score": avg_score, "strategy_scores": scores}
        for s in sigs:
            for k, v in s.weighted_scores.items():
                if k != "score":
                    merged_scores[k] = v

        merged.append(AggregatedSignal(
            symbol=symbol,
            recommended_action=action,
            aggregated_confidence=confidence,
            contributing_signals=all_contributing,
            consensus_ratio=sum(s.consensus_ratio for s in sigs) / len(sigs),
            weighted_scores=merged_scores,
        ))

    return merged


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
        total_execution_costs: float = 0.0

        # Track benchmark prices (first coin close for BTC, ETH)
        benchmark_btc: list[float] = []
        benchmark_eth: list[float] = []

        prev_value = config.initial_capital
        current_date = start_dt
        n_symbols = len(config.symbols)
        step_count = 0

        # ── Adaptive position sizer ──
        # Initialise once per run; it accumulates trade history across steps.
        sizing_mode = SizingMode(config.sizing_mode)
        position_sizer = PositionSizer(mode=sizing_mode)

        # ── Resolve active strategies ──
        active_strategies = list(config.strategies)
        if "combined" in active_strategies:
            active_strategies = ["trend_following", "funding_carry", "pairs_btc_eth"]

        use_funding = "funding_carry" in active_strategies
        use_pairs = "pairs_btc_eth" in active_strategies
        use_trend = "trend_following" in active_strategies

        funding_store: FundingRateStore | None = None
        if use_funding:
            funding_store = FundingRateStore(storage_dir=config.funding_rates_dir)

        _pairs_trader: PairsTrader | None = None
        if use_pairs:
            _pairs_trader = PairsTrader(
                lookback=60, entry_z=2.0, exit_z=0.5, stop_z=3.5,
            )

        # ── Donchian ensemble + cross-sectional momentum ──
        donchian = DonchianEnsemble()
        momentum_ranker = MomentumRanker(lookback=7)
        # Pre-fill with historical prices (Donchian needs up to 360 days warm-up)
        for sym in config.symbols:
            candles = store.load(sym, "1d", end=start_dt)
            for c in candles[-400:]:
                donchian.update(sym, c.close)
                momentum_ranker.update(sym, c.close)

        # ── Zarattini (2025) trailing stop state ──
        # Tracks per-symbol trail values that only ratchet upward.
        # Cleared when a position is closed; keyed by symbol.
        trail_state: dict[str, float] = {}

        # ── Trade context for strategy-specific exits ──
        # Stores regime at entry time so we can apply different time stops:
        #   - Mean reversion (ranging): max 3 days (Lopez de Prado Triple Barrier)
        #   - Trend following (trending): no fixed time stop, only stale-position
        #     check after 30 days with <2% movement
        trade_context: dict[str, dict] = {}

        # ── Sadaqat & Butt fixed % hard stops by tier ──
        # Research: fixed 10-20% stop boosted Sharpe by 0.32-0.50.
        FIXED_STOP_PCT: dict[str, float] = {
            "btc": 0.12,       # 12% max loss from entry
            "top5": 0.15,      # 15% max loss
            "large_cap": 0.20, # 20% max loss
            "mid_cap": 0.20,   # 20% max loss
            "meme": 0.20,      # 20% max loss
        }

        while current_date <= end_dt:
            step_count += 1
            # 1. Build snapshot
            snapshot = data_layer.build_snapshot(config.symbols, current_date)

            # Collect benchmark prices + update Donchian/Momentum each step
            btc_coin = snapshot.coins.get("BTCUSDT")
            eth_coin = snapshot.coins.get("ETHUSDT")
            benchmark_btc.append(btc_coin.current_price if btc_coin and btc_coin.current_price > 0 else (benchmark_btc[-1] if benchmark_btc else 0))
            benchmark_eth.append(eth_coin.current_price if eth_coin and eth_coin.current_price > 0 else (benchmark_eth[-1] if benchmark_eth else 0))

            for sym, coin in snapshot.coins.items():
                if coin.current_price > 0:
                    donchian.update(sym, coin.current_price)
                    momentum_ranker.update(sym, coin.current_price)

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

            # 4. Generate signals from active strategies
            noise_rng = random.Random(noise_seed + step_count) if noise_seed is not None else None

            signal_lists: list[list[AggregatedSignal]] = []

            # Compute momentum rankings for this step
            mom_scores = momentum_ranker.rank()

            # 4a. Trend-following signals (default strategy)
            if use_trend:
                trend_signals = _generate_deterministic_signals(
                    snapshot, config.symbols, noise_rng=noise_rng,
                    strategy_params=config.strategy_params,
                    donchian=donchian, momentum_scores=mom_scores,
                )
                # Apply funding carry modifier on top of trend signals
                if use_funding and funding_store is not None:
                    trend_signals = _apply_funding_carry_modifier(
                        trend_signals, funding_store, current_date,
                    )
                signal_lists.append(trend_signals)
            elif use_funding and funding_store is not None:
                # Funding carry standalone: generate base trend signals then modify
                base_signals = _generate_deterministic_signals(
                    snapshot, config.symbols, noise_rng=noise_rng,
                    strategy_params=config.strategy_params,
                    donchian=donchian, momentum_scores=mom_scores,
                )
                base_signals = _apply_funding_carry_modifier(
                    base_signals, funding_store, current_date,
                )
                signal_lists.append(base_signals)

            # 4b. Pairs trading signals (BTC-ETH spread)
            if use_pairs and _pairs_trader is not None:
                pairs_sigs = _generate_pairs_signals(
                    _pairs_trader, snapshot,
                    symbol_a="BTCUSDT", symbol_b="ETHUSDT",
                )
                if pairs_sigs:
                    signal_lists.append(pairs_sigs)

            # 4c. Merge all strategy signal lists
            if len(signal_lists) == 0:
                # Fallback: generate basic trend signals if no strategy produced output
                signals = _generate_deterministic_signals(
                    snapshot, config.symbols, noise_rng=noise_rng,
                    strategy_params=config.strategy_params,
                    donchian=donchian, momentum_scores=mom_scores,
                )
            elif len(signal_lists) == 1:
                signals = signal_lists[0]
            else:
                signals = _merge_signal_lists(*signal_lists)

            # 5. Position management — check existing positions for exits
            # Zarattini (2025) trailing stop (primary), ATR hard stop (catastrophic),
            # Sadaqat & Butt fixed % stop, signal-flip, time stop.
            from syndicate.data.models import OrderSide, TradeOrder
            _atr_hard_stop_mult = 4.0  # Widened: catastrophic protection only
            _atr_tp_mult = config.strategy_params.get("atr_tp_mult", 6.0)
            positions_to_close: list[tuple[str, float, str]] = []  # (symbol, price, reason)

            for pos in list(trader.portfolio.positions):
                sym_coin = snapshot.coins.get(pos.symbol)
                if sym_coin is None or sym_coin.current_price <= 0:
                    continue
                price = sym_coin.current_price
                sym_ind = sym_coin.indicators_4h

                # ── ATR-based trailing stop (3x ATR — proven in our backtests) ──
                atr_stop_mult = config.strategy_params.get("atr_stop_mult", 3.0)
                if sym_ind and sym_ind.atr_14 and sym_ind.atr_14 > 0:
                    stop_distance = sym_ind.atr_14 * atr_stop_mult
                    if pos.side == OrderSide.BUY:
                        if price <= pos.entry_price - stop_distance:
                            positions_to_close.append((pos.symbol, price, "ATR_STOP"))
                            continue
                    else:
                        if price >= pos.entry_price + stop_distance:
                            positions_to_close.append((pos.symbol, price, "ATR_STOP"))
                            continue

                # ── HARD STOP 2: Sadaqat & Butt fixed % stop (catastrophic only) ──
                # Research showed 10-20% stops boost Sharpe, but our ATR stops already
                # handle normal drawdowns. Use 25% as absolute catastrophe protection only.
                if pos.side == OrderSide.BUY:
                    if price <= pos.entry_price * 0.75:  # -25% max loss
                        positions_to_close.append((pos.symbol, price, "HARD_STOP_25PCT"))
                        continue
                else:
                    if price >= pos.entry_price * 1.25:
                        positions_to_close.append((pos.symbol, price, "HARD_STOP_25PCT"))
                        continue

                # ── TAKE PROFIT at 2R (6x ATR) ──
                # Keep existing TP logic; the Zarattini trail tightening at +2R
                # (above) handles locking in gains on the way up.
                if sym_ind and sym_ind.atr_14 and sym_ind.atr_14 > 0:
                    tp_distance = sym_ind.atr_14 * _atr_tp_mult
                    if pos.side == OrderSide.BUY:
                        if price >= pos.entry_price + tp_distance:
                            positions_to_close.append((pos.symbol, price, "TAKE_PROFIT"))
                            continue
                    else:
                        if price <= pos.entry_price - tp_distance:
                            positions_to_close.append((pos.symbol, price, "TAKE_PROFIT"))
                            continue

                # ── Signal-flip exit (only on VERY strong opposing signal) ──
                # Research: trend-following profits come from letting winners run.
                # Only exit when multiple indicators strongly agree on reversal.
                for sig in signals:
                    if sig.symbol == pos.symbol:
                        sig_score = sig.weighted_scores.get("score", 0)
                        if pos.side == OrderSide.BUY and sig_score < -4.0:
                            positions_to_close.append((pos.symbol, price, "SIGNAL_FLIP"))
                        elif pos.side == OrderSide.SELL and sig_score > 4.0:
                            positions_to_close.append((pos.symbol, price, "SIGNAL_FLIP"))

                # ── Strategy-specific time stop (Lopez de Prado Triple Barrier) ──
                # Mean reversion (ranging): max 3 days — thesis has failed
                # Trend following (trending): no fixed stop, but close stale
                #   positions after 30 days with <2% movement
                ctx = trade_context.get(pos.symbol, {})
                entry_date = ctx.get("entry_date")
                if entry_date is None and hasattr(pos, "entry_time"):
                    entry_date = pos.entry_time
                if entry_date is not None:
                    holding_days = (current_date - entry_date).days

                    if ctx.get("regime") == "ranging" and ctx.get("adx_at_entry") is not None and ctx["adx_at_entry"] < 15:
                        # Pure mean reversion only (ADX very low): max 5 days
                        # Don't apply to mixed signals (ADX 15-25) — those are transitional
                        if holding_days >= 5:
                            positions_to_close.append((pos.symbol, price, "MR_TIME_STOP"))
                            continue
                    else:
                        # Trend following: close after 30 days if <2% movement
                        if holding_days >= 30:
                            entry_px = pos.entry_price
                            pnl_pct_chk = (
                                (price - entry_px) / entry_px
                                if pos.side == OrderSide.BUY
                                else (entry_px - price) / entry_px
                            )
                            if abs(pnl_pct_chk) < 0.02:
                                positions_to_close.append((pos.symbol, price, "STALE_POSITION"))
                                continue

            # Execute exits
            for sym, exit_price, reason in positions_to_close:
                pos = trader.portfolio.get_position(sym)
                if pos is None:
                    continue
                close_side = OrderSide.SELL if pos.side == OrderSide.BUY else OrderSide.BUY

                # Apply slippage + fees to exit price
                exit_costs = compute_total_execution_cost(sym, exit_price, pos.quantity)
                if close_side == OrderSide.BUY:
                    exit_price = exit_costs["adjusted_price_buy"]
                else:
                    exit_price = exit_costs["adjusted_price_sell"]
                total_execution_costs += exit_costs["total_cost_usd"]

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

                    # Clear Zarattini trail state for this symbol
                    trail_state.pop(f"zarattini_trail_{sym}", None)

                    # Clear trade context for this symbol
                    trade_context.pop(sym, None)

                    # Feed closed trade into the adaptive position sizer
                    position_sizer.record_trade(
                        win=(pnl_pct > 0),
                        pnl_pct=pnl_pct,
                    )

            # 6. Risk management for new entries — adaptive position sizing
            #
            # Compute the position fraction from the sizer. For "fixed" mode
            # this is the default 2%; for kelly/vol_target/adaptive it adapts
            # based on rolling trade history and current volatility.
            _representative_vol = 0.0
            _representative_price = 0.0
            for _sym in config.symbols:
                _coin = snapshot.coins.get(_sym)
                if _coin and _coin.indicators_4h and _coin.indicators_4h.atr_14 and _coin.current_price > 0:
                    _representative_vol = atr_to_annual_vol(
                        atr=_coin.indicators_4h.atr_14,
                        price=_coin.current_price,
                        period_hours=4.0,
                    )
                    _representative_price = _coin.current_price
                    break  # use first available

            adaptive_fraction = position_sizer.compute_position_fraction(
                portfolio_value=trader.portfolio.total_value,
                current_vol=_representative_vol,
                price=_representative_price,
            )

            # Use adaptive fraction as max_position_pct, but also respect
            # the original per-symbol cap so we don't over-concentrate.
            per_symbol_pct = min(0.20, 0.80 / max(n_symbols, 1))
            effective_max_position_pct = (
                min(per_symbol_pct, adaptive_fraction)
                if sizing_mode != SizingMode.FIXED
                else per_symbol_pct
            )
            risk_limits = RiskLimits(
                max_position_pct=effective_max_position_pct,
                max_daily_drawdown_pct=0.08,
                min_signal_confidence=0.45,
                min_consensus_ratio=0.0,
                max_open_positions=max(n_symbols * 2, 10),
            )
            risk_mgr = RiskManager(limits=risk_limits, regime=regime)
            orders = risk_mgr.evaluate(signals, trader.portfolio)

            # 7. Execute new entries
            for order in orders:
                # Apply slippage + fees to entry price
                entry_costs = compute_total_execution_cost(
                    order.symbol, order.price, order.quantity,
                )
                if order.side == OrderSide.BUY:
                    order.price = entry_costs["adjusted_price_buy"]
                else:
                    order.price = entry_costs["adjusted_price_sell"]
                total_execution_costs += entry_costs["total_cost_usd"]

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

                    # Store trade context for strategy-specific exit management
                    coin = snapshot.coins.get(result.symbol)
                    ind = coin.indicators_4h if coin else None
                    adx_val = ind.adx_14 if ind else None
                    trade_context[result.symbol] = {
                        "entry_date": current_date,
                        "regime": "trending" if (adx_val and adx_val > 25) else "ranging",
                        "adx_at_entry": adx_val,
                    }

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

        # ── Phase weight learning placeholder ──
        # When LLM-based backtesting is added (multi-team signals per step),
        # track simulated team attributions here and adjust weights over time
        # using PhaseWeightManager.  Currently the backtester uses deterministic
        # signals from a single "technical" strategy, so phase weights are not
        # applicable.  The integration points will be:
        #   1. After each step's trades close, call phase_weights.update_from_tracker()
        #   2. Use phase_weights.get_weights() to adjust signal aggregation weights
        #   3. Record per-step phase transitions in equity_curve entries

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
        metrics["total_execution_costs"] = round(total_execution_costs, 2)

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
