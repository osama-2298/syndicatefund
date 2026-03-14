"""
Risk Manager.

Enforces the CRO's rules on every trade. Takes aggregated signals and the current
portfolio state, applies position sizing and exposure limits, and produces
trade orders that are safe to execute.

This is the gatekeeper — no trade gets to execution without passing through here.
"""

from __future__ import annotations

import structlog

from hivemind.data.models import (
    AggregatedSignal,
    MarketRegime,
    OrderSide,
    PortfolioState,
    RiskLimits,
    SignalAction,
    TradeOrder,
)
from hivemind.risk.trade_params import compute_trade_params, size_position

logger = structlog.get_logger()


class RiskManager:
    """
    Enforces risk rules set by the CRO.

    Takes aggregated signals, filters them against risk limits,
    and produces sized trade orders.
    """

    def __init__(self, limits: RiskLimits | None = None, regime: MarketRegime | None = None) -> None:
        self.limits = limits or RiskLimits()
        self.regime = regime

    def evaluate(
        self,
        signals: list[AggregatedSignal],
        portfolio: PortfolioState,
    ) -> list[TradeOrder]:
        """
        Process aggregated signals through risk filters and produce trade orders.

        Filters applied:
        1. Minimum confidence threshold
        2. Minimum consensus ratio
        3. Maximum open positions
        4. Maximum position size (% of portfolio)
        5. Daily drawdown check

        Args:
            signals: Aggregated signals from the Signal Aggregator.
            portfolio: Current portfolio state.

        Returns:
            List of TradeOrder objects ready for execution.
        """
        orders = []

        # Global check: halt all trading if drawdown limit breached
        if portfolio.drawdown_pct >= self.limits.max_daily_drawdown_pct:
            logger.warning(
                "risk_halt_drawdown",
                drawdown_pct=round(portfolio.drawdown_pct * 100, 2),
                limit_pct=round(self.limits.max_daily_drawdown_pct * 100, 2),
            )
            return []

        for signal in signals:
            order = self._evaluate_signal(signal, portfolio)
            if order is not None:
                orders.append(order)

        logger.info(
            "risk_evaluation_complete",
            signals_received=len(signals),
            orders_produced=len(orders),
        )
        return orders

    def _evaluate_signal(
        self,
        signal: AggregatedSignal,
        portfolio: PortfolioState,
    ) -> TradeOrder | None:
        """Evaluate a single aggregated signal against risk limits."""

        symbol = signal.symbol

        # ── Filter 1: Skip HOLD signals ──
        if signal.recommended_action == SignalAction.HOLD:
            logger.debug("risk_skip_hold", symbol=symbol)
            return None

        # ── Filter 2: Minimum confidence ──
        if signal.aggregated_confidence < self.limits.min_signal_confidence:
            logger.debug(
                "risk_skip_low_confidence",
                symbol=symbol,
                confidence=round(signal.aggregated_confidence, 3),
                min_required=self.limits.min_signal_confidence,
            )
            return None

        # ── Filter 3: Minimum consensus ──
        if signal.consensus_ratio < self.limits.min_consensus_ratio:
            logger.debug(
                "risk_skip_low_consensus",
                symbol=symbol,
                consensus=round(signal.consensus_ratio, 3),
                min_required=self.limits.min_consensus_ratio,
            )
            return None

        # ── Filter 4: Max open positions ──
        if len(portfolio.positions) >= self.limits.max_open_positions:
            # Only allow signals that close existing positions (SELL, COVER)
            if signal.recommended_action not in (SignalAction.SELL, SignalAction.COVER):
                logger.debug(
                    "risk_skip_max_positions",
                    symbol=symbol,
                    open_positions=len(portfolio.positions),
                    limit=self.limits.max_open_positions,
                )
                return None

        # ── Determine trade side and sizing ──
        existing_position = portfolio.get_position(symbol)

        if signal.recommended_action == SignalAction.BUY:
            if existing_position is not None:
                logger.debug("risk_skip_already_in_position", symbol=symbol)
                return None
            return self._size_new_position(signal, portfolio, OrderSide.BUY)

        elif signal.recommended_action == SignalAction.SHORT:
            if existing_position is not None:
                logger.debug("risk_skip_already_in_position", symbol=symbol)
                return None
            return self._size_new_position(signal, portfolio, OrderSide.SELL)

        elif signal.recommended_action == SignalAction.SELL:
            if existing_position is None or existing_position.side != OrderSide.BUY:
                logger.debug("risk_skip_no_long_to_sell", symbol=symbol)
                return None
            return self._close_position(signal, existing_position)

        elif signal.recommended_action == SignalAction.COVER:
            if existing_position is None or existing_position.side != OrderSide.SELL:
                logger.debug("risk_skip_no_short_to_cover", symbol=symbol)
                return None
            return self._close_position(signal, existing_position)

        return None

    def _size_new_position(
        self,
        signal: AggregatedSignal,
        portfolio: PortfolioState,
        side: OrderSide,
    ) -> TradeOrder | None:
        """
        Size a new position using ATR-based risk parameters.
        Every trade gets stop loss, take profit, and trailing stop BEFORE entry.
        """
        total_value = portfolio.total_value
        if total_value <= 0:
            return None

        price = self._estimate_price(signal)
        if price <= 0:
            return None

        # Get ATR from signal metadata (indicators)
        atr = self._get_atr(signal)

        # Compute full trade parameters
        params = compute_trade_params(
            symbol=signal.symbol,
            entry_price=price,
            side=side,
            atr=atr,
            confidence=signal.aggregated_confidence,
            portfolio=portfolio,
            regime=self.regime,
        )

        # Size position using risk-based formula
        quantity = size_position(price, params, portfolio)

        if quantity <= 0:
            logger.debug("risk_skip_insufficient_cash", symbol=signal.symbol)
            return None

        # Also enforce the CRO's max position limit
        max_notional = total_value * self.limits.max_position_pct
        if quantity * price > max_notional:
            quantity = max_notional / price

        order = TradeOrder(
            symbol=signal.symbol,
            side=side,
            quantity=quantity,
            price=price,
            source_signal_id=signal.contributing_signals[0].id if signal.contributing_signals else "",
            params=params,
        )

        logger.info(
            "risk_order_created",
            symbol=order.symbol,
            side=order.side.value,
            quantity=round(order.quantity, 6),
            notional=round(order.notional_value, 2),
            stop_loss=round(params.stop_loss_price, 2),
            take_profit=round(params.take_profit_1, 2),
            risk_usd=round(params.risk_amount_usd, 2),
            tier=params.asset_tier,
        )

        return order

    def _get_atr(self, signal: AggregatedSignal) -> float | None:
        """Extract ATR from signal metadata. Uses real ATR-14 if available."""
        # First try: real ATR-14 from indicators
        for sig in signal.contributing_signals:
            if "atr_14" in sig.metadata:
                return float(sig.metadata["atr_14"])

        # Fallback: estimate from 24h high-low range
        for sig in signal.contributing_signals:
            if "stats_24h" in sig.metadata:
                stats = sig.metadata["stats_24h"]
                high = stats.get("high", 0)
                low = stats.get("low", 0)
                if high > 0 and low > 0:
                    return (high - low) * 0.7
        return None

    def _close_position(self, signal: AggregatedSignal, position: object) -> TradeOrder:
        """Create an order to close an existing position entirely."""
        from hivemind.data.models import Position

        pos: Position = position  # type: ignore
        # To close a long, we sell. To close a short, we buy.
        close_side = OrderSide.SELL if pos.side == OrderSide.BUY else OrderSide.BUY

        return TradeOrder(
            symbol=signal.symbol,
            side=close_side,
            quantity=pos.quantity,
            price=pos.current_price if pos.current_price > 0 else pos.entry_price,
            source_signal_id=signal.contributing_signals[0].id if signal.contributing_signals else "",
        )

    def _estimate_price(self, signal: AggregatedSignal) -> float:
        """Extract the best available price estimate from signal metadata."""
        # Check if any contributing signal has price metadata
        for sig in signal.contributing_signals:
            if "current_price" in sig.metadata:
                return float(sig.metadata["current_price"])

        # Fallback: check the stats in metadata
        for sig in signal.contributing_signals:
            if "stats_24h" in sig.metadata:
                stats = sig.metadata["stats_24h"]
                if "close" in stats:
                    return float(stats["close"])

        logger.warning("risk_no_price_available", symbol=signal.symbol)
        return 0.0
