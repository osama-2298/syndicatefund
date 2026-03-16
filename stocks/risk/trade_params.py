"""
Stock Trade Parameters — asset tiers (mega/large/mid/small cap) + short selling model.

Stocks have lower volatility than crypto, so tighter ATR multipliers and larger positions.
"""

from __future__ import annotations

from syndicate.data.models import (
    MarketRegime,
    OrderSide,
    PortfolioState,
    TradeParameters,
)

# ─── Stock Asset Tier Configuration ───

STOCK_TIER_CONFIG = {
    "mega_cap": {  # AAPL, MSFT, NVDA, AMZN, GOOGL, META
        "stop_atr_mult": 1.5,
        "trail_atr_mult": 2.0,
        "tp1_r_mult": 1.5,
        "tp2_r_mult": 2.5,
        "risk_per_trade": 0.02,  # 2% risk per trade (stocks are less volatile)
        "max_position_pct": 0.10,  # 10% max in one mega cap
        "max_holding_hours": 480,  # 20 trading days
        "fallback_stop_pct": 0.05,  # 5% stop
    },
    "large_cap": {  # S&P 500 components
        "stop_atr_mult": 2.0,
        "trail_atr_mult": 2.5,
        "tp1_r_mult": 1.5,
        "tp2_r_mult": 2.5,
        "risk_per_trade": 0.015,
        "max_position_pct": 0.08,
        "max_holding_hours": 360,  # 15 trading days
        "fallback_stop_pct": 0.07,
    },
    "mid_cap": {  # Russell 1000 but not S&P 500
        "stop_atr_mult": 2.5,
        "trail_atr_mult": 3.0,
        "tp1_r_mult": 1.5,
        "tp2_r_mult": 3.0,
        "risk_per_trade": 0.01,
        "max_position_pct": 0.05,
        "max_holding_hours": 240,
        "fallback_stop_pct": 0.10,
    },
    "small_cap": {  # Everything else
        "stop_atr_mult": 3.0,
        "trail_atr_mult": 3.5,
        "tp1_r_mult": 2.0,
        "tp2_r_mult": 3.5,
        "risk_per_trade": 0.005,
        "max_position_pct": 0.03,
        "max_holding_hours": 120,
        "fallback_stop_pct": 0.15,
    },
}

# Mega cap stocks (top ~10 by market cap)
MEGA_CAP_STOCKS = {
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG", "META", "BRK-B",
    "LLY", "TSM", "AVGO", "JPM", "V", "UNH", "WMT",
}


def classify_stock_tier(symbol: str, market_cap: float | None = None) -> str:
    """Classify a stock into an asset tier."""
    if symbol in MEGA_CAP_STOCKS:
        return "mega_cap"
    if market_cap:
        if market_cap > 200e9:
            return "mega_cap"
        if market_cap > 10e9:
            return "large_cap"
        if market_cap > 2e9:
            return "mid_cap"
        return "small_cap"
    return "large_cap"  # Default assumption for S&P 500


def compute_stock_trade_params(
    symbol: str,
    entry_price: float,
    side: OrderSide,
    atr: float | None,
    confidence: float,
    portfolio: PortfolioState,
    regime: MarketRegime | None = None,
    market_cap: float | None = None,
    short_data: dict | None = None,
) -> TradeParameters:
    """
    Compute full trade parameters for a stock position.
    Includes short selling adjustments.
    """
    tier = classify_stock_tier(symbol, market_cap)
    config = STOCK_TIER_CONFIG[tier]

    # Regime adjustments
    regime_stop_adj = 1.0
    regime_tp_adj = 1.0
    regime_time_adj = 1.0
    if regime == MarketRegime.BULL:
        regime_stop_adj = 0.9
        regime_tp_adj = 1.2
        regime_time_adj = 1.2
    elif regime == MarketRegime.BEAR:
        regime_stop_adj = 1.15
        regime_tp_adj = 0.8
        regime_time_adj = 0.8
    elif regime == MarketRegime.CRISIS:
        regime_stop_adj = 1.25
        regime_tp_adj = 0.65
        regime_time_adj = 0.5

    stop_atr_mult = config["stop_atr_mult"] * regime_stop_adj

    if atr and atr > 0:
        stop_distance = atr * stop_atr_mult
    else:
        stop_distance = entry_price * config["fallback_stop_pct"]

    if side == OrderSide.BUY:
        stop_loss = entry_price - stop_distance
    else:
        stop_loss = entry_price + stop_distance

    stop_loss = max(stop_loss, 0.0)
    stop_loss_pct = (stop_distance / entry_price) * 100

    r_value = stop_distance
    tp1_mult = config["tp1_r_mult"] * regime_tp_adj
    tp2_mult = config["tp2_r_mult"] * regime_tp_adj

    if side == OrderSide.BUY:
        tp1 = entry_price + (r_value * tp1_mult)
        tp2 = entry_price + (r_value * tp2_mult)
        trail_activation = entry_price + (r_value * 1.5)
    else:
        tp1 = entry_price - (r_value * tp1_mult)
        tp2 = entry_price - (r_value * tp2_mult)
        trail_activation = entry_price - (r_value * 1.5)

    trail_atr_mult = config["trail_atr_mult"] * regime_stop_adj
    trail_distance = atr * trail_atr_mult if atr and atr > 0 else stop_distance * 1.2

    risk_per_trade = config["risk_per_trade"]
    adjusted_risk = risk_per_trade * min(confidence / 0.7, 1.0)

    # ── SHORT SELLING ADJUSTMENTS ──
    if side == OrderSide.SELL and short_data:
        # Borrow cost drag: reduce position size proportionally
        borrow_cost = short_data.get("borrow_cost_est", 0)
        if borrow_cost and borrow_cost > 3:
            adjusted_risk *= 0.8  # 20% size reduction for expensive borrows
        if borrow_cost and borrow_cost > 10:
            adjusted_risk *= 0.6  # Another 40% for very expensive

        # SSR active: reduce size 30%
        if short_data.get("ssr_active"):
            adjusted_risk *= 0.7

        # Squeeze risk: halve size on HIGH
        squeeze_risk = short_data.get("squeeze_risk", "LOW")
        if squeeze_risk == "HIGH":
            adjusted_risk *= 0.5
        elif squeeze_risk == "MEDIUM":
            adjusted_risk *= 0.75

    total_value = max(portfolio.total_value, 1)
    risk_amount = total_value * adjusted_risk
    max_hours = int(config["max_holding_hours"] * regime_time_adj)

    return TradeParameters(
        stop_loss_price=round(stop_loss, 2),
        stop_loss_pct=round(stop_loss_pct, 2),
        stop_atr_multiplier=round(stop_atr_mult, 2),
        take_profit_1=round(tp1, 2),
        take_profit_2=round(tp2, 2),
        r_value=round(r_value, 4),
        trailing_stop_activation=round(trail_activation, 2),
        trailing_stop_distance=round(trail_distance, 4),
        trailing_atr_multiplier=round(trail_atr_mult, 2),
        max_holding_hours=max_hours,
        risk_amount_usd=round(risk_amount, 2),
        risk_pct_of_portfolio=round(adjusted_risk * 100, 3),
        asset_tier=tier,
    )


def size_stock_position(
    entry_price: float,
    params: TradeParameters,
    portfolio: PortfolioState,
) -> float:
    """Calculate stock position size based on risk parameters."""
    tier = params.asset_tier
    config = STOCK_TIER_CONFIG.get(tier, STOCK_TIER_CONFIG["large_cap"])

    stop_distance = abs(entry_price - params.stop_loss_price)
    if stop_distance <= 0:
        return 0.0

    quantity = params.risk_amount_usd / stop_distance
    max_notional = portfolio.total_value * config["max_position_pct"]
    notional = quantity * entry_price

    if notional > max_notional:
        quantity = max_notional / entry_price

    max_from_cash = portfolio.cash * 0.95
    if quantity * entry_price > max_from_cash:
        quantity = max_from_cash / entry_price

    # Stocks trade in whole shares
    quantity = int(quantity)
    return max(quantity, 0)
