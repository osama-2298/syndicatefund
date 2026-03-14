"""
Paper Trading Engine.

Simulates trade execution without real money. Maintains a virtual portfolio,
records all trades, and tracks P&L. This is the execution engine for Phase 1-2.
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog

from hivemind.data.models import (
    OrderSide,
    PortfolioState,
    Position,
    TradeOrder,
    TradeResult,
)

logger = structlog.get_logger()


class PaperTrader:
    """
    Simulated trade execution.

    Executes orders against a virtual portfolio at current market prices.
    Assumes perfect fills (no slippage, no partial fills) — this is paper trading.
    """

    def __init__(self, initial_cash: float = 100_000.0) -> None:
        self.portfolio = PortfolioState(cash=initial_cash, peak_value=initial_cash)
        self.trade_history: list[TradeResult] = []

    def execute(self, order: TradeOrder) -> TradeResult | None:
        """
        Execute a single trade order against the paper portfolio.

        Returns a TradeResult on success, None if the order can't be filled.
        """
        # Validate the order
        if order.quantity <= 0 or order.price <= 0:
            logger.warning(
                "paper_trade_invalid_order",
                symbol=order.symbol,
                quantity=order.quantity,
                price=order.price,
            )
            return None

        existing = self.portfolio.get_position(order.symbol)

        if existing is not None:
            return self._close_position(order, existing)
        else:
            return self._open_position(order)

    def execute_batch(self, orders: list[TradeOrder]) -> list[TradeResult]:
        """Execute multiple orders sequentially."""
        results = []
        for order in orders:
            result = self.execute(order)
            if result is not None:
                results.append(result)
        return results

    def update_prices(self, prices: dict[str, float]) -> None:
        """
        Update current prices for all open positions.
        Call this before querying portfolio value or P&L.
        """
        for position in self.portfolio.positions:
            if position.symbol in prices:
                position.current_price = prices[position.symbol]

        # Update peak value for drawdown tracking
        current_value = self.portfolio.total_value
        if current_value > self.portfolio.peak_value:
            self.portfolio.peak_value = current_value

        self.portfolio.timestamp = datetime.now(timezone.utc)

    def get_summary(self) -> dict:
        """Get a summary of the current portfolio state."""
        p = self.portfolio
        return {
            "total_value": round(p.total_value, 2),
            "cash": round(p.cash, 2),
            "positions_value": round(p.total_position_value, 2),
            "unrealized_pnl": round(p.total_unrealized_pnl, 2),
            "realized_pnl": round(p.total_realized_pnl, 2),
            "total_pnl": round(p.total_realized_pnl + p.total_unrealized_pnl, 2),
            "return_pct": round(((p.total_value / 100_000) - 1) * 100, 2),
            "drawdown_pct": round(p.drawdown_pct * 100, 2),
            "open_positions": len(p.positions),
            "total_trades": len(self.trade_history),
        }

    def print_portfolio(self) -> None:
        """Print a formatted portfolio summary to stdout."""
        summary = self.get_summary()

        print("\n" + "=" * 60)
        print("  HIVEMIND PAPER PORTFOLIO")
        print("=" * 60)
        print(f"  Total Value:     ${summary['total_value']:>12,.2f}")
        print(f"  Cash:            ${summary['cash']:>12,.2f}")
        print(f"  Positions Value: ${summary['positions_value']:>12,.2f}")
        print(f"  Unrealized P&L:  ${summary['unrealized_pnl']:>12,.2f}")
        print(f"  Realized P&L:    ${summary['realized_pnl']:>12,.2f}")
        print(f"  Total P&L:       ${summary['total_pnl']:>12,.2f}")
        print(f"  Return:          {summary['return_pct']:>12.2f}%")
        print(f"  Drawdown:        {summary['drawdown_pct']:>12.2f}%")
        print(f"  Open Positions:  {summary['open_positions']:>12}")
        print(f"  Total Trades:    {summary['total_trades']:>12}")

        if self.portfolio.positions:
            print("\n  OPEN POSITIONS:")
            print(f"  {'Symbol':<12} {'Side':<6} {'Qty':>12} {'Entry':>12} {'Current':>12} {'P&L':>10} {'P&L%':>8}")
            print("  " + "-" * 74)
            for pos in self.portfolio.positions:
                print(
                    f"  {pos.symbol:<12} {pos.side.value:<6} "
                    f"{pos.quantity:>12.6f} ${pos.entry_price:>11,.2f} "
                    f"${pos.current_price:>11,.2f} "
                    f"${pos.unrealized_pnl:>9,.2f} "
                    f"{pos.pnl_pct:>7.2%}"
                )
        print("=" * 60 + "\n")

    def partial_close(self, symbol: str, quantity: float, price: float) -> float:
        """
        Partially close a position — used by Trade Monitor for TP1/TP2 exits.
        Returns realized P&L for the closed portion.
        """
        position = self.portfolio.get_position(symbol)
        if position is None:
            return 0.0

        # Cap quantity to what we actually hold
        close_qty = min(quantity, position.quantity)
        if close_qty <= 0:
            return 0.0

        # Calculate P&L on the closed portion
        if position.side == OrderSide.BUY:
            pnl = (price - position.entry_price) * close_qty
        else:
            pnl = (position.entry_price - price) * close_qty

        # Return cash
        original_notional = close_qty * position.entry_price
        self.portfolio.cash += original_notional + pnl
        self.portfolio.total_realized_pnl += pnl

        # Reduce position quantity
        position.quantity -= close_qty

        # If fully closed, remove the position
        if position.quantity <= 0.0001:  # Floating point tolerance
            self.portfolio.positions = [
                p for p in self.portfolio.positions if p.symbol != symbol
            ]

        logger.info(
            "paper_trade_partial_close",
            symbol=symbol,
            quantity=round(close_qty, 6),
            price=round(price, 2),
            pnl=round(pnl, 2),
            remaining=round(position.quantity, 6) if position.quantity > 0.0001 else 0,
        )

        return pnl

    # ─── Internal ───

    def _open_position(self, order: TradeOrder) -> TradeResult | None:
        """Open a new position."""
        notional = order.quantity * order.price

        # Check cash
        if notional > self.portfolio.cash:
            logger.warning(
                "paper_trade_insufficient_cash",
                symbol=order.symbol,
                required=round(notional, 2),
                available=round(self.portfolio.cash, 2),
            )
            return None

        # Deduct cash
        self.portfolio.cash -= notional

        # Create position
        side = OrderSide.BUY if order.side == OrderSide.BUY else OrderSide.SELL
        position = Position(
            symbol=order.symbol,
            side=side,
            entry_price=order.price,
            quantity=order.quantity,
            entry_time=datetime.now(timezone.utc),
            current_price=order.price,
        )
        self.portfolio.positions.append(position)

        result = TradeResult(
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            executed_price=order.price,
            is_paper=True,
        )
        self.trade_history.append(result)

        logger.info(
            "paper_trade_opened",
            symbol=order.symbol,
            side=order.side.value,
            quantity=round(order.quantity, 6),
            price=round(order.price, 2),
            notional=round(notional, 2),
        )

        return result

    def _close_position(self, order: TradeOrder, position: Position) -> TradeResult | None:
        """Close an existing position."""
        # Calculate realized P&L
        if position.side == OrderSide.BUY:
            pnl = (order.price - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - order.price) * position.quantity

        # Return cash (original notional + P&L)
        original_notional = position.quantity * position.entry_price
        self.portfolio.cash += original_notional + pnl
        self.portfolio.total_realized_pnl += pnl

        # Remove position
        self.portfolio.positions = [
            p for p in self.portfolio.positions if p.symbol != order.symbol
        ]

        result = TradeResult(
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=position.quantity,
            executed_price=order.price,
            is_paper=True,
        )
        self.trade_history.append(result)

        logger.info(
            "paper_trade_closed",
            symbol=order.symbol,
            side=order.side.value,
            quantity=round(position.quantity, 6),
            entry_price=round(position.entry_price, 2),
            exit_price=round(order.price, 2),
            pnl=round(pnl, 2),
        )

        return result
