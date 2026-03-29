"""
Post-Trade Reconciliation Engine.

Matches internal order/fill records against exchange-reported trades to detect
breaks (mismatches in quantity, price, fees, or missing records).  Generates
daily reconciliation reports and tracks settlement status for T+0 and T+2
settlement windows.

In crypto, most spot trades settle T+0 (on-chain finality), but some OTC and
derivatives settle T+1 or T+2.  The settlement tracker handles both.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


# ═══════════════════════════════════════════
#  Enums
# ═══════════════════════════════════════════


class ReconciliationStatus(str, Enum):
    """Status of a single reconciliation entry."""

    MATCHED = "MATCHED"                # Internal and exchange records agree
    BREAK_QTY = "BREAK_QTY"            # Quantity mismatch
    BREAK_PRICE = "BREAK_PRICE"        # Price mismatch beyond tolerance
    BREAK_FEE = "BREAK_FEE"            # Fee mismatch beyond tolerance
    BREAK_MISSING_INTERNAL = "BREAK_MISSING_INTERNAL"   # Exchange has it, we don't
    BREAK_MISSING_EXCHANGE = "BREAK_MISSING_EXCHANGE"   # We have it, exchange doesn't
    BREAK_MULTIPLE = "BREAK_MULTIPLE"  # Multiple fields disagree
    PENDING = "PENDING"                # Not yet reconciled


class SettlementStatus(str, Enum):
    """Settlement lifecycle."""

    UNSETTLED = "UNSETTLED"
    SETTLING = "SETTLING"
    SETTLED = "SETTLED"
    FAILED = "FAILED"


# ═══════════════════════════════════════════
#  Data Models
# ═══════════════════════════════════════════


class ReconciliationEntry(BaseModel):
    """
    A single trade record used in reconciliation.

    Both internal (our system) and exchange (venue-reported) sides are
    represented by this model.  During matching, pairs of entries are compared
    field by field.
    """

    internal_id: str = ""              # Our order/fill ID
    exchange_id: str = ""              # Venue-assigned trade/fill ID
    symbol: str
    side: str                          # "BUY" or "SELL"
    quantity: float
    price: float
    fees: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    venue: str = ""
    status: ReconciliationStatus = ReconciliationStatus.PENDING
    breaks: list[str] = Field(default_factory=list)  # Human-readable break descriptions
    settlement_status: SettlementStatus = SettlementStatus.UNSETTLED
    settlement_due: datetime | None = None


class BreakRecord(BaseModel):
    """Detailed record of a reconciliation break for investigation."""

    break_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    internal_entry: ReconciliationEntry | None = None
    exchange_entry: ReconciliationEntry | None = None
    break_types: list[str] = Field(default_factory=list)
    severity: str = "LOW"              # LOW, MEDIUM, HIGH, CRITICAL
    details: dict[str, Any] = Field(default_factory=dict)
    resolved: bool = False
    resolution_note: str = ""
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class ReconReport(BaseModel):
    """Daily reconciliation summary report."""

    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    report_date: str                   # YYYY-MM-DD
    total_internal_trades: int = 0
    total_exchange_trades: int = 0
    matched: int = 0
    breaks: int = 0
    break_details: list[BreakRecord] = Field(default_factory=list)
    total_internal_volume: float = 0.0
    total_exchange_volume: float = 0.0
    volume_difference: float = 0.0
    total_fee_difference: float = 0.0
    settlement_summary: dict[str, int] = Field(default_factory=dict)
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    @property
    def match_rate(self) -> float:
        total = self.matched + self.breaks
        if total == 0:
            return 1.0
        return self.matched / total


class SettlementRecord(BaseModel):
    """Tracks settlement status for a single trade."""

    trade_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    venue: str = ""
    trade_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    settlement_type: str = "T+0"       # "T+0", "T+1", "T+2"
    settlement_due: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    status: SettlementStatus = SettlementStatus.UNSETTLED
    settled_at: datetime | None = None


# ═══════════════════════════════════════════
#  Tolerances
# ═══════════════════════════════════════════

# How much difference we accept before flagging a break.
_QTY_TOLERANCE_PCT = 0.0001     # 0.01% -- covers rounding
_PRICE_TOLERANCE_PCT = 0.0005   # 0.05% -- covers slight slippage variance
_FEE_TOLERANCE_PCT = 0.01       # 1% -- fee tiers/rebates can vary


# ═══════════════════════════════════════════
#  Reconciler
# ═══════════════════════════════════════════


class Reconciler:
    """
    Post-trade reconciliation engine.

    Compares internal trade records against exchange-reported fills.  Identifies
    breaks, generates daily reports, and tracks settlement status.

    Usage:
        reconciler = Reconciler()
        reconciler.add_internal_trades(our_fills)
        reconciler.add_exchange_trades(venue_fills)
        reconciler.match_trades()
        breaks = reconciler.find_breaks()
        report = reconciler.generate_report("2026-03-28")
    """

    def __init__(
        self,
        qty_tolerance_pct: float = _QTY_TOLERANCE_PCT,
        price_tolerance_pct: float = _PRICE_TOLERANCE_PCT,
        fee_tolerance_pct: float = _FEE_TOLERANCE_PCT,
    ) -> None:
        self._internal: list[ReconciliationEntry] = []
        self._exchange: list[ReconciliationEntry] = []
        self._matched_pairs: list[tuple[ReconciliationEntry, ReconciliationEntry]] = []
        self._breaks: list[BreakRecord] = []
        self._settlements: dict[str, SettlementRecord] = {}

        self._qty_tol = qty_tolerance_pct
        self._price_tol = price_tolerance_pct
        self._fee_tol = fee_tolerance_pct

    # ── Data ingestion ──

    def add_internal_trades(self, trades: list[ReconciliationEntry]) -> None:
        """Add internal (our system) trade records for reconciliation."""
        self._internal.extend(trades)
        logger.info("recon_internal_added", count=len(trades))

    def add_exchange_trades(self, trades: list[ReconciliationEntry]) -> None:
        """Add exchange-reported trade records for reconciliation."""
        self._exchange.extend(trades)
        logger.info("recon_exchange_added", count=len(trades))

    def clear(self) -> None:
        """Reset all loaded trades and results for a fresh reconciliation run."""
        self._internal.clear()
        self._exchange.clear()
        self._matched_pairs.clear()
        self._breaks.clear()

    # ── Matching ──

    def match_trades(self) -> int:
        """
        Match internal records against exchange records.

        Matching strategy (in priority order):
        1. Exact match on (exchange_id <-> exchange_id) if both populated.
        2. Fuzzy match on (symbol, side, timestamp within 60s, qty within tolerance).

        Returns the number of matched pairs.
        """
        self._matched_pairs.clear()
        self._breaks.clear()

        # Index exchange trades by exchange_id for fast lookup
        exchange_by_id: dict[str, ReconciliationEntry] = {}
        exchange_unmatched: list[ReconciliationEntry] = []

        for ex in self._exchange:
            if ex.exchange_id:
                exchange_by_id[ex.exchange_id] = ex
            else:
                exchange_unmatched.append(ex)

        internal_unmatched: list[ReconciliationEntry] = []

        # Pass 1: Exact ID match
        for internal in self._internal:
            if internal.exchange_id and internal.exchange_id in exchange_by_id:
                ex = exchange_by_id.pop(internal.exchange_id)
                self._compare_and_record(internal, ex)
            else:
                internal_unmatched.append(internal)

        # Remaining exchange entries go to unmatched pool
        exchange_unmatched.extend(exchange_by_id.values())

        # Pass 2: Fuzzy match on (symbol, side, time, qty)
        still_unmatched_exchange: list[ReconciliationEntry] = []

        for ex in exchange_unmatched:
            matched = False
            for i, internal in enumerate(internal_unmatched):
                if self._fuzzy_match(internal, ex):
                    self._compare_and_record(internal, ex)
                    internal_unmatched.pop(i)
                    matched = True
                    break
            if not matched:
                still_unmatched_exchange.append(ex)

        # Record missing-internal breaks (exchange has it, we don't)
        for ex in still_unmatched_exchange:
            ex.status = ReconciliationStatus.BREAK_MISSING_INTERNAL
            ex.breaks.append("No matching internal record found")
            self._breaks.append(BreakRecord(
                exchange_entry=ex,
                break_types=["MISSING_INTERNAL"],
                severity="HIGH",
                details={
                    "exchange_id": ex.exchange_id,
                    "symbol": ex.symbol,
                    "qty": ex.quantity,
                    "price": ex.price,
                },
            ))

        # Record missing-exchange breaks (we have it, exchange doesn't)
        for internal in internal_unmatched:
            internal.status = ReconciliationStatus.BREAK_MISSING_EXCHANGE
            internal.breaks.append("No matching exchange record found")
            self._breaks.append(BreakRecord(
                internal_entry=internal,
                break_types=["MISSING_EXCHANGE"],
                severity="HIGH",
                details={
                    "internal_id": internal.internal_id,
                    "symbol": internal.symbol,
                    "qty": internal.quantity,
                    "price": internal.price,
                },
            ))

        matched_count = len(self._matched_pairs)
        break_count = len(self._breaks)

        logger.info(
            "recon_matching_complete",
            matched=matched_count,
            breaks=break_count,
            internal_total=len(self._internal),
            exchange_total=len(self._exchange),
        )
        return matched_count

    def find_breaks(self) -> list[BreakRecord]:
        """
        Return all detected breaks from the last match_trades() run.

        If match_trades() has not been called, calls it first.
        """
        if not self._matched_pairs and not self._breaks:
            self.match_trades()
        return list(self._breaks)

    # ── Reporting ──

    def generate_report(self, report_date: str = "") -> ReconReport:
        """
        Generate a daily reconciliation report.

        Parameters
        ----------
        report_date : str
            Date label for the report (YYYY-MM-DD).  Defaults to today.
        """
        if not report_date:
            report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Ensure matching has run
        if not self._matched_pairs and not self._breaks:
            self.match_trades()

        internal_volume = sum(e.quantity * e.price for e in self._internal)
        exchange_volume = sum(e.quantity * e.price for e in self._exchange)
        internal_fees = sum(e.fees for e in self._internal)
        exchange_fees = sum(e.fees for e in self._exchange)

        # Settlement summary
        settlement_counts: dict[str, int] = {}
        for sr in self._settlements.values():
            key = sr.status.value
            settlement_counts[key] = settlement_counts.get(key, 0) + 1

        report = ReconReport(
            report_date=report_date,
            total_internal_trades=len(self._internal),
            total_exchange_trades=len(self._exchange),
            matched=len(self._matched_pairs),
            breaks=len(self._breaks),
            break_details=list(self._breaks),
            total_internal_volume=round(internal_volume, 2),
            total_exchange_volume=round(exchange_volume, 2),
            volume_difference=round(abs(internal_volume - exchange_volume), 2),
            total_fee_difference=round(abs(internal_fees - exchange_fees), 4),
            settlement_summary=settlement_counts,
        )

        logger.info(
            "recon_report_generated",
            date=report_date,
            matched=report.matched,
            breaks=report.breaks,
            match_rate=f"{report.match_rate:.2%}",
            volume_diff=report.volume_difference,
        )
        return report

    # ── Settlement tracking ──

    def settlement_tracker(
        self,
        trade_id: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        venue: str = "",
        settlement_type: str = "T+0",
        trade_time: datetime | None = None,
    ) -> SettlementRecord:
        """
        Register a trade for settlement tracking.

        Parameters
        ----------
        settlement_type : str
            One of "T+0", "T+1", "T+2".  Determines the settlement_due timestamp.

        Returns the created SettlementRecord.
        """
        t = trade_time or datetime.now(timezone.utc)

        # Parse settlement offset
        offset_days = 0
        if settlement_type == "T+1":
            offset_days = 1
        elif settlement_type == "T+2":
            offset_days = 2

        due = t + timedelta(days=offset_days)

        record = SettlementRecord(
            trade_id=trade_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            venue=venue,
            trade_time=t,
            settlement_type=settlement_type,
            settlement_due=due,
            status=SettlementStatus.UNSETTLED,
        )
        self._settlements[trade_id] = record

        logger.info(
            "settlement_registered",
            trade_id=trade_id,
            symbol=symbol,
            type=settlement_type,
            due=due.isoformat(),
        )
        return record

    def mark_settled(self, trade_id: str) -> SettlementRecord | None:
        """Mark a trade as settled."""
        record = self._settlements.get(trade_id)
        if record is None:
            logger.warning("settlement_not_found", trade_id=trade_id)
            return None

        record.status = SettlementStatus.SETTLED
        record.settled_at = datetime.now(timezone.utc)
        logger.info("settlement_settled", trade_id=trade_id)
        return record

    def mark_failed(self, trade_id: str, reason: str = "") -> SettlementRecord | None:
        """Mark a trade settlement as failed."""
        record = self._settlements.get(trade_id)
        if record is None:
            return None

        record.status = SettlementStatus.FAILED
        logger.warning("settlement_failed", trade_id=trade_id, reason=reason)
        return record

    def get_unsettled(self) -> list[SettlementRecord]:
        """Return all unsettled trades, sorted by settlement_due (earliest first)."""
        result = [
            r for r in self._settlements.values()
            if r.status in (SettlementStatus.UNSETTLED, SettlementStatus.SETTLING)
        ]
        result.sort(key=lambda r: r.settlement_due)
        return result

    def get_overdue_settlements(self) -> list[SettlementRecord]:
        """Return trades that are past their settlement_due but not yet settled."""
        now = datetime.now(timezone.utc)
        return [
            r for r in self._settlements.values()
            if r.status in (SettlementStatus.UNSETTLED, SettlementStatus.SETTLING)
            and r.settlement_due <= now
        ]

    def get_settlement_summary(self) -> dict[str, Any]:
        """Aggregate settlement statistics."""
        total = len(self._settlements)
        settled = sum(
            1 for r in self._settlements.values()
            if r.status == SettlementStatus.SETTLED
        )
        failed = sum(
            1 for r in self._settlements.values()
            if r.status == SettlementStatus.FAILED
        )
        unsettled = self.get_unsettled()
        overdue = self.get_overdue_settlements()

        return {
            "total_trades": total,
            "settled": settled,
            "failed": failed,
            "pending": len(unsettled),
            "overdue": len(overdue),
            "settlement_rate": round(settled / total, 4) if total > 0 else 1.0,
        }

    # ── Internal helpers ──

    def _fuzzy_match(
        self,
        internal: ReconciliationEntry,
        exchange: ReconciliationEntry,
    ) -> bool:
        """
        Check whether two entries likely represent the same trade.

        Criteria:
        - Same symbol
        - Same side
        - Timestamps within 60 seconds
        - Quantities within tolerance
        """
        if internal.symbol != exchange.symbol:
            return False
        if internal.side != exchange.side:
            return False

        time_diff = abs(
            (internal.timestamp - exchange.timestamp).total_seconds()
        )
        if time_diff > 60:
            return False

        if internal.quantity == 0 and exchange.quantity == 0:
            return True
        if internal.quantity == 0 or exchange.quantity == 0:
            return False

        qty_diff = abs(internal.quantity - exchange.quantity) / max(
            internal.quantity, exchange.quantity
        )
        if qty_diff > self._qty_tol * 10:  # More lenient for fuzzy match
            return False

        return True

    def _compare_and_record(
        self,
        internal: ReconciliationEntry,
        exchange: ReconciliationEntry,
    ) -> None:
        """
        Compare a matched pair field by field and record any breaks.
        """
        break_types: list[str] = []
        details: dict[str, Any] = {}
        break_descriptions: list[str] = []

        # Quantity check
        if internal.quantity > 0:
            qty_diff_pct = (
                abs(internal.quantity - exchange.quantity) / internal.quantity
            )
            if qty_diff_pct > self._qty_tol:
                break_types.append("QTY")
                details["qty_internal"] = internal.quantity
                details["qty_exchange"] = exchange.quantity
                details["qty_diff_pct"] = round(qty_diff_pct * 100, 4)
                break_descriptions.append(
                    f"Qty mismatch: internal={internal.quantity} vs "
                    f"exchange={exchange.quantity} ({qty_diff_pct:.4%})"
                )

        # Price check
        if internal.price > 0:
            price_diff_pct = (
                abs(internal.price - exchange.price) / internal.price
            )
            if price_diff_pct > self._price_tol:
                break_types.append("PRICE")
                details["price_internal"] = internal.price
                details["price_exchange"] = exchange.price
                details["price_diff_pct"] = round(price_diff_pct * 100, 4)
                break_descriptions.append(
                    f"Price mismatch: internal={internal.price} vs "
                    f"exchange={exchange.price} ({price_diff_pct:.4%})"
                )

        # Fee check
        max_fee = max(internal.fees, exchange.fees, 0.0001)  # Avoid div by zero
        fee_diff_pct = abs(internal.fees - exchange.fees) / max_fee
        if fee_diff_pct > self._fee_tol and abs(internal.fees - exchange.fees) > 0.01:
            break_types.append("FEE")
            details["fee_internal"] = internal.fees
            details["fee_exchange"] = exchange.fees
            break_descriptions.append(
                f"Fee mismatch: internal={internal.fees} vs "
                f"exchange={exchange.fees}"
            )

        self._matched_pairs.append((internal, exchange))

        if break_types:
            # Determine status
            if len(break_types) > 1:
                status = ReconciliationStatus.BREAK_MULTIPLE
            elif "QTY" in break_types:
                status = ReconciliationStatus.BREAK_QTY
            elif "PRICE" in break_types:
                status = ReconciliationStatus.BREAK_PRICE
            else:
                status = ReconciliationStatus.BREAK_FEE

            internal.status = status
            exchange.status = status
            internal.breaks = break_descriptions
            exchange.breaks = break_descriptions

            # Severity: qty breaks are worse than price/fee breaks
            severity = "LOW"
            if "QTY" in break_types:
                severity = "HIGH"
            elif "PRICE" in break_types:
                severity = "MEDIUM"

            self._breaks.append(BreakRecord(
                internal_entry=internal,
                exchange_entry=exchange,
                break_types=break_types,
                severity=severity,
                details=details,
            ))

            logger.warning(
                "recon_break_detected",
                internal_id=internal.internal_id,
                exchange_id=exchange.exchange_id,
                types=break_types,
                severity=severity,
            )
        else:
            internal.status = ReconciliationStatus.MATCHED
            exchange.status = ReconciliationStatus.MATCHED
