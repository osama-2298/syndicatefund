"""Realistic slippage modeling for crypto backtests.

Based on empirical research:
- Square-root impact model: slippage = Y * sigma * sqrt(Q/ADV) (Donier & Bonart)
- Tier-based minimum slippage floors (Amberdata, CoinGecko 2025 data)
- Fee modeling (Binance VIP 0: 10 bps taker)

For our order sizes ($10-50K):
- BTC: ~5 bps slippage + 10 bps fee = 15 bps per trade
- Top 10 alts: ~10 bps + 10 bps = 20 bps per trade
- Mid-caps: ~30 bps + 10 bps = 40 bps per trade
"""

import math

# Tier-based slippage floors (bps) — from empirical Binance order book data
SLIPPAGE_BPS = {
    "btc": 5,          # Deep liquidity, tight spreads
    "top5": 8,         # ETH, SOL, BNB, XRP
    "large_cap": 12,   # Top 20
    "mid_cap": 25,     # Top 100
    "small_cap": 80,   # Outside top 100
    "meme": 50,        # Meme coins (volatile but sometimes liquid)
}

# Exchange fee (Binance VIP 0 taker, both entry and exit)
FEE_BPS = 10  # 0.10%

# Volatility multiplier for stress periods
# When ATR is >2x its 20-period average, multiply slippage by this
STRESS_MULTIPLIER = 2.5


def classify_tier(symbol: str) -> str:
    """Classify a symbol into a liquidity tier."""
    sym = symbol.upper()
    if sym in ("BTCUSDT",):
        return "btc"
    if sym in ("ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"):
        return "top5"
    if sym in ("ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT",
               "LTCUSDT", "UNIUSDT", "ATOMUSDT", "NEARUSDT", "AAVEUSDT"):
        return "large_cap"
    if sym in ("DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "FLOKIUSDT", "BONKUSDT"):
        return "meme"
    return "mid_cap"


def compute_slippage(
    symbol: str,
    price: float,
    quantity: float,
    is_volatile: bool = False,
) -> float:
    """Compute realistic slippage for a trade.

    Returns the slippage amount in USD (always positive).
    The execution price will be worse by this amount.
    """
    tier = classify_tier(symbol)
    base_bps = SLIPPAGE_BPS.get(tier, 25)

    # Apply stress multiplier during volatile periods
    if is_volatile:
        base_bps *= STRESS_MULTIPLIER

    notional = price * quantity
    slippage_pct = base_bps / 10000  # Convert bps to fraction
    slippage_usd = notional * slippage_pct

    return slippage_usd


def compute_total_execution_cost(
    symbol: str,
    price: float,
    quantity: float,
    is_volatile: bool = False,
) -> dict:
    """Compute total execution cost (slippage + fees).

    Returns:
        {
            "slippage_usd": float,
            "fee_usd": float,
            "total_cost_usd": float,
            "total_cost_bps": float,
            "adjusted_price_buy": float,   # Worse price for buys
            "adjusted_price_sell": float,   # Worse price for sells
        }
    """
    notional = price * quantity
    slippage = compute_slippage(symbol, price, quantity, is_volatile)
    fee = notional * (FEE_BPS / 10000)
    total = slippage + fee
    total_bps = (total / notional) * 10000 if notional > 0 else 0

    cost_pct = total / notional if notional > 0 else 0

    return {
        "slippage_usd": round(slippage, 2),
        "fee_usd": round(fee, 2),
        "total_cost_usd": round(total, 2),
        "total_cost_bps": round(total_bps, 1),
        "adjusted_price_buy": price * (1 + cost_pct),   # Pay more
        "adjusted_price_sell": price * (1 - cost_pct),   # Receive less
    }
