"""
Technical indicator calculations.

Uses the `ta` library for standard indicators computed over pandas DataFrames.
Takes raw Candle data, returns a TechnicalIndicators model ready for LLM consumption.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import ta

from hivemind.data.models import Candle, TechnicalIndicators


def candles_to_dataframe(candles: list[Candle]) -> pd.DataFrame:
    """Convert a list of Candle models to a pandas DataFrame."""
    if not candles:
        raise ValueError("Cannot compute indicators on empty candle list")

    df = pd.DataFrame([c.model_dump() for c in candles])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def compute_indicators(candles: list[Candle], symbol: str) -> TechnicalIndicators:
    """
    Compute all technical indicators from raw candle data.

    Requires at least 200 candles for SMA(200) to be meaningful.
    Works with fewer, but some indicators will be None.

    Args:
        candles: List of OHLCV candles, oldest first.
        symbol: Trading pair (e.g. 'BTCUSDT').

    Returns:
        TechnicalIndicators with all computable fields populated.
    """
    df = candles_to_dataframe(candles)
    n = len(df)

    indicators = TechnicalIndicators(symbol=symbol)

    if n < 2:
        return indicators

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # ── Trend: Moving Averages ──
    if n >= 20:
        indicators.sma_20 = _last_valid(ta.trend.sma_indicator(close, window=20))
    if n >= 50:
        indicators.sma_50 = _last_valid(ta.trend.sma_indicator(close, window=50))
    if n >= 200:
        indicators.sma_200 = _last_valid(ta.trend.sma_indicator(close, window=200))

    if n >= 12:
        indicators.ema_12 = _last_valid(ta.trend.ema_indicator(close, window=12))
    if n >= 26:
        indicators.ema_26 = _last_valid(ta.trend.ema_indicator(close, window=26))

    # ── Momentum: RSI ──
    if n >= 15:  # RSI(14) needs at least 15 data points
        rsi_series = ta.momentum.rsi(close, window=14)
        indicators.rsi_14 = _last_valid(rsi_series)

    # ── Momentum: MACD ──
    if n >= 35:  # MACD(12,26,9) needs enough data
        macd = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
        indicators.macd_line = _last_valid(macd.macd())
        indicators.macd_signal = _last_valid(macd.macd_signal())
        indicators.macd_histogram = _last_valid(macd.macd_diff())

    # ── Volatility: Bollinger Bands ──
    if n >= 20:
        bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
        indicators.bb_upper = _last_valid(bb.bollinger_hband())
        indicators.bb_middle = _last_valid(bb.bollinger_mavg())
        indicators.bb_lower = _last_valid(bb.bollinger_lband())
        indicators.bb_width = _last_valid(bb.bollinger_wband())

    # ── Volatility: ATR ──
    if n >= 15:
        atr_series = ta.volatility.average_true_range(high, low, close, window=14)
        indicators.atr_14 = _last_valid(atr_series)

    # ── Volume ──
    if n >= 20:
        vol_sma = ta.trend.sma_indicator(volume, window=20)
        indicators.volume_sma_20 = _last_valid(vol_sma)
        indicators.current_volume = float(volume.iloc[-1])

        avg_vol = indicators.volume_sma_20
        if avg_vol and avg_vol > 0:
            indicators.volume_ratio = indicators.current_volume / avg_vol

    return indicators


def format_price_history(candles: list[Candle], last_n: int = 30) -> str:
    """
    Format recent price history as a readable string for LLM consumption.

    Shows the last N candles with open/high/low/close/volume.
    """
    recent = candles[-last_n:] if len(candles) > last_n else candles

    lines = [f"Recent price history ({len(recent)} candles):"]
    lines.append(f"{'Timestamp':<22} {'Open':>12} {'High':>12} {'Low':>12} {'Close':>12} {'Volume':>14}")
    lines.append("-" * 90)

    for c in recent:
        ts = c.timestamp.strftime("%Y-%m-%d %H:%M")
        lines.append(
            f"{ts:<22} {c.open:>12,.2f} {c.high:>12,.2f} "
            f"{c.low:>12,.2f} {c.close:>12,.2f} {c.volume:>14,.0f}"
        )

    # Summary stats
    closes = [c.close for c in recent]
    first_close = closes[0]
    last_close = closes[-1]
    change_pct = ((last_close - first_close) / first_close) * 100

    lines.append(f"\nPeriod change: {change_pct:+.2f}%")
    lines.append(f"Period high: {max(c.high for c in recent):,.2f}")
    lines.append(f"Period low: {min(c.low for c in recent):,.2f}")
    lines.append(f"Current price: {last_close:,.2f}")

    return "\n".join(lines)


def _last_valid(series: pd.Series) -> float | None:
    """Get the last non-NaN value from a pandas Series, or None."""
    if series is None or series.empty:
        return None
    # Drop NaN and get last value
    valid = series.dropna()
    if valid.empty:
        return None
    val = float(valid.iloc[-1])
    if np.isnan(val) or np.isinf(val):
        return None
    return val
