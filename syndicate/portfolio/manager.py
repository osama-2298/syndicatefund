"""
Portfolio Managers — One per Market Segment.

Sits between the Risk Manager and Execution Engine in the pipeline.
Each PM manages a segment (L1s, DeFi, Memes, etc.) and makes the
final trade decisions for their sector.

The PM layer:
1. Receives risk-approved trade orders
2. Groups them by segment
3. Each PM reviews orders for their segment
4. PMs can approve, reject, or adjust sizing
5. Approved orders go to execution

For v1, PMs are deterministic (segment classification + allocation rules).
In v2, each PM can be an LLM agent with sector expertise.
"""

from __future__ import annotations

from typing import Any

import structlog

from syndicate.data.models import AggregatedSignal, PortfolioState, TradeOrder

logger = structlog.get_logger()

# Coin-to-segment mapping. In production, this comes from a data source.
SEGMENT_MAP: dict[str, str] = {
    # Layer 1s
    "BTCUSDT": "L1s",
    "ETHUSDT": "L1s",
    "SOLUSDT": "L1s",
    "AVAXUSDT": "L1s",
    "ADAUSDT": "L1s",
    "DOTUSDT": "L1s",
    "NEARUSDT": "L1s",
    "SUIUSDT": "L1s",
    "APTUSDT": "L1s",
    "ATOMUSDT": "L1s",
    "SEIUSDT": "L1s",
    # DeFi
    "UNIUSDT": "DeFi",
    "AAVEUSDT": "DeFi",
    "MKRUSDT": "DeFi",
    "LINKUSDT": "DeFi",
    "SNXUSDT": "DeFi",
    "CRVUSDT": "DeFi",
    "COMPUSDT": "DeFi",
    "PENDLEUSDT": "DeFi",
    # Layer 2s
    "OPUSDT": "L2s",
    "ARBUSDT": "L2s",
    "MATICUSDT": "L2s",
    "STRKUSDT": "L2s",
    # Memes
    "DOGEUSDT": "Memes",
    "SHIBUSDT": "Memes",
    "PEPEUSDT": "Memes",
    "FLOKIUSDT": "Memes",
    "BONKUSDT": "Memes",
    "WIFUSDT": "Memes",
    # AI / Infra
    "FETUSDT": "AI",
    "RENDERUSDT": "AI",
    "TAOUSDT": "AI",
    "FILUSDT": "Infra",
    "ARUSDT": "Infra",
}

# Default segment for unknown coins
DEFAULT_SEGMENT = "Other"

# Maximum allocation per segment as % of portfolio
SEGMENT_MAX_ALLOCATION: dict[str, float] = {
    "L1s": 0.40,     # Up to 40% in L1s
    "DeFi": 0.25,    # Up to 25% in DeFi (was 20 — DeFi has real revenue)
    "L2s": 0.20,     # Up to 20% in L2s (was 15)
    "Memes": 0.15,   # Up to 15% in Memes (was 10 — memes can 10x)
    "AI": 0.20,      # Up to 20% in AI (was 15 — fastest growing sector)
    "Infra": 0.15,   # Up to 15% in Infra (was 10)
    "Other": 0.15,   # Up to 15% in unknown (was 10 — new coins that don't fit categories)
}


def classify_segment(symbol: str) -> str:
    """Classify a coin into its market segment."""
    return SEGMENT_MAP.get(symbol, DEFAULT_SEGMENT)


class PortfolioManager:
    """
    A single PM responsible for one market segment.
    Reviews and approves/rejects trade orders for their sector.
    """

    def __init__(self, segment: str, max_allocation: float) -> None:
        self.segment = segment
        self.max_allocation = max_allocation

    def review_orders(
        self,
        orders: list[TradeOrder],
        portfolio: PortfolioState,
    ) -> list[TradeOrder]:
        """
        Review orders for this segment. Returns approved orders.
        May reduce sizing if segment would be over-allocated.
        """
        if not orders:
            return []

        total_value = max(portfolio.total_value, 1)
        max_segment_notional = total_value * self.max_allocation

        # Calculate current segment exposure
        current_exposure = sum(
            p.notional_value for p in portfolio.positions
            if classify_segment(p.symbol) == self.segment
        )

        remaining_allocation = max_segment_notional - current_exposure
        if remaining_allocation <= 0:
            logger.info(
                "pm_segment_full",
                segment=self.segment,
                current_pct=round(current_exposure / total_value * 100, 1),
                max_pct=round(self.max_allocation * 100, 1),
            )
            # Still allow orders that close existing positions (longs AND shorts)
            return [o for o in orders if portfolio.get_position(o.symbol) is not None]

        approved = []
        used = 0.0

        for order in orders:
            # Close orders always pass through
            if portfolio.get_position(order.symbol) is not None:
                approved.append(order)
                continue

            notional = order.notional_value
            if used + notional <= remaining_allocation:
                approved.append(order)
                used += notional
            else:
                # Reduce size to fit remaining allocation
                remaining = remaining_allocation - used
                if remaining > 0 and order.price > 0:
                    reduced_qty = remaining / order.price
                    if reduced_qty > 0:
                        reduced_order = TradeOrder(
                            symbol=order.symbol,
                            side=order.side,
                            quantity=reduced_qty,
                            price=order.price,
                            source_signal_id=order.source_signal_id,
                            params=order.params,
                        )
                        approved.append(reduced_order)
                        used += reduced_order.notional_value
                        logger.info(
                            "pm_order_reduced",
                            segment=self.segment,
                            symbol=order.symbol,
                            original_qty=round(order.quantity, 6),
                            reduced_qty=round(reduced_qty, 6),
                        )
                break  # No more room

        return approved


class PortfolioManagerGroup:
    """
    The PM layer — a group of PMs, one per segment.
    Routes trade orders to the appropriate PM for approval.
    """

    def __init__(self, ceo_sector_weights: dict[str, float] | None = None) -> None:
        self._managers: dict[str, PortfolioManager] = {}
        # Create a PM for each known segment, adjusted by CEO's sector weights
        for segment, base_alloc in SEGMENT_MAX_ALLOCATION.items():
            # CEO weight multiplies the base allocation
            # e.g., CEO says DeFi=1.5 → DeFi max goes from 20% to 30%
            # CEO says Memes=0.0 → Memes max goes to 0% (blocked)
            ceo_weight = 1.0
            if ceo_sector_weights:
                ceo_weight = ceo_sector_weights.get(segment, 1.0)
            adjusted_alloc = min(base_alloc * ceo_weight, 0.50)  # Cap at 50% per segment
            self._managers[segment] = PortfolioManager(segment, adjusted_alloc)

    def review(
        self,
        orders: list[TradeOrder],
        portfolio: PortfolioState,
    ) -> list[TradeOrder]:
        """
        Route orders to segment PMs and collect approved orders.
        """
        if not orders:
            return []

        # Group orders by segment
        by_segment: dict[str, list[TradeOrder]] = {}
        for order in orders:
            segment = classify_segment(order.symbol)
            by_segment.setdefault(segment, []).append(order)

        # Each PM reviews their orders
        approved = []
        for segment, segment_orders in by_segment.items():
            pm = self._managers.get(segment)
            if pm is None:
                # Create on-the-fly for unknown segments
                pm = PortfolioManager(segment, SEGMENT_MAX_ALLOCATION.get(segment, 0.10))
                self._managers[segment] = pm

            pm_approved = pm.review_orders(segment_orders, portfolio)
            approved.extend(pm_approved)

            if len(pm_approved) < len(segment_orders):
                rejected = len(segment_orders) - len(pm_approved)
                logger.info(
                    "pm_orders_filtered",
                    segment=segment,
                    submitted=len(segment_orders),
                    approved=len(pm_approved),
                    rejected=rejected,
                )

        return approved

    def get_segment_exposure(self, portfolio: PortfolioState) -> dict[str, float]:
        """Get current exposure per segment as % of portfolio."""
        total_value = max(portfolio.total_value, 1)
        exposure: dict[str, float] = {}

        for pos in portfolio.positions:
            segment = classify_segment(pos.symbol)
            exposure[segment] = exposure.get(segment, 0) + pos.notional_value

        return {seg: round(val / total_value * 100, 1) for seg, val in exposure.items()}
