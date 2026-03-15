"""
Stock screener — scores S&P 500 / universe stocks for selection.

Mirrors the crypto COO's coin scoring but adapted for equities.
"""

from __future__ import annotations

import math

import structlog

from stocks.data.models import StockScore

logger = structlog.get_logger()


def compute_stock_scores(all_stats: list[dict], max_candidates: int = 30) -> list[StockScore]:
    """
    Score each stock by opportunity.

    Inputs: list of dicts with keys: symbol, close, volume, price_change_pct, high, low
    Returns: top candidates sorted by composite score descending.
    """
    if not all_stats:
        return []

    max_vol = max((s.get("volume", 0) for s in all_stats), default=1)

    scored = []
    for stat in all_stats:
        symbol = stat.get("symbol", "")
        vol = stat.get("volume", 0)
        change = stat.get("price_change_pct", 0)
        high = stat.get("high", 0)
        low = stat.get("low", 0)
        close = stat.get("close", 0)

        if close <= 0 or vol <= 0:
            continue

        # Volume score (log-normalized)
        vol_score = min(1.0, math.log1p(vol) / math.log1p(max_vol)) if max_vol > 0 else 0

        # Volatility score (daily range %)
        daily_range_pct = ((high - low) / close) * 100 if close > 0 else 0

        # Stocks have lower volatility than crypto — adjusted thresholds
        if 1.5 <= daily_range_pct <= 4.0:
            vol_score_adj = 1.0
        elif 0.5 <= daily_range_pct < 1.5:
            vol_score_adj = daily_range_pct / 1.5
        elif 4.0 < daily_range_pct <= 8.0:
            vol_score_adj = max(0.3, 1.0 - (daily_range_pct - 4.0) / 8.0)
        elif daily_range_pct > 8.0:
            vol_score_adj = 0.2
        else:
            vol_score_adj = 0.1

        # Momentum score
        abs_change = abs(change)
        if abs_change > 5:
            momentum_strength = 1.0
        elif abs_change > 3:
            momentum_strength = 0.7
        elif abs_change > 1.5:
            momentum_strength = 0.4
        elif abs_change > 0.5:
            momentum_strength = 0.2
        else:
            momentum_strength = 0.05

        momentum = momentum_strength if change > 0 else -momentum_strength

        composite = (vol_score * 0.35) + (vol_score_adj * 0.35) + (abs(momentum) * 0.30)

        scored.append(
            StockScore(
                symbol=symbol,
                volume_score=round(vol_score, 3),
                volatility_score=round(vol_score_adj, 3),
                momentum_score=round(momentum, 3),
                composite_score=round(composite, 3),
            )
        )

    scored.sort(key=lambda x: x.composite_score, reverse=True)
    return scored[:max_candidates]
