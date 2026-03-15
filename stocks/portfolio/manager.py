"""
Stock Portfolio Managers — GICS 11 sectors with dynamic classification via Yahoo Finance.
"""

from __future__ import annotations

import structlog

from hivemind.data.models import PortfolioState, TradeOrder

logger = structlog.get_logger()

# GICS Sector max allocation as % of portfolio
GICS_MAX_ALLOCATION: dict[str, float] = {
    "Technology": 0.25,
    "Health Care": 0.15,
    "Financials": 0.15,
    "Consumer Discretionary": 0.12,
    "Communication Services": 0.12,
    "Industrials": 0.12,
    "Consumer Staples": 0.10,
    "Energy": 0.10,
    "Utilities": 0.08,
    "Real Estate": 0.08,
    "Materials": 0.08,
    "Other": 0.10,
}

# Cache for stock → sector mapping (populated dynamically)
_SECTOR_CACHE: dict[str, str] = {}


def classify_stock_sector(symbol: str) -> str:
    """Classify a stock into its GICS sector. Uses cache, falls back to Yahoo Finance."""
    if symbol in _SECTOR_CACHE:
        return _SECTOR_CACHE[symbol]

    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        sector = ticker.info.get("sector", "Other")
        _SECTOR_CACHE[symbol] = sector
        return sector
    except Exception:
        return "Other"


def preload_sectors(symbols: list[str], fundamentals_map: dict) -> None:
    """Pre-populate sector cache from fundamentals data already fetched."""
    for symbol in symbols:
        if symbol in _SECTOR_CACHE:
            continue
        fund = fundamentals_map.get(symbol)
        if fund and fund.gics_sector:
            _SECTOR_CACHE[symbol] = fund.gics_sector


class StockPortfolioManager:
    """A single PM responsible for one GICS sector."""

    def __init__(self, sector: str, max_allocation: float) -> None:
        self.sector = sector
        self.max_allocation = max_allocation

    def review_orders(self, orders: list[TradeOrder], portfolio: PortfolioState) -> list[TradeOrder]:
        if not orders:
            return []

        total_value = max(portfolio.total_value, 1)
        max_notional = total_value * self.max_allocation

        current_exposure = sum(
            p.notional_value for p in portfolio.positions
            if classify_stock_sector(p.symbol) == self.sector
        )

        remaining = max_notional - current_exposure
        if remaining <= 0:
            return [o for o in orders if o.side.value == "SELL"]

        approved = []
        used = 0.0
        for order in orders:
            if portfolio.get_position(order.symbol) is not None:
                approved.append(order)
                continue
            notional = order.notional_value
            if used + notional <= remaining:
                approved.append(order)
                used += notional
            else:
                leftover = remaining - used
                if leftover > 0 and order.price > 0:
                    reduced_qty = int(leftover / order.price)
                    if reduced_qty > 0:
                        reduced = TradeOrder(
                            symbol=order.symbol, side=order.side,
                            quantity=reduced_qty, price=order.price,
                            source_signal_id=order.source_signal_id,
                        )
                        approved.append(reduced)
                break
        return approved


class StockPortfolioManagerGroup:
    """Routes stock orders to GICS sector PMs."""

    def __init__(self, ceo_sector_weights: dict[str, float] | None = None) -> None:
        self._managers: dict[str, StockPortfolioManager] = {}
        for sector, base_alloc in GICS_MAX_ALLOCATION.items():
            ceo_weight = 1.0
            if ceo_sector_weights:
                ceo_weight = ceo_sector_weights.get(sector, 1.0)
            adjusted = min(base_alloc * ceo_weight, 0.35)  # Cap at 35%
            self._managers[sector] = StockPortfolioManager(sector, adjusted)

    def review(self, orders: list[TradeOrder], portfolio: PortfolioState) -> list[TradeOrder]:
        if not orders:
            return []

        by_sector: dict[str, list[TradeOrder]] = {}
        for order in orders:
            sector = classify_stock_sector(order.symbol)
            by_sector.setdefault(sector, []).append(order)

        approved = []
        for sector, sector_orders in by_sector.items():
            pm = self._managers.get(sector)
            if pm is None:
                pm = StockPortfolioManager(sector, GICS_MAX_ALLOCATION.get(sector, 0.10))
                self._managers[sector] = pm
            approved.extend(pm.review_orders(sector_orders, portfolio))
        return approved

    def get_sector_exposure(self, portfolio: PortfolioState) -> dict[str, float]:
        total_value = max(portfolio.total_value, 1)
        exposure: dict[str, float] = {}
        for pos in portfolio.positions:
            sector = classify_stock_sector(pos.symbol)
            exposure[sector] = exposure.get(sector, 0) + pos.notional_value
        return {s: round(v / total_value * 100, 1) for s, v in exposure.items()}
