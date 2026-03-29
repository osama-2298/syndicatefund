"""
Data source alpha evaluator — tests predictive power of each indicator.

Uses historical data to statistically evaluate which data sources
actually have alpha and which are noise.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd

from hivemind.research.data.query import get_candles, get_returns, get_fear_greed, get_available_symbols


def _compute_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Compute RSI indicator."""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def evaluate_rsi(symbol: str = "BTCUSDT", timeframe: str = "1d", forward_periods: int = 1) -> dict:
    """Test if RSI extremes predict reversals."""
    df = get_candles(symbol, timeframe)
    if len(df) < 50:
        return {"error": "insufficient_data", "sample_size": len(df)}

    rsi = _compute_rsi(df["close"])
    fwd_return = df["close"].pct_change(forward_periods).shift(-forward_periods)

    # Remove NaN
    mask = rsi.notna() & fwd_return.notna()
    rsi_clean = rsi[mask].values
    fwd_clean = fwd_return[mask].values

    if len(rsi_clean) < 30:
        return {"error": "insufficient_data", "sample_size": len(rsi_clean)}

    # Correlation
    corr = float(np.corrcoef(rsi_clean, fwd_clean)[0, 1])

    # Oversold (RSI < 30) -> buy signal
    oversold_mask = rsi_clean < 30
    oversold_returns = fwd_clean[oversold_mask] if oversold_mask.any() else np.array([])

    # Overbought (RSI > 70) -> sell signal
    overbought_mask = rsi_clean > 70
    overbought_returns = fwd_clean[overbought_mask] if overbought_mask.any() else np.array([])

    # Neutral
    neutral_mask = ~oversold_mask & ~overbought_mask
    neutral_returns = fwd_clean[neutral_mask]

    return {
        "source": "RSI(14)",
        "symbol": symbol,
        "timeframe": timeframe,
        "forward_periods": forward_periods,
        "correlation_with_forward_return": corr,
        "oversold_signals": int(oversold_mask.sum()),
        "oversold_avg_return": float(np.mean(oversold_returns)) if len(oversold_returns) > 0 else None,
        "oversold_hit_rate": float(np.mean(oversold_returns > 0)) if len(oversold_returns) > 0 else None,
        "overbought_signals": int(overbought_mask.sum()),
        "overbought_avg_return": float(np.mean(overbought_returns)) if len(overbought_returns) > 0 else None,
        "overbought_hit_rate": float(np.mean(overbought_returns < 0)) if len(overbought_returns) > 0 else None,
        "neutral_avg_return": float(np.mean(neutral_returns)) if len(neutral_returns) > 0 else None,
        "sample_size": len(rsi_clean),
        "verdict": "predictive" if abs(corr) > 0.05 else "noise",
    }


def evaluate_ma_crossover(symbol: str = "BTCUSDT", timeframe: str = "1d", forward_periods: int = 5) -> dict:
    """Test if SMA20 > SMA50 predicts positive returns."""
    df = get_candles(symbol, timeframe)
    if len(df) < 60:
        return {"error": "insufficient_data"}

    sma20 = df["close"].rolling(20).mean()
    sma50 = df["close"].rolling(50).mean()
    fwd_return = df["close"].pct_change(forward_periods).shift(-forward_periods)

    mask = sma20.notna() & sma50.notna() & fwd_return.notna()

    bullish = (sma20 > sma50) & mask
    bearish = (sma20 <= sma50) & mask

    bull_returns = fwd_return[bullish].values
    bear_returns = fwd_return[bearish].values

    return {
        "source": "SMA20/SMA50 Crossover",
        "symbol": symbol,
        "bullish_periods": int(bullish.sum()),
        "bullish_avg_return": float(np.mean(bull_returns)) if len(bull_returns) > 0 else None,
        "bullish_hit_rate": float(np.mean(bull_returns > 0)) if len(bull_returns) > 0 else None,
        "bearish_periods": int(bearish.sum()),
        "bearish_avg_return": float(np.mean(bear_returns)) if len(bear_returns) > 0 else None,
        "bearish_hit_rate": float(np.mean(bear_returns < 0)) if len(bear_returns) > 0 else None,
        "spread": float(np.mean(bull_returns) - np.mean(bear_returns)) if len(bull_returns) > 0 and len(bear_returns) > 0 else None,
        "sample_size": int(mask.sum()),
        "verdict": "predictive" if len(bull_returns) > 0 and len(bear_returns) > 0 and np.mean(bull_returns) > np.mean(bear_returns) else "weak",
    }


def evaluate_volume(symbol: str = "BTCUSDT", timeframe: str = "1d", forward_periods: int = 1) -> dict:
    """Test if high volume predicts direction."""
    df = get_candles(symbol, timeframe)
    if len(df) < 30:
        return {"error": "insufficient_data"}

    vol_ratio = df["volume"] / df["volume"].rolling(20).mean()
    fwd_return = df["close"].pct_change(forward_periods).shift(-forward_periods)

    mask = vol_ratio.notna() & fwd_return.notna()

    high_vol = (vol_ratio > 1.5) & mask
    normal_vol = (vol_ratio <= 1.5) & mask

    high_returns = fwd_return[high_vol].values
    normal_returns = fwd_return[normal_vol].values

    corr = float(np.corrcoef(vol_ratio[mask].values, fwd_return[mask].values)[0, 1]) if mask.sum() > 10 else 0

    return {
        "source": "Volume Ratio",
        "symbol": symbol,
        "correlation": corr,
        "high_volume_periods": int(high_vol.sum()),
        "high_vol_avg_return": float(np.mean(high_returns)) if len(high_returns) > 0 else None,
        "normal_vol_avg_return": float(np.mean(normal_returns)) if len(normal_returns) > 0 else None,
        "sample_size": int(mask.sum()),
        "verdict": "predictive" if abs(corr) > 0.05 else "noise",
    }


def evaluate_fear_greed(forward_periods: int = 1) -> dict:
    """Test if Fear & Greed Index predicts BTC returns."""
    fg = get_fear_greed()
    btc = get_candles("BTCUSDT", "1d")

    if fg.empty or btc.empty:
        return {"error": "insufficient_data"}

    # Align by date
    fg["date"] = pd.to_datetime(fg["date"]).dt.date
    btc["date"] = pd.to_datetime(btc["timestamp"]).dt.date
    btc["fwd_return"] = btc["close"].pct_change(forward_periods).shift(-forward_periods)

    merged = pd.merge(fg, btc[["date", "fwd_return"]], on="date", how="inner")
    merged = merged.dropna(subset=["value", "fwd_return"])

    if len(merged) < 30:
        return {"error": "insufficient_data", "sample_size": len(merged)}

    corr = float(np.corrcoef(merged["value"].values, merged["fwd_return"].values)[0, 1])

    # Extreme fear (< 20) -> buy signal?
    fear = merged[merged["value"] < 20]
    greed = merged[merged["value"] > 80]
    neutral = merged[(merged["value"] >= 20) & (merged["value"] <= 80)]

    return {
        "source": "Fear & Greed Index",
        "correlation_with_forward_return": corr,
        "extreme_fear_count": len(fear),
        "extreme_fear_avg_return": float(fear["fwd_return"].mean()) if len(fear) > 0 else None,
        "extreme_fear_hit_rate": float((fear["fwd_return"] > 0).mean()) if len(fear) > 0 else None,
        "extreme_greed_count": len(greed),
        "extreme_greed_avg_return": float(greed["fwd_return"].mean()) if len(greed) > 0 else None,
        "extreme_greed_hit_rate": float((greed["fwd_return"] < 0).mean()) if len(greed) > 0 else None,
        "neutral_avg_return": float(neutral["fwd_return"].mean()) if len(neutral) > 0 else None,
        "sample_size": len(merged),
        "verdict": "predictive" if abs(corr) > 0.05 else "noise",
    }


def evaluate_momentum(symbol: str = "BTCUSDT", timeframe: str = "1d", lookback: int = 7, forward: int = 7) -> dict:
    """Test if past N-day returns predict next N-day returns (momentum vs mean reversion)."""
    df = get_candles(symbol, timeframe)
    if len(df) < lookback + forward + 10:
        return {"error": "insufficient_data"}

    past_return = df["close"].pct_change(lookback)
    fwd_return = df["close"].pct_change(forward).shift(-forward)

    mask = past_return.notna() & fwd_return.notna()

    corr = float(np.corrcoef(past_return[mask].values, fwd_return[mask].values)[0, 1])

    # Is it momentum (positive correlation) or mean reversion (negative)?
    pattern = "momentum" if corr > 0.02 else "mean_reversion" if corr < -0.02 else "random"

    return {
        "source": f"Momentum ({lookback}d -> {forward}d)",
        "symbol": symbol,
        "correlation": corr,
        "pattern": pattern,
        "sample_size": int(mask.sum()),
        "verdict": "predictive" if abs(corr) > 0.05 else "noise",
    }


def evaluate_mean_reversion(symbol: str = "BTCUSDT", timeframe: str = "1d", forward_periods: int = 5) -> dict:
    """Test if deviation from SMA20 predicts reversal."""
    df = get_candles(symbol, timeframe)
    if len(df) < 30:
        return {"error": "insufficient_data"}

    sma20 = df["close"].rolling(20).mean()
    deviation = (df["close"] - sma20) / sma20  # % deviation from SMA
    fwd_return = df["close"].pct_change(forward_periods).shift(-forward_periods)

    mask = deviation.notna() & fwd_return.notna()

    corr = float(np.corrcoef(deviation[mask].values, fwd_return[mask].values)[0, 1])

    # Mean reversion = negative correlation (high deviation -> negative future return)
    return {
        "source": "Mean Reversion (SMA20 deviation)",
        "symbol": symbol,
        "correlation": corr,
        "is_mean_reverting": corr < -0.03,
        "sample_size": int(mask.sum()),
        "verdict": "predictive" if abs(corr) > 0.05 else "noise",
    }


def full_report(symbol: str = "BTCUSDT") -> dict[str, Any]:
    """Run all data source evaluations and produce a ranked report."""
    evaluations = [
        evaluate_rsi(symbol),
        evaluate_ma_crossover(symbol),
        evaluate_volume(symbol),
        evaluate_fear_greed(),
        evaluate_momentum(symbol),
        evaluate_mean_reversion(symbol),
    ]

    # Filter out errors
    valid = [e for e in evaluations if "error" not in e]

    # Rank by absolute correlation with forward returns
    for e in valid:
        corr_key = next((k for k in e if "correlation" in k.lower()), None)
        e["_abs_corr"] = abs(e.get(corr_key, 0)) if corr_key else 0

    ranked = sorted(valid, key=lambda x: x["_abs_corr"], reverse=True)

    # Clean up
    for e in ranked:
        del e["_abs_corr"]

    predictive = [e for e in ranked if e.get("verdict") == "predictive"]
    noise = [e for e in ranked if e.get("verdict") != "predictive"]

    return {
        "symbol_tested": symbol,
        "total_sources_evaluated": len(evaluations),
        "predictive_sources": len(predictive),
        "noise_sources": len(noise),
        "ranked_evaluations": ranked,
        "predictive": [e["source"] for e in predictive],
        "noise": [e["source"] for e in noise],
        "errors": [e for e in evaluations if "error" in e],
    }
