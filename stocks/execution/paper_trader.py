"""
Stock Paper Trader — market hours awareness (9:30-16:00 ET), whole share execution.

Inherits from syndicate PaperTrader with stock-specific overrides.
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog

from syndicate.data.models import OrderSide, Position, TradeOrder, TradeResult
from syndicate.execution.paper_trader import PaperTrader

logger = structlog.get_logger()


def is_market_hours() -> bool:
    """Check if US stock market is currently open (9:30-16:00 ET)."""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        return True  # Assume open if can't check

    now_et = datetime.now(ZoneInfo("US/Eastern"))

    # Weekend check
    if now_et.weekday() >= 5:
        return False

    hour = now_et.hour
    minute = now_et.minute

    # 9:30 AM to 4:00 PM ET
    if hour < 9 or (hour == 9 and minute < 30):
        return False
    if hour >= 16:
        return False

    return True


class StockPaperTrader(PaperTrader):
    """Stock paper trader with market hours awareness and whole share execution."""

    def execute(self, order: TradeOrder) -> TradeResult | None:
        """Execute with whole shares and market hours logging."""
        # Stocks trade in whole shares
        order.quantity = int(order.quantity)
        if order.quantity <= 0:
            return None

        if not is_market_hours():
            logger.info(
                "stock_order_outside_hours",
                symbol=order.symbol,
                side=order.side.value,
                note="Executing anyway (paper trading)",
            )

        return super().execute(order)
