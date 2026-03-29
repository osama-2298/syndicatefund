"""
Order Management System.

Full lifecycle order management with support for institutional order types,
time-in-force policies, amendment/cancellation, and complete audit trails.
Every state transition is logged for regulatory compliance and post-trade analysis.
"""

from __future__ import annotations

import uuid
from collections import deque
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

from syndicate.data.models import OrderSide

logger = structlog.get_logger()


# ═══════════════════════════════════════════
#  Enums
# ═══════════════════════════════════════════


class OrderType(str, Enum):
    """Supported order types for institutional execution."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"
    ICEBERG = "ICEBERG"


class TimeInForce(str, Enum):
    """Time-in-force policies controlling order lifetime."""

    GTC = "GTC"        # Good til cancelled
    IOC = "IOC"        # Immediate or cancel -- fill what you can, cancel rest
    FOK = "FOK"        # Fill or kill -- all or nothing
    GTD = "GTD"        # Good til date -- expires at a specified time
    DAY = "DAY"        # Expires at end of trading day (00:00 UTC)


class OrderStatus(str, Enum):
    """Lifecycle states for a managed order."""

    PENDING = "PENDING"        # Created, awaiting validation
    SUBMITTED = "SUBMITTED"    # Sent to venue
    PARTIAL = "PARTIAL"        # Partially filled
    FILLED = "FILLED"          # Fully executed
    CANCELLED = "CANCELLED"    # Cancelled by user or system
    REJECTED = "REJECTED"      # Rejected by venue or pre-trade checks
    EXPIRED = "EXPIRED"        # Time-in-force expired


# Terminal states -- once reached, no further transitions allowed.
_TERMINAL_STATES = {
    OrderStatus.FILLED,
    OrderStatus.CANCELLED,
    OrderStatus.REJECTED,
    OrderStatus.EXPIRED,
}

# Valid state transitions.
_VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {
        OrderStatus.SUBMITTED,
        OrderStatus.REJECTED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.SUBMITTED: {
        OrderStatus.PARTIAL,
        OrderStatus.FILLED,
        OrderStatus.CANCELLED,
        OrderStatus.REJECTED,
        OrderStatus.EXPIRED,
    },
    OrderStatus.PARTIAL: {
        OrderStatus.FILLED,
        OrderStatus.CANCELLED,
        OrderStatus.EXPIRED,
    },
}


# ═══════════════════════════════════════════
#  Audit Trail
# ═══════════════════════════════════════════


class AuditEntry(BaseModel):
    """Single entry in the order audit trail."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event: str                       # e.g. "CREATED", "SUBMITTED", "AMENDED", "FILL"
    old_status: OrderStatus | None = None
    new_status: OrderStatus | None = None
    details: dict[str, Any] = Field(default_factory=dict)


# ═══════════════════════════════════════════
#  ManagedOrder
# ═══════════════════════════════════════════


class ManagedOrder(BaseModel):
    """
    Full lifecycle order with audit trail, fill tracking, and amendment history.

    Every order created by the system is wrapped in a ManagedOrder.  State
    transitions are validated -- illegal jumps (e.g. FILLED -> PENDING) raise
    ValueError so bugs are caught immediately rather than silently corrupting state.
    """

    # Identity
    order_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_order_id: str = ""           # External reference for reconciliation
    parent_order_id: str | None = None  # For child orders (iceberg slices, splits)

    # Instrument
    symbol: str
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    time_in_force: TimeInForce = TimeInForce.GTC

    # Pricing
    quantity: float
    limit_price: float | None = None    # Required for LIMIT, STOP_LIMIT
    stop_price: float | None = None     # Required for STOP, STOP_LIMIT, TRAILING_STOP
    trailing_offset: float | None = None  # For TRAILING_STOP -- distance in price units
    display_qty: float | None = None    # For ICEBERG -- visible quantity per clip

    # Expiry
    expire_time: datetime | None = None  # For GTD orders

    # Fill state
    filled_quantity: float = 0.0
    average_fill_price: float = 0.0
    total_fees: float = 0.0
    fill_count: int = 0

    # Status
    status: OrderStatus = OrderStatus.PENDING
    reject_reason: str = ""
    cancel_reason: str = ""

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: datetime | None = None
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Venue
    venue: str = ""                     # Exchange/venue the order is routed to
    venue_order_id: str = ""            # ID assigned by the venue

    # Source
    source_signal_id: str = ""
    strategy_tag: str = ""              # Free-form tag for grouping by strategy

    # Audit trail
    audit_trail: list[AuditEntry] = Field(default_factory=list)

    # ── Computed properties ──

    @property
    def remaining_quantity(self) -> float:
        return self.quantity - self.filled_quantity

    @property
    def is_terminal(self) -> bool:
        return self.status in _TERMINAL_STATES

    @property
    def fill_pct(self) -> float:
        if self.quantity == 0:
            return 0.0
        return self.filled_quantity / self.quantity

    @property
    def notional_value(self) -> float:
        price = self.average_fill_price if self.filled_quantity > 0 else (self.limit_price or 0.0)
        return self.quantity * price

    # ── State management ──

    def transition(
        self,
        new_status: OrderStatus,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Move to a new status with validation.

        Raises ValueError on illegal transitions so callers can never silently
        corrupt the order state machine.
        """
        if self.is_terminal:
            raise ValueError(
                f"Order {self.order_id} is in terminal state {self.status.value} -- "
                f"cannot transition to {new_status.value}"
            )

        allowed = _VALID_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Illegal transition: {self.status.value} -> {new_status.value} "
                f"for order {self.order_id}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        old = self.status
        self.status = new_status
        self.last_updated = datetime.now(timezone.utc)

        self.audit_trail.append(AuditEntry(
            event=f"STATUS_{new_status.value}",
            old_status=old,
            new_status=new_status,
            details=details or {},
        ))

    def record_fill(
        self,
        qty: float,
        price: float,
        fee: float = 0.0,
        venue_fill_id: str = "",
    ) -> None:
        """
        Record a (partial) fill.

        Updates average price using incremental weighted average and transitions
        status to PARTIAL or FILLED as appropriate.
        """
        if qty <= 0:
            raise ValueError(f"Fill quantity must be positive, got {qty}")
        if qty > self.remaining_quantity + 1e-9:
            raise ValueError(
                f"Fill qty {qty} exceeds remaining {self.remaining_quantity} "
                f"on order {self.order_id}"
            )

        # Weighted average price
        total_value = self.average_fill_price * self.filled_quantity + price * qty
        self.filled_quantity += qty
        self.average_fill_price = total_value / self.filled_quantity
        self.total_fees += fee
        self.fill_count += 1
        self.last_updated = datetime.now(timezone.utc)

        # Determine new status
        if abs(self.remaining_quantity) < 1e-9:
            new_status = OrderStatus.FILLED
        else:
            new_status = OrderStatus.PARTIAL

        old = self.status
        if new_status != old:
            self.transition(new_status, details={
                "fill_qty": qty,
                "fill_price": price,
                "fee": fee,
                "venue_fill_id": venue_fill_id,
            })
        else:
            # Still PARTIAL -- log the fill without a status change
            self.audit_trail.append(AuditEntry(
                event="FILL",
                old_status=old,
                new_status=old,
                details={
                    "fill_qty": qty,
                    "fill_price": price,
                    "fee": fee,
                    "venue_fill_id": venue_fill_id,
                    "cumulative_filled": self.filled_quantity,
                },
            ))


# ═══════════════════════════════════════════
#  OrderManager
# ═══════════════════════════════════════════


class OrderManager:
    """
    Central order management system.

    Validates, submits, amends, cancels orders and maintains a full audit trail.
    All orders are stored in memory with O(1) lookup by order_id.  A configurable
    history depth prevents unbounded memory growth in long-running processes.
    """

    def __init__(self, max_history: int = 50_000) -> None:
        self._orders: dict[str, ManagedOrder] = {}
        self._history: deque[str] = deque(maxlen=max_history)
        self._max_history = max_history

    # ── Submission ──

    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        time_in_force: TimeInForce = TimeInForce.GTC,
        limit_price: float | None = None,
        stop_price: float | None = None,
        trailing_offset: float | None = None,
        display_qty: float | None = None,
        expire_time: datetime | None = None,
        source_signal_id: str = "",
        strategy_tag: str = "",
        venue: str = "",
        client_order_id: str = "",
        parent_order_id: str | None = None,
    ) -> ManagedOrder:
        """
        Validate and create a new order.

        Pre-trade validation ensures:
        - Quantity is positive.
        - LIMIT / STOP_LIMIT orders have a limit_price.
        - STOP / STOP_LIMIT orders have a stop_price.
        - TRAILING_STOP orders have a trailing_offset or stop_price.
        - GTD orders have an expire_time in the future.
        - ICEBERG orders have a display_qty < total quantity.

        Returns ManagedOrder in SUBMITTED state on success, REJECTED on failure.
        """
        order = ManagedOrder(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            time_in_force=time_in_force,
            limit_price=limit_price,
            stop_price=stop_price,
            trailing_offset=trailing_offset,
            display_qty=display_qty,
            expire_time=expire_time,
            source_signal_id=source_signal_id,
            strategy_tag=strategy_tag,
            venue=venue,
            client_order_id=client_order_id or str(uuid.uuid4())[:8],
            parent_order_id=parent_order_id,
        )

        order.audit_trail.append(AuditEntry(
            event="CREATED",
            new_status=OrderStatus.PENDING,
            details={
                "order_type": order_type.value,
                "symbol": symbol,
                "qty": quantity,
            },
        ))

        # Pre-trade validation
        reject = self._validate_order(order)
        if reject:
            order.reject_reason = reject
            order.transition(OrderStatus.REJECTED, details={"reason": reject})
            self._store(order)
            logger.warning("order_rejected",
                           order_id=order.order_id, reason=reject)
            return order

        # Accept
        order.submitted_at = datetime.now(timezone.utc)
        order.transition(OrderStatus.SUBMITTED, details={"venue": venue})
        self._store(order)

        logger.info(
            "order_submitted",
            order_id=order.order_id,
            symbol=symbol,
            side=side.value,
            order_type=order_type.value,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price,
            venue=venue,
        )
        return order

    # ── Amendment ──

    def amend_order(
        self,
        order_id: str,
        new_quantity: float | None = None,
        new_limit_price: float | None = None,
        new_stop_price: float | None = None,
    ) -> ManagedOrder:
        """
        Amend an open order's price or quantity.

        Only SUBMITTED or PARTIAL orders can be amended.
        Quantity can only be reduced (not increased) to prevent accidental exposure
        growth -- submit a new order to add size.
        """
        order = self._get_or_raise(order_id)

        if order.status not in (OrderStatus.SUBMITTED, OrderStatus.PARTIAL):
            raise ValueError(
                f"Cannot amend order {order_id} in state {order.status.value}. "
                f"Only SUBMITTED or PARTIAL orders may be amended."
            )

        changes: dict[str, Any] = {}

        if new_quantity is not None:
            if new_quantity <= 0:
                raise ValueError("Amended quantity must be positive")
            if new_quantity > order.quantity:
                raise ValueError(
                    f"Cannot increase quantity from {order.quantity} to "
                    f"{new_quantity}. Submit a new order instead."
                )
            if new_quantity < order.filled_quantity:
                raise ValueError(
                    f"Amended quantity {new_quantity} is below already-filled "
                    f"{order.filled_quantity}"
                )
            changes["quantity"] = {"old": order.quantity, "new": new_quantity}
            order.quantity = new_quantity

        if new_limit_price is not None:
            if new_limit_price <= 0:
                raise ValueError("Limit price must be positive")
            changes["limit_price"] = {
                "old": order.limit_price,
                "new": new_limit_price,
            }
            order.limit_price = new_limit_price

        if new_stop_price is not None:
            if new_stop_price <= 0:
                raise ValueError("Stop price must be positive")
            changes["stop_price"] = {
                "old": order.stop_price,
                "new": new_stop_price,
            }
            order.stop_price = new_stop_price

        if not changes:
            raise ValueError("No amendment parameters provided")

        order.last_updated = datetime.now(timezone.utc)
        order.audit_trail.append(AuditEntry(
            event="AMENDED",
            old_status=order.status,
            new_status=order.status,
            details=changes,
        ))

        logger.info("order_amended", order_id=order_id, changes=changes)
        return order

    # ── Cancellation ──

    def cancel_order(
        self,
        order_id: str,
        reason: str = "User requested",
    ) -> ManagedOrder:
        """
        Cancel a pending/submitted/partial order.

        Terminal-state orders cannot be cancelled (raises ValueError).
        """
        order = self._get_or_raise(order_id)

        if order.is_terminal:
            raise ValueError(
                f"Cannot cancel order {order_id} -- already in terminal "
                f"state {order.status.value}"
            )

        order.cancel_reason = reason
        order.transition(OrderStatus.CANCELLED, details={"reason": reason})

        logger.info(
            "order_cancelled",
            order_id=order_id,
            reason=reason,
            filled=order.filled_quantity,
            remaining=order.remaining_quantity,
        )
        return order

    # ── Queries ──

    def get_order(self, order_id: str) -> ManagedOrder | None:
        """Retrieve an order by ID.  Returns None if not found."""
        return self._orders.get(order_id)

    def get_order_status(self, order_id: str) -> OrderStatus:
        """Get the current status of an order.  Raises KeyError if not found."""
        return self._get_or_raise(order_id).status

    def get_open_orders(
        self,
        symbol: str | None = None,
    ) -> list[ManagedOrder]:
        """
        Return all non-terminal orders, optionally filtered by symbol.
        Sorted by creation time (oldest first).
        """
        result = [
            o for o in self._orders.values()
            if not o.is_terminal
            and (symbol is None or o.symbol == symbol)
        ]
        result.sort(key=lambda o: o.created_at)
        return result

    def get_order_history(
        self,
        symbol: str | None = None,
        status: OrderStatus | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[ManagedOrder]:
        """
        Query historical orders with optional filters.
        Returns most recent first, up to ``limit`` results.
        """
        results: list[ManagedOrder] = []
        for oid in reversed(self._history):
            order = self._orders.get(oid)
            if order is None:
                continue
            if symbol and order.symbol != symbol:
                continue
            if status and order.status != status:
                continue
            if since and order.created_at < since:
                continue
            results.append(order)
            if len(results) >= limit:
                break
        return results

    def get_fill_summary(self, order_id: str) -> dict[str, Any]:
        """Return a concise summary of an order's fills and current state."""
        order = self._get_or_raise(order_id)
        return {
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side.value,
            "order_type": order.order_type.value,
            "status": order.status.value,
            "quantity": order.quantity,
            "filled_quantity": round(order.filled_quantity, 8),
            "remaining_quantity": round(order.remaining_quantity, 8),
            "fill_pct": round(order.fill_pct * 100, 2),
            "average_fill_price": round(order.average_fill_price, 8),
            "total_fees": round(order.total_fees, 8),
            "fill_count": order.fill_count,
            "venue": order.venue,
            "created_at": order.created_at.isoformat(),
            "last_updated": order.last_updated.isoformat(),
        }

    def expire_gtd_orders(self) -> list[ManagedOrder]:
        """
        Check all open GTD orders and expire those past their expire_time.
        Called periodically by the heartbeat loop.
        """
        now = datetime.now(timezone.utc)
        expired: list[ManagedOrder] = []
        for order in self.get_open_orders():
            if (
                order.time_in_force == TimeInForce.GTD
                and order.expire_time
                and now >= order.expire_time
            ):
                order.transition(
                    OrderStatus.EXPIRED,
                    details={"expire_time": order.expire_time.isoformat()},
                )
                expired.append(order)
                logger.info("order_expired_gtd",
                            order_id=order.order_id, symbol=order.symbol)
        return expired

    def cancel_all(
        self,
        symbol: str | None = None,
        reason: str = "Bulk cancel",
    ) -> list[ManagedOrder]:
        """Cancel all open orders, optionally filtered by symbol."""
        cancelled: list[ManagedOrder] = []
        for order in self.get_open_orders(symbol=symbol):
            try:
                self.cancel_order(order.order_id, reason=reason)
                cancelled.append(order)
            except ValueError:
                pass  # Already terminal -- skip
        logger.info("orders_bulk_cancelled",
                     count=len(cancelled), symbol=symbol, reason=reason)
        return cancelled

    # ── Internal ──

    def _validate_order(self, order: ManagedOrder) -> str:
        """
        Pre-trade validation.
        Returns a rejection reason string, or empty string if valid.
        """
        if order.quantity <= 0:
            return "Quantity must be positive"

        if order.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT):
            if order.limit_price is None or order.limit_price <= 0:
                return (
                    f"{order.order_type.value} order requires a positive "
                    f"limit_price"
                )

        if order.order_type in (OrderType.STOP, OrderType.STOP_LIMIT):
            if order.stop_price is None or order.stop_price <= 0:
                return (
                    f"{order.order_type.value} order requires a positive "
                    f"stop_price"
                )

        if order.order_type == OrderType.TRAILING_STOP:
            has_offset = (
                order.trailing_offset is not None
                and order.trailing_offset > 0
            )
            has_stop = (
                order.stop_price is not None
                and order.stop_price > 0
            )
            if not has_offset and not has_stop:
                return (
                    "TRAILING_STOP requires a positive trailing_offset "
                    "or stop_price"
                )

        if order.order_type == OrderType.ICEBERG:
            if order.display_qty is None or order.display_qty <= 0:
                return "ICEBERG order requires a positive display_qty"
            if order.display_qty >= order.quantity:
                return "ICEBERG display_qty must be less than total quantity"

        if order.time_in_force == TimeInForce.GTD:
            if order.expire_time is None:
                return "GTD order requires an expire_time"
            if order.expire_time <= datetime.now(timezone.utc):
                return "GTD expire_time must be in the future"

        return ""

    def _store(self, order: ManagedOrder) -> None:
        """Store an order and record it in history."""
        self._orders[order.order_id] = order
        self._history.append(order.order_id)

        # Evict oldest terminal orders when we exceed 2x capacity
        if len(self._orders) > self._max_history * 2:
            while len(self._orders) > self._max_history:
                oldest_id = self._history.popleft()
                oldest = self._orders.get(oldest_id)
                if oldest and oldest.is_terminal:
                    del self._orders[oldest_id]

    def _get_or_raise(self, order_id: str) -> ManagedOrder:
        """Retrieve an order or raise KeyError."""
        order = self._orders.get(order_id)
        if order is None:
            raise KeyError(f"Order {order_id} not found")
        return order
