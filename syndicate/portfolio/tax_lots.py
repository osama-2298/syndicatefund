"""
Tax Lot Tracker — FIFO/LIFO/SpecID Cost Basis & Tax Loss Harvesting.

Tracks individual purchase lots for accurate cost basis accounting,
wash sale detection, and tax-efficient selling.

Key concepts:
- Each purchase creates a new TaxLot with its own cost basis
- Selling depletes lots using a configurable method (FIFO, LIFO, etc.)
- Wash sale rule: cannot claim a loss if the same security is repurchased
  within 30 days before or after the sale
- Long-term: held > 365 days (lower tax rate)
- Short-term: held <= 365 days (taxed as ordinary income)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import numpy as np
from pydantic import BaseModel, Field

from syndicate.data.models import OrderSide


# ═══════════════════════════════════════════
#  Models
# ═══════════════════════════════════════════


class LotSelectionMethod(str, Enum):
    """Method for selecting which lots to sell."""
    FIFO = "FIFO"          # First In, First Out
    LIFO = "LIFO"          # Last In, First Out
    HIFO = "HIFO"          # Highest Cost, First Out (minimizes gains)
    SPECIFIC = "SPECIFIC"  # Specific lot identification


class TaxLot(BaseModel):
    """A single purchase lot with cost basis tracking."""
    lot_id: str
    symbol: str
    purchase_date: datetime
    quantity: float  # remaining quantity (decreases as lots are sold)
    original_quantity: float  # quantity at purchase
    cost_basis_per_unit: float  # price paid per unit
    current_price: float = 0.0

    @property
    def cost_basis_total(self) -> float:
        """Total cost basis for remaining quantity."""
        return self.quantity * self.cost_basis_per_unit

    @property
    def current_value(self) -> float:
        """Current market value of remaining quantity."""
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        """Unrealized profit/loss."""
        return self.current_value - self.cost_basis_total

    @property
    def unrealized_pnl_pct(self) -> float:
        """Unrealized P&L as percentage of cost basis."""
        if self.cost_basis_total == 0:
            return 0.0
        return self.unrealized_pnl / self.cost_basis_total

    @property
    def holding_period_days(self) -> int:
        """Days held since purchase."""
        now = datetime.now(timezone.utc)
        return (now - self.purchase_date).days

    @property
    def is_long_term(self) -> bool:
        """True if held more than 365 days (qualifies for long-term capital gains)."""
        return self.holding_period_days > 365

    @property
    def holding_period(self) -> str:
        """Human-readable holding period."""
        days = self.holding_period_days
        if days > 365:
            return f"{days // 365}y {days % 365}d (long-term)"
        return f"{days}d (short-term)"


class SaleRecord(BaseModel):
    """Record of a lot sale for tax reporting."""
    lot_id: str
    symbol: str
    purchase_date: datetime
    sale_date: datetime
    quantity_sold: float
    cost_basis_per_unit: float
    sale_price: float
    realized_pnl: float
    realized_pnl_pct: float
    is_long_term: bool
    is_wash_sale: bool = False
    disallowed_loss: float = 0.0  # wash sale disallowed amount


class TaxHarvestOpportunity(BaseModel):
    """An identified tax loss harvesting opportunity."""
    symbol: str
    lot_id: str
    unrealized_loss: float
    loss_pct: float
    holding_period_days: int
    is_long_term: bool
    quantity: float
    cost_basis: float
    current_value: float
    wash_sale_risk: bool  # True if same symbol was bought in last 30 days
    estimated_tax_savings: float  # at assumed tax rate


class TaxReport(BaseModel):
    """Annual tax summary."""
    year: int
    total_short_term_gains: float = 0.0
    total_short_term_losses: float = 0.0
    net_short_term: float = 0.0
    total_long_term_gains: float = 0.0
    total_long_term_losses: float = 0.0
    net_long_term: float = 0.0
    total_wash_sale_disallowed: float = 0.0
    net_realized_pnl: float = 0.0
    num_transactions: int = 0
    sales: list[SaleRecord] = Field(default_factory=list)
    unrealized_gains: float = 0.0
    unrealized_losses: float = 0.0


# ═══════════════════════════════════════════
#  Tax Lot Tracker
# ═══════════════════════════════════════════


class TaxLotTracker:
    """
    Tracks tax lots across all positions for cost basis accounting
    and tax-efficient order execution.
    """

    def __init__(
        self,
        short_term_rate: float = 0.37,  # Federal short-term (ordinary income)
        long_term_rate: float = 0.20,   # Federal long-term capital gains
    ) -> None:
        self._lots: dict[str, list[TaxLot]] = {}  # symbol -> list of lots
        self._sales: list[SaleRecord] = []
        self._lot_counter: int = 0
        self.short_term_rate = short_term_rate
        self.long_term_rate = long_term_rate

    def _next_lot_id(self) -> str:
        self._lot_counter += 1
        return f"LOT-{self._lot_counter:06d}"

    # ── Add Lot ─────────────────────────────

    def add_lot(
        self,
        symbol: str,
        quantity: float,
        price: float,
        purchase_date: datetime | None = None,
    ) -> TaxLot:
        """
        Record a new purchase as a tax lot.

        Args:
            symbol: The ticker symbol.
            quantity: Number of units purchased.
            price: Price per unit at purchase.
            purchase_date: When the purchase occurred (defaults to now).

        Returns:
            The newly created TaxLot.
        """
        lot = TaxLot(
            lot_id=self._next_lot_id(),
            symbol=symbol,
            purchase_date=purchase_date or datetime.now(timezone.utc),
            quantity=quantity,
            original_quantity=quantity,
            cost_basis_per_unit=price,
            current_price=price,
        )

        if symbol not in self._lots:
            self._lots[symbol] = []
        self._lots[symbol].append(lot)
        return lot

    # ── Update Prices ───────────────────────

    def update_prices(self, price_map: dict[str, float]) -> None:
        """Update current prices on all lots."""
        for symbol, lots in self._lots.items():
            if symbol in price_map:
                for lot in lots:
                    lot.current_price = price_map[symbol]

    # ── Sell Lots ───────────────────────────

    def sell_lots(
        self,
        symbol: str,
        quantity: float,
        sale_price: float,
        method: LotSelectionMethod = LotSelectionMethod.FIFO,
        specific_lot_ids: list[str] | None = None,
        sale_date: datetime | None = None,
    ) -> list[SaleRecord]:
        """
        Sell a quantity using the specified lot selection method.

        Depletes lots according to the method until the requested quantity
        is fulfilled. Returns SaleRecord for each lot (or partial lot) sold.

        Args:
            symbol: Symbol to sell.
            quantity: Total quantity to sell.
            sale_price: Price per unit at sale.
            method: FIFO, LIFO, HIFO, or SPECIFIC.
            specific_lot_ids: Required if method is SPECIFIC.
            sale_date: When the sale occurred (defaults to now).

        Returns:
            List of SaleRecord, one per lot depleted.
        """
        now = sale_date or datetime.now(timezone.utc)
        lots = self._lots.get(symbol, [])
        active_lots = [l for l in lots if l.quantity > 0]

        if not active_lots:
            return []

        # Sort lots according to method
        if method == LotSelectionMethod.FIFO:
            active_lots.sort(key=lambda l: l.purchase_date)
        elif method == LotSelectionMethod.LIFO:
            active_lots.sort(key=lambda l: l.purchase_date, reverse=True)
        elif method == LotSelectionMethod.HIFO:
            active_lots.sort(key=lambda l: l.cost_basis_per_unit, reverse=True)
        elif method == LotSelectionMethod.SPECIFIC:
            if specific_lot_ids is None:
                raise ValueError("specific_lot_ids required for SPECIFIC method")
            id_set = set(specific_lot_ids)
            active_lots = [l for l in active_lots if l.lot_id in id_set]

        remaining = quantity
        records: list[SaleRecord] = []

        for lot in active_lots:
            if remaining <= 0:
                break

            sell_qty = min(lot.quantity, remaining)
            cost_basis = sell_qty * lot.cost_basis_per_unit
            proceeds = sell_qty * sale_price
            realized_pnl = proceeds - cost_basis
            realized_pnl_pct = realized_pnl / cost_basis if cost_basis > 0 else 0.0

            # Check holding period at time of sale
            holding_days = (now - lot.purchase_date).days
            is_lt = holding_days > 365

            # Check wash sale
            is_wash = self._check_wash_sale_for_lot(symbol, lot, now)
            disallowed = abs(realized_pnl) if is_wash and realized_pnl < 0 else 0.0

            record = SaleRecord(
                lot_id=lot.lot_id,
                symbol=symbol,
                purchase_date=lot.purchase_date,
                sale_date=now,
                quantity_sold=round(sell_qty, 8),
                cost_basis_per_unit=lot.cost_basis_per_unit,
                sale_price=sale_price,
                realized_pnl=round(realized_pnl, 2),
                realized_pnl_pct=round(realized_pnl_pct, 4),
                is_long_term=is_lt,
                is_wash_sale=is_wash,
                disallowed_loss=round(disallowed, 2),
            )
            records.append(record)
            self._sales.append(record)

            # Deplete the lot
            lot.quantity = round(lot.quantity - sell_qty, 8)
            remaining -= sell_qty

        return records

    # ── Unrealized Gains ────────────────────

    def get_unrealized_gains(
        self,
        symbol: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get unrealized gains/losses by lot.

        Args:
            symbol: Filter to a specific symbol. If None, returns all.

        Returns:
            List of dicts with lot details and unrealized P&L.
        """
        results = []
        symbols = [symbol] if symbol else list(self._lots.keys())

        for sym in symbols:
            for lot in self._lots.get(sym, []):
                if lot.quantity <= 0:
                    continue
                results.append({
                    "lot_id": lot.lot_id,
                    "symbol": lot.symbol,
                    "quantity": lot.quantity,
                    "cost_basis_per_unit": lot.cost_basis_per_unit,
                    "current_price": lot.current_price,
                    "cost_basis_total": round(lot.cost_basis_total, 2),
                    "current_value": round(lot.current_value, 2),
                    "unrealized_pnl": round(lot.unrealized_pnl, 2),
                    "unrealized_pnl_pct": round(lot.unrealized_pnl_pct, 4),
                    "holding_period": lot.holding_period,
                    "is_long_term": lot.is_long_term,
                })

        # Sort by unrealized P&L ascending (biggest losses first)
        results.sort(key=lambda r: r["unrealized_pnl"])
        return results

    # ── Tax Loss Harvesting ─────────────────

    def harvest_losses(
        self,
        min_loss_pct: float = 0.05,
        min_loss_usd: float = 100.0,
    ) -> list[TaxHarvestOpportunity]:
        """
        Identify tax loss harvesting opportunities across all positions.

        Scans all lots for unrealized losses that exceed the minimum thresholds.
        Flags wash sale risk if the same symbol was purchased in the last 30 days.

        Args:
            min_loss_pct: Minimum loss percentage to consider (default 5%).
            min_loss_usd: Minimum dollar loss to consider (default $100).

        Returns:
            List of TaxHarvestOpportunity sorted by loss magnitude.
        """
        opportunities: list[TaxHarvestOpportunity] = []
        now = datetime.now(timezone.utc)

        for symbol, lots in self._lots.items():
            for lot in lots:
                if lot.quantity <= 0:
                    continue
                if lot.unrealized_pnl >= 0:
                    continue  # No loss to harvest

                loss = abs(lot.unrealized_pnl)
                loss_pct = abs(lot.unrealized_pnl_pct)

                if loss_pct < min_loss_pct or loss < min_loss_usd:
                    continue

                # Check wash sale risk: was same symbol bought in last 30 days?
                wash_risk = self._has_recent_purchase(symbol, now, days=30)

                # Estimated tax savings
                rate = self.long_term_rate if lot.is_long_term else self.short_term_rate
                tax_savings = loss * rate

                opportunities.append(TaxHarvestOpportunity(
                    symbol=symbol,
                    lot_id=lot.lot_id,
                    unrealized_loss=round(-loss, 2),
                    loss_pct=round(-loss_pct, 4),
                    holding_period_days=lot.holding_period_days,
                    is_long_term=lot.is_long_term,
                    quantity=lot.quantity,
                    cost_basis=round(lot.cost_basis_total, 2),
                    current_value=round(lot.current_value, 2),
                    wash_sale_risk=wash_risk,
                    estimated_tax_savings=round(tax_savings, 2),
                ))

        # Sort by absolute loss descending (biggest opportunities first)
        opportunities.sort(key=lambda o: o.unrealized_loss)
        return opportunities

    # ── Wash Sale Detection ─────────────────

    def wash_sale_check(
        self,
        symbol: str,
        sale_date: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Check if selling a symbol would trigger a wash sale.

        The IRS wash sale rule: if you sell a security at a loss and buy
        the same (or substantially identical) security within 30 days
        before or after the sale, the loss is disallowed.

        Args:
            symbol: Symbol to check.
            sale_date: Proposed sale date (defaults to now).

        Returns:
            Dict with wash sale analysis.
        """
        now = sale_date or datetime.now(timezone.utc)
        window_start = now - timedelta(days=30)
        window_end = now + timedelta(days=30)

        # Check purchases within the 61-day window (30 before, sale day, 30 after)
        lots = self._lots.get(symbol, [])
        triggering_lots: list[dict[str, Any]] = []

        for lot in lots:
            if lot.quantity <= 0:
                continue
            if window_start <= lot.purchase_date <= window_end:
                # This lot was purchased within the wash sale window
                if lot.purchase_date != now:  # Don't flag the lot being sold
                    triggering_lots.append({
                        "lot_id": lot.lot_id,
                        "purchase_date": lot.purchase_date.isoformat(),
                        "quantity": lot.quantity,
                        "cost_basis": lot.cost_basis_per_unit,
                        "days_from_sale": (lot.purchase_date - now).days,
                    })

        # Also check recent sales that were repurchased
        recent_sales = [
            s for s in self._sales
            if s.symbol == symbol
            and window_start <= s.sale_date <= window_end
            and s.realized_pnl < 0
        ]

        is_wash_sale = len(triggering_lots) > 0
        total_at_risk = sum(
            t["quantity"] * t["cost_basis"] for t in triggering_lots
        )

        return {
            "symbol": symbol,
            "is_wash_sale": is_wash_sale,
            "triggering_purchases": triggering_lots,
            "num_triggering_lots": len(triggering_lots),
            "total_notional_at_risk": round(total_at_risk, 2),
            "recent_loss_sales": len(recent_sales),
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "recommendation": (
                "AVOID SALE — wash sale would disallow loss deduction"
                if is_wash_sale
                else "CLEAR — no wash sale conflict"
            ),
        }

    # ── Tax Report ──────────────────────────

    def generate_tax_report(self, year: int) -> TaxReport:
        """
        Generate annual tax summary with short-term vs long-term breakdown.

        Args:
            year: Tax year to report on.

        Returns:
            TaxReport with full realized and unrealized summary.
        """
        year_sales = [
            s for s in self._sales
            if s.sale_date.year == year
        ]

        st_gains = 0.0
        st_losses = 0.0
        lt_gains = 0.0
        lt_losses = 0.0
        wash_disallowed = 0.0

        for sale in year_sales:
            adjusted_pnl = sale.realized_pnl
            if sale.is_wash_sale:
                wash_disallowed += sale.disallowed_loss
                # Wash sale losses are disallowed
                if adjusted_pnl < 0:
                    adjusted_pnl = 0.0

            if sale.is_long_term:
                if adjusted_pnl >= 0:
                    lt_gains += adjusted_pnl
                else:
                    lt_losses += adjusted_pnl
            else:
                if adjusted_pnl >= 0:
                    st_gains += adjusted_pnl
                else:
                    st_losses += adjusted_pnl

        # Unrealized summary across all active lots
        unrealized_gains = 0.0
        unrealized_losses = 0.0
        for lots in self._lots.values():
            for lot in lots:
                if lot.quantity <= 0:
                    continue
                pnl = lot.unrealized_pnl
                if pnl >= 0:
                    unrealized_gains += pnl
                else:
                    unrealized_losses += pnl

        net_st = st_gains + st_losses
        net_lt = lt_gains + lt_losses

        return TaxReport(
            year=year,
            total_short_term_gains=round(st_gains, 2),
            total_short_term_losses=round(st_losses, 2),
            net_short_term=round(net_st, 2),
            total_long_term_gains=round(lt_gains, 2),
            total_long_term_losses=round(lt_losses, 2),
            net_long_term=round(net_lt, 2),
            total_wash_sale_disallowed=round(wash_disallowed, 2),
            net_realized_pnl=round(net_st + net_lt, 2),
            num_transactions=len(year_sales),
            sales=year_sales,
            unrealized_gains=round(unrealized_gains, 2),
            unrealized_losses=round(unrealized_losses, 2),
        )

    # ── Internal Helpers ────────────────────

    def _has_recent_purchase(
        self, symbol: str, reference_date: datetime, days: int = 30,
    ) -> bool:
        """Check if symbol was purchased within N days of reference date."""
        cutoff = reference_date - timedelta(days=days)
        for lot in self._lots.get(symbol, []):
            if lot.purchase_date >= cutoff and lot.purchase_date <= reference_date:
                # Exclude lots that are fully depleted (they were sold)
                if lot.original_quantity > 0:
                    return True
        return False

    def _check_wash_sale_for_lot(
        self, symbol: str, selling_lot: TaxLot, sale_date: datetime,
    ) -> bool:
        """Check if selling this specific lot triggers a wash sale."""
        # Only relevant if the sale would be at a loss
        pnl = (selling_lot.current_price - selling_lot.cost_basis_per_unit) * selling_lot.quantity
        if pnl >= 0:
            return False  # No loss, no wash sale issue

        window_start = sale_date - timedelta(days=30)
        window_end = sale_date + timedelta(days=30)

        for lot in self._lots.get(symbol, []):
            if lot.lot_id == selling_lot.lot_id:
                continue
            if lot.quantity <= 0:
                continue
            if window_start <= lot.purchase_date <= window_end:
                return True

        return False

    # ── Convenience ─────────────────────────

    def get_lots(self, symbol: str | None = None) -> list[TaxLot]:
        """Get all active lots, optionally filtered by symbol."""
        if symbol:
            return [l for l in self._lots.get(symbol, []) if l.quantity > 0]
        result = []
        for lots in self._lots.values():
            result.extend(l for l in lots if l.quantity > 0)
        return result

    def total_cost_basis(self, symbol: str | None = None) -> float:
        """Total cost basis across all active lots."""
        return sum(l.cost_basis_total for l in self.get_lots(symbol))

    def total_current_value(self, symbol: str | None = None) -> float:
        """Total current value across all active lots."""
        return sum(l.current_value for l in self.get_lots(symbol))
