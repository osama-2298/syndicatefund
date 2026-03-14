"""
Trade Parameter Calculator — ATR-based stop loss, R-multiple take profits, Chandelier trailing.

Every trade gets a full parameter set calculated BEFORE entry:
- Stop loss (ATR-based, adapts to each coin's volatility)
- Take profit targets (tiered: sell 33% at 1.5R, 33% at 2.5R, trail the rest)
- Trailing stop (Chandelier exit, activates after 1.5R profit)
- Time stop (max holding period)
- Risk amount (max $ at risk if stop is hit)

Asset tiers determine multipliers:
  BTC:       tight stops (2.0x ATR), wide trails, 15-25% max position
  Top 5:     moderate (2.5x ATR), 10-15% max position
  Large cap: wider (3.0x ATR), 5-10% max position
  Mid cap:   wide (3.5x ATR), 3-5% max position
  Meme:      very wide (4.5x ATR), 1-2% max position
"""

from __future__ import annotations

from hivemind.data.models import (
    AggregatedSignal,
    MarketRegime,
    OrderSide,
    PortfolioState,
    TradeOrder,
    TradeParameters,
)

# ─── Asset Tier Configuration ───

TIER_CONFIG = {
    "btc": {
        "stop_atr_mult": 2.0,
        "trail_atr_mult": 2.5,
        "tp1_r_mult": 1.5,
        "tp2_r_mult": 2.5,
        "risk_per_trade": 0.015,  # 1.5% of portfolio
        "max_position_pct": 0.20,
        "max_holding_hours": 360,  # 15 days
        "fallback_stop_pct": 0.065,  # 6.5%
    },
    "top5": {
        "stop_atr_mult": 2.5,
        "trail_atr_mult": 3.0,
        "tp1_r_mult": 1.5,
        "tp2_r_mult": 2.5,
        "risk_per_trade": 0.012,
        "max_position_pct": 0.12,
        "max_holding_hours": 240,  # 10 days
        "fallback_stop_pct": 0.10,
    },
    "large_cap": {
        "stop_atr_mult": 3.0,
        "trail_atr_mult": 3.5,
        "tp1_r_mult": 1.5,
        "tp2_r_mult": 2.5,
        "risk_per_trade": 0.01,
        "max_position_pct": 0.08,
        "max_holding_hours": 168,  # 7 days
        "fallback_stop_pct": 0.12,
    },
    "mid_cap": {
        "stop_atr_mult": 3.5,
        "trail_atr_mult": 4.0,
        "tp1_r_mult": 1.5,
        "tp2_r_mult": 3.0,
        "risk_per_trade": 0.0075,
        "max_position_pct": 0.05,
        "max_holding_hours": 120,  # 5 days
        "fallback_stop_pct": 0.20,
    },
    "meme": {
        "stop_atr_mult": 4.5,
        "trail_atr_mult": 5.0,
        "tp1_r_mult": 2.0,
        "tp2_r_mult": 4.0,
        "risk_per_trade": 0.0025,  # 0.25% — tiny risk per meme trade
        "max_position_pct": 0.02,
        "max_holding_hours": 48,  # 2 days
        "fallback_stop_pct": 0.35,
    },
}

# Classify coins into tiers
BTC_SYMBOLS = {"BTCUSDT"}
TOP5_SYMBOLS = {"ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT"}
MEME_SYMBOLS = {
    "DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "BONKUSDT", "WIFUSDT",
    "FLOKIUSDT", "TRUMPUSDT",
}
LARGE_CAP_SYMBOLS = {
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "UNIUSDT",
    "ATOMUSDT", "NEARUSDT", "APTUSDT", "SUIUSDT",
}


def classify_tier(symbol: str) -> str:
    """Classify a coin into an asset tier."""
    if symbol in BTC_SYMBOLS:
        return "btc"
    if symbol in TOP5_SYMBOLS:
        return "top5"
    if symbol in MEME_SYMBOLS:
        return "meme"
    if symbol in LARGE_CAP_SYMBOLS:
        return "large_cap"
    return "mid_cap"


def compute_trade_params(
    symbol: str,
    entry_price: float,
    side: OrderSide,
    atr: float | None,
    confidence: float,
    portfolio: PortfolioState,
    regime: MarketRegime | None = None,
) -> TradeParameters:
    """
    Compute full trade parameters for a position.

    Uses ATR-based stops when ATR is available, falls back to percentage-based.
    Adjusts for regime (bull = tighter stops, bear = wider stops).
    """
    tier = classify_tier(symbol)
    config = TIER_CONFIG[tier]

    # Regime adjustments
    regime_stop_adj = 1.0
    regime_tp_adj = 1.0
    regime_time_adj = 1.0
    if regime == MarketRegime.BULL:
        regime_stop_adj = 0.85   # Tighter stops in bull (cleaner trends)
        regime_tp_adj = 1.25     # Wider targets (let winners run)
        regime_time_adj = 1.25   # Longer holds
    elif regime == MarketRegime.BEAR:
        regime_stop_adj = 1.20   # Wider stops in bear (more volatile)
        regime_tp_adj = 0.75     # Tighter targets (take profits fast)
        regime_time_adj = 0.75   # Shorter holds
    elif regime == MarketRegime.CRISIS:
        regime_stop_adj = 1.30
        regime_tp_adj = 0.60
        regime_time_adj = 0.50

    # Calculate stop distance
    stop_atr_mult = config["stop_atr_mult"] * regime_stop_adj

    if atr and atr > 0:
        stop_distance = atr * stop_atr_mult
    else:
        # Fallback: percentage-based
        stop_distance = entry_price * config["fallback_stop_pct"]

    # Stop loss price
    if side == OrderSide.BUY:
        stop_loss = entry_price - stop_distance
    else:
        stop_loss = entry_price + stop_distance

    stop_loss = max(stop_loss, 0.0)
    stop_loss_pct = (stop_distance / entry_price) * 100

    # R-value (1R = stop distance)
    r_value = stop_distance

    # Take profit targets
    tp1_mult = config["tp1_r_mult"] * regime_tp_adj
    tp2_mult = config["tp2_r_mult"] * regime_tp_adj

    if side == OrderSide.BUY:
        tp1 = entry_price + (r_value * tp1_mult)
        tp2 = entry_price + (r_value * tp2_mult)
        trail_activation = entry_price + (r_value * 1.5)  # Activate at 1.5R
    else:
        tp1 = entry_price - (r_value * tp1_mult)
        tp2 = entry_price - (r_value * tp2_mult)
        trail_activation = entry_price - (r_value * 1.5)

    # Trailing stop
    trail_atr_mult = config["trail_atr_mult"] * regime_stop_adj
    if atr and atr > 0:
        trail_distance = atr * trail_atr_mult
    else:
        trail_distance = stop_distance * 1.2  # Slightly wider than initial stop

    # Position sizing: risk-based
    risk_per_trade = config["risk_per_trade"]
    # Scale risk by confidence (higher confidence = closer to max risk)
    adjusted_risk = risk_per_trade * min(confidence / 0.7, 1.0)

    total_value = max(portfolio.total_value, 1)
    risk_amount = total_value * adjusted_risk

    # Time stop
    max_hours = int(config["max_holding_hours"] * regime_time_adj)

    return TradeParameters(
        stop_loss_price=round(stop_loss, 8),
        stop_loss_pct=round(stop_loss_pct, 2),
        stop_atr_multiplier=round(stop_atr_mult, 2),
        take_profit_1=round(tp1, 8),
        take_profit_2=round(tp2, 8),
        r_value=round(r_value, 8),
        trailing_stop_activation=round(trail_activation, 8),
        trailing_stop_distance=round(trail_distance, 8),
        trailing_atr_multiplier=round(trail_atr_mult, 2),
        max_holding_hours=max_hours,
        risk_amount_usd=round(risk_amount, 2),
        risk_pct_of_portfolio=round(adjusted_risk * 100, 3),
        asset_tier=tier,
    )


def size_position(
    entry_price: float,
    params: TradeParameters,
    portfolio: PortfolioState,
) -> float:
    """
    Calculate position size based on risk parameters.
    Position size = risk_amount / stop_distance
    Then cap at max_position_pct.
    """
    tier = params.asset_tier
    config = TIER_CONFIG.get(tier, TIER_CONFIG["mid_cap"])

    stop_distance = abs(entry_price - params.stop_loss_price)
    if stop_distance <= 0:
        return 0.0

    # Risk-based sizing
    quantity = params.risk_amount_usd / stop_distance

    # Cap at max position
    max_notional = portfolio.total_value * config["max_position_pct"]
    notional = quantity * entry_price

    if notional > max_notional:
        quantity = max_notional / entry_price

    # Cash check (keep 5% buffer)
    max_from_cash = portfolio.cash * 0.95
    if quantity * entry_price > max_from_cash:
        quantity = max_from_cash / entry_price

    return max(quantity, 0.0)
