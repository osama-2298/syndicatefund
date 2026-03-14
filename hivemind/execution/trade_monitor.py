"""
Trade Lifecycle Monitor — watches open positions between cycles.

At the start of each cycle:
1. Fetches candles since last check for each open position
2. Walks through candles chronologically to detect:
   - Stop loss hit (candle low breached SL)
   - Take profit 1 hit (candle high reached TP1)
   - Take profit 2 hit (candle high reached TP2)
   - Trailing stop hit (after TP1, trailing chandelier stop)
   - Time stop expired (holding too long)
3. Executes any triggered exits
4. Records the outcome for feedback to agents

Since we paper trade, we reconstruct what WOULD have happened
by scanning the high/low of each candle between cycles.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from hivemind.data.binance_client import BinanceClient
from hivemind.data.models import (
    Candle,
    OrderSide,
    Position,
    TradeParameters,
)

logger = structlog.get_logger()


class TradeOutcome:
    """Record of how a trade ended."""

    def __init__(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        exit_reason: str,
        pnl_pct: float,
        pnl_usd: float,
        holding_hours: float,
        quantity_exited: float,
        quantity_remaining: float,
        asset_tier: str,
    ) -> None:
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.exit_price = exit_price
        self.exit_reason = exit_reason  # STOP_LOSS, TAKE_PROFIT_1, TAKE_PROFIT_2, TRAILING_STOP, TIME_STOP
        self.pnl_pct = pnl_pct
        self.pnl_usd = pnl_usd
        self.holding_hours = holding_hours
        self.quantity_exited = quantity_exited
        self.quantity_remaining = quantity_remaining
        self.asset_tier = asset_tier
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason,
            "pnl_pct": round(self.pnl_pct, 4),
            "pnl_usd": round(self.pnl_usd, 2),
            "holding_hours": round(self.holding_hours, 1),
            "quantity_exited": self.quantity_exited,
            "quantity_remaining": self.quantity_remaining,
            "asset_tier": self.asset_tier,
            "timestamp": self.timestamp.isoformat(),
        }

    def feedback_message(self) -> str:
        """Human-readable feedback for agents."""
        direction = "long" if self.side == "BUY" else "short"
        result = "WIN" if self.pnl_pct > 0 else "LOSS" if self.pnl_pct < 0 else "FLAT"
        return (
            f"{result}: {direction} {self.symbol} entered at ${self.entry_price:,.2f}, "
            f"exited at ${self.exit_price:,.2f} ({self.exit_reason}). "
            f"P&L: {self.pnl_pct:+.2%} (${self.pnl_usd:+,.2f}) in {self.holding_hours:.0f}h."
        )


class OpenTrade:
    """An open trade with its parameters, tracked for lifecycle monitoring."""

    def __init__(
        self,
        symbol: str,
        side: OrderSide,
        entry_price: float,
        quantity: float,
        params: TradeParameters,
        entry_time: datetime | None = None,
    ) -> None:
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.quantity = quantity  # Remaining quantity (decreases as TPs hit)
        self.original_quantity = quantity
        self.params = params
        self.entry_time = entry_time or datetime.now(timezone.utc)

        # Trailing stop state
        self.highest_since_entry = entry_price  # For longs
        self.lowest_since_entry = entry_price   # For shorts
        self.trailing_active = False
        self.current_trailing_stop = 0.0

        # Partial exit state
        self.tp1_hit = False
        self.tp2_hit = False
        self.stop_moved_to_breakeven = False

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "entry_price": self.entry_price,
            "quantity": self.quantity,
            "original_quantity": self.original_quantity,
            "params": self.params.model_dump(),
            "entry_time": self.entry_time.isoformat(),
            "highest_since_entry": self.highest_since_entry,
            "lowest_since_entry": self.lowest_since_entry,
            "trailing_active": self.trailing_active,
            "current_trailing_stop": self.current_trailing_stop,
            "tp1_hit": self.tp1_hit,
            "tp2_hit": self.tp2_hit,
            "stop_moved_to_breakeven": self.stop_moved_to_breakeven,
        }


class TradeMonitor:
    """
    Monitors open trades and detects exits between cycles.
    Persists open trades to disk so they survive between runs.
    """

    def __init__(self, storage_path: str = "data/open_trades.json") -> None:
        self._path = Path(storage_path)
        self.open_trades: dict[str, OpenTrade] = {}  # symbol -> OpenTrade
        self.outcomes: list[TradeOutcome] = []  # Outcomes from this check
        self._load()

    def register_trade(self, symbol: str, side: OrderSide, entry_price: float,
                       quantity: float, params: TradeParameters) -> None:
        """Register a new trade for monitoring."""
        self.open_trades[symbol] = OpenTrade(
            symbol=symbol, side=side, entry_price=entry_price,
            quantity=quantity, params=params,
        )
        self._save()
        logger.info("trade_registered", symbol=symbol, entry=entry_price,
                     sl=params.stop_loss_price, tp1=params.take_profit_1)

    def check_all(
        self,
        binance: BinanceClient,
        paper_trader=None,
        interval: str = "1h",
    ) -> list[TradeOutcome]:
        """
        Check all open trades against recent candle data.
        If paper_trader is provided, executes partial/full closes on the portfolio.
        Returns list of triggered outcomes.
        """
        self.outcomes = []

        symbols_to_remove = []

        for symbol, trade in list(self.open_trades.items()):
            try:
                candles = binance.get_klines(symbol=symbol, interval=interval, limit=50)
                outcomes = self._check_trade(trade, candles)

                # Execute exits on the paper portfolio
                for outcome in outcomes:
                    if paper_trader is not None and outcome.quantity_exited > 0:
                        paper_trader.partial_close(
                            symbol=outcome.symbol,
                            quantity=outcome.quantity_exited,
                            price=outcome.exit_price,
                        )

                self.outcomes.extend(outcomes)

                if trade.quantity <= 0:
                    symbols_to_remove.append(symbol)

            except Exception as e:
                logger.warning("trade_check_failed", symbol=symbol, error=str(e))

        for sym in symbols_to_remove:
            del self.open_trades[sym]

        if self.outcomes:
            self._save()

        return self.outcomes

    def _check_trade(self, trade: OpenTrade, candles: list[Candle]) -> list[TradeOutcome]:
        """Walk through candles and detect any triggered exits."""
        outcomes = []
        params = trade.params
        is_long = trade.side == OrderSide.BUY

        for candle in candles:
            # Skip candles before entry
            if candle.timestamp < trade.entry_time:
                continue

            if trade.quantity <= 0:
                break

            high = candle.high
            low = candle.low

            # Update highest/lowest
            if high > trade.highest_since_entry:
                trade.highest_since_entry = high
            if low < trade.lowest_since_entry:
                trade.lowest_since_entry = low

            # Update trailing stop if active
            if trade.trailing_active:
                if is_long:
                    new_trail = trade.highest_since_entry - params.trailing_stop_distance
                    if new_trail > trade.current_trailing_stop:
                        trade.current_trailing_stop = new_trail
                else:
                    new_trail = trade.lowest_since_entry + params.trailing_stop_distance
                    if new_trail < trade.current_trailing_stop or trade.current_trailing_stop == 0:
                        trade.current_trailing_stop = new_trail

            # ── Check STOP LOSS ──
            stop_price = params.stop_loss_price
            if trade.stop_moved_to_breakeven:
                stop_price = trade.entry_price  # Breakeven stop

            if is_long and low <= stop_price:
                exit_price = stop_price
                reason = "STOP_LOSS" if not trade.stop_moved_to_breakeven else "BREAKEVEN_STOP"
                outcomes.append(self._create_outcome(trade, exit_price, reason, trade.quantity, candle))
                trade.quantity = 0
                break

            if not is_long and high >= stop_price:
                exit_price = stop_price
                reason = "STOP_LOSS" if not trade.stop_moved_to_breakeven else "BREAKEVEN_STOP"
                outcomes.append(self._create_outcome(trade, exit_price, reason, trade.quantity, candle))
                trade.quantity = 0
                break

            # ── Check TRAILING STOP ──
            if trade.trailing_active and trade.current_trailing_stop > 0:
                if is_long and low <= trade.current_trailing_stop:
                    outcomes.append(self._create_outcome(
                        trade, trade.current_trailing_stop, "TRAILING_STOP", trade.quantity, candle))
                    trade.quantity = 0
                    break
                if not is_long and high >= trade.current_trailing_stop:
                    outcomes.append(self._create_outcome(
                        trade, trade.current_trailing_stop, "TRAILING_STOP", trade.quantity, candle))
                    trade.quantity = 0
                    break

            # ── Check TAKE PROFIT 1 ──
            if not trade.tp1_hit and params.take_profit_1 > 0:
                if is_long and high >= params.take_profit_1:
                    exit_qty = trade.original_quantity * 0.33
                    exit_qty = min(exit_qty, trade.quantity)
                    outcomes.append(self._create_outcome(
                        trade, params.take_profit_1, "TAKE_PROFIT_1", exit_qty, candle))
                    trade.quantity -= exit_qty
                    trade.tp1_hit = True
                    trade.stop_moved_to_breakeven = True  # Move stop to breakeven
                    # Activate trailing if we're past activation level
                    if high >= params.trailing_stop_activation:
                        trade.trailing_active = True
                        trade.current_trailing_stop = high - params.trailing_stop_distance

                if not is_long and low <= params.take_profit_1:
                    exit_qty = trade.original_quantity * 0.33
                    exit_qty = min(exit_qty, trade.quantity)
                    outcomes.append(self._create_outcome(
                        trade, params.take_profit_1, "TAKE_PROFIT_1", exit_qty, candle))
                    trade.quantity -= exit_qty
                    trade.tp1_hit = True
                    trade.stop_moved_to_breakeven = True

            # ── Check TAKE PROFIT 2 ──
            if trade.tp1_hit and not trade.tp2_hit and params.take_profit_2 > 0:
                if is_long and high >= params.take_profit_2:
                    exit_qty = trade.original_quantity * 0.33
                    exit_qty = min(exit_qty, trade.quantity)
                    outcomes.append(self._create_outcome(
                        trade, params.take_profit_2, "TAKE_PROFIT_2", exit_qty, candle))
                    trade.quantity -= exit_qty
                    trade.tp2_hit = True
                    trade.trailing_active = True  # Always trail the remainder

                if not is_long and low <= params.take_profit_2:
                    exit_qty = trade.original_quantity * 0.33
                    exit_qty = min(exit_qty, trade.quantity)
                    outcomes.append(self._create_outcome(
                        trade, params.take_profit_2, "TAKE_PROFIT_2", exit_qty, candle))
                    trade.quantity -= exit_qty
                    trade.tp2_hit = True
                    trade.trailing_active = True

        # ── Check TIME STOP ──
        if trade.quantity > 0 and params.max_holding_hours > 0:
            now = datetime.now(timezone.utc)
            hours_held = (now - trade.entry_time).total_seconds() / 3600
            if hours_held > params.max_holding_hours:
                # Get last candle close as exit price
                if candles:
                    exit_price = candles[-1].close
                    outcomes.append(self._create_outcome(
                        trade, exit_price, "TIME_STOP", trade.quantity, candles[-1]))
                    trade.quantity = 0

        return outcomes

    def _create_outcome(
        self, trade: OpenTrade, exit_price: float, reason: str,
        quantity: float, candle: Candle,
    ) -> TradeOutcome:
        """Create a trade outcome record."""
        is_long = trade.side == OrderSide.BUY

        if is_long:
            pnl_pct = (exit_price - trade.entry_price) / trade.entry_price
        else:
            pnl_pct = (trade.entry_price - exit_price) / trade.entry_price

        pnl_usd = pnl_pct * quantity * trade.entry_price
        hours = (candle.timestamp - trade.entry_time).total_seconds() / 3600

        return TradeOutcome(
            symbol=trade.symbol,
            side=trade.side.value,
            entry_price=trade.entry_price,
            exit_price=exit_price,
            exit_reason=reason,
            pnl_pct=pnl_pct,
            pnl_usd=pnl_usd,
            holding_hours=max(hours, 0),
            quantity_exited=quantity,
            quantity_remaining=trade.quantity - quantity,
            asset_tier=trade.params.asset_tier,
        )

    def get_feedback_summary(self) -> list[str]:
        """Get feedback messages for all outcomes this cycle."""
        return [o.feedback_message() for o in self.outcomes]

    def _load(self) -> None:
        """Load open trades from disk."""
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            for item in data:
                params = TradeParameters.model_validate(item["params"])
                trade = OpenTrade(
                    symbol=item["symbol"],
                    side=OrderSide(item["side"]),
                    entry_price=item["entry_price"],
                    quantity=item["quantity"],
                    params=params,
                    entry_time=datetime.fromisoformat(item["entry_time"]),
                )
                trade.original_quantity = item.get("original_quantity", item["quantity"])
                trade.highest_since_entry = item.get("highest_since_entry", item["entry_price"])
                trade.lowest_since_entry = item.get("lowest_since_entry", item["entry_price"])
                trade.trailing_active = item.get("trailing_active", False)
                trade.current_trailing_stop = item.get("current_trailing_stop", 0)
                trade.tp1_hit = item.get("tp1_hit", False)
                trade.tp2_hit = item.get("tp2_hit", False)
                trade.stop_moved_to_breakeven = item.get("stop_moved_to_breakeven", False)
                self.open_trades[item["symbol"]] = trade
        except Exception as e:
            logger.error("trade_monitor_load_failed", error=str(e))

    def _save(self) -> None:
        """Save open trades to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [trade.to_dict() for trade in self.open_trades.values()]
        self._path.write_text(json.dumps(data, indent=2, default=str))
