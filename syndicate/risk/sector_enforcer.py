"""
Sector Exposure Enforcer.

Fixes the gap where ``max_sector_pct`` is defined in RiskLimits but never
actually checked before trade execution.

Provides:
  - check_sector_limits()   - verify all sectors within max_sector_pct
  - would_breach()          - pre-trade check: does this order cause a breach?
  - get_sector_exposures()  - current exposure breakdown by sector
  - enforce()               - hard gate that rejects breaching trades
  - generate_sector_report() - full report with traffic-light status

Sector mapping is aligned with the CEO's sector_weights:
  L1s, DeFi, L2s, Memes, AI, Infra, Exchange, Stablecoin, Other
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

import structlog
from pydantic import BaseModel, Field

from syndicate.data.models import OrderSide, PortfolioState, RiskLimits

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
#  Sector mapping
# ---------------------------------------------------------------------------

# Comprehensive symbol -> sector mapping for the crypto universe
# Aligned with the CEO agent's sector taxonomy: L1s, DeFi, L2s, Memes, AI, Infra
SYMBOL_SECTOR: dict[str, str] = {
    # L1s
    "BTCUSDT": "L1s",
    "ETHUSDT": "L1s",
    "SOLUSDT": "L1s",
    "ADAUSDT": "L1s",
    "AVAXUSDT": "L1s",
    "DOTUSDT": "L1s",
    "ATOMUSDT": "L1s",
    "NEARUSDT": "L1s",
    "APTUSDT": "L1s",
    "SUIUSDT": "L1s",
    "ALGOUSDT": "L1s",
    "ICPUSDT": "L1s",
    "HBARUSDT": "L1s",
    "XLMUSDT": "L1s",
    "LTCUSDT": "L1s",
    "XRPUSDT": "L1s",
    "TONUSDT": "L1s",
    "SEIUSDT": "L1s",
    "INJUSDT": "L1s",
    "TIAUSDT": "L1s",
    # DeFi
    "UNIUSDT": "DeFi",
    "LINKUSDT": "DeFi",
    "AAVEUSDT": "DeFi",
    "MKRUSDT": "DeFi",
    "COMPUSDT": "DeFi",
    "SNXUSDT": "DeFi",
    "CRVUSDT": "DeFi",
    "SUSHIUSDT": "DeFi",
    "1INCHUSDT": "DeFi",
    "LDOUSDT": "DeFi",
    "PENDLEUSDT": "DeFi",
    "JUPUSDT": "DeFi",
    "RAYUSDT": "DeFi",
    "JTEOUSDT": "DeFi",
    # L2s
    "MATICUSDT": "L2s",
    "OPUSDT": "L2s",
    "ARBUSDT": "L2s",
    "STRKUSDT": "L2s",
    "ZKUSDT": "L2s",
    "MANTAUSDT": "L2s",
    "IMXUSDT": "L2s",
    "METISUSDT": "L2s",
    # Memes
    "DOGEUSDT": "Memes",
    "SHIBUSDT": "Memes",
    "PEPEUSDT": "Memes",
    "BONKUSDT": "Memes",
    "WIFUSDT": "Memes",
    "FLOKIUSDT": "Memes",
    "TRUMPUSDT": "Memes",
    "NEIROUSDT": "Memes",
    "TURBOUSDT": "Memes",
    "MEMEUSDT": "Memes",
    "BOMEUSDT": "Memes",
    "PEOPLEUSDT": "Memes",
    "NOTUSDT": "Memes",
    # AI
    "FETUSDT": "AI",
    "AGIXUSDT": "AI",
    "OCEANUSDT": "AI",
    "RENDERUSDT": "AI",
    "TAOUSDT": "AI",
    "WLDUSDT": "AI",
    "ARKMUSDT": "AI",
    "AITUSDT": "AI",
    # Infra
    "FILUSDT": "Infra",
    "ARUSDT": "Infra",
    "GRTUSDT": "Infra",
    "THETAUSDT": "Infra",
    "STORJUSDT": "Infra",
    "RNDRFDUSD": "Infra",
    "AKTUSDT": "Infra",
    # Exchange
    "BNBUSDT": "Exchange",
    "FTMUSDT": "Exchange",
    "CAKEUSDT": "Exchange",
}

DEFAULT_SECTOR = "Other"


def classify_sector(symbol: str) -> str:
    """Return the sector for a given symbol. Falls back to 'Other'."""
    return SYMBOL_SECTOR.get(symbol, DEFAULT_SECTOR)


# ---------------------------------------------------------------------------
#  Enums & models
# ---------------------------------------------------------------------------


class TrafficLight(str, Enum):
    """Traffic-light status for sector exposure."""
    GREEN = "green"      # within limit, < 80% of max
    AMBER = "amber"      # between 80% and 100% of max
    RED = "red"          # at or above max


class SectorExposure(BaseModel):
    """Exposure summary for a single sector."""

    sector: str
    current_weight: float = 0.0      # fraction of portfolio (0-1)
    max_weight: float = 0.20         # from RiskLimits.max_sector_pct
    headroom: float = 0.0            # max_weight - current_weight
    breach: bool = False
    status: TrafficLight = TrafficLight.GREEN
    symbols: list[str] = Field(default_factory=list)
    notional_usd: float = 0.0


class SectorBreachResult(BaseModel):
    """Result of a would_breach() check."""

    would_breach: bool = False
    sector: str = ""
    current_weight: float = 0.0
    post_trade_weight: float = 0.0
    max_weight: float = 0.0
    message: str = "OK"


class SectorReport(BaseModel):
    """Full sector exposure report."""

    exposures: list[SectorExposure] = Field(default_factory=list)
    breaches: list[SectorExposure] = Field(default_factory=list)
    any_breach: bool = False
    portfolio_value: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
#  Sector Enforcer
# ---------------------------------------------------------------------------


class SectorEnforcer:
    """Enforce sector exposure limits defined in RiskLimits.max_sector_pct.

    Integrates with the CEO's sector_weights to provide dynamic overrides:
    when the CEO sets a sector to weight 0 (AVOID), the enforcer's max
    for that sector drops to 0.

    Usage:
        enforcer = SectorEnforcer(limits)
        report = enforcer.generate_sector_report(portfolio)
        breach = enforcer.would_breach("PEPEUSDT", 5000, portfolio)
        allowed, reason = enforcer.enforce("PEPEUSDT", 5000, portfolio)
    """

    def __init__(
        self,
        limits: RiskLimits | None = None,
        ceo_sector_weights: dict[str, float] | None = None,
    ) -> None:
        self.limits = limits or RiskLimits()
        self.ceo_sector_weights = ceo_sector_weights or {}

    def update_ceo_weights(self, weights: dict[str, float]) -> None:
        """Update sector weight overrides from the CEO directive."""
        self.ceo_sector_weights = weights
        logger.info("sector_weights_updated", weights=weights)

    # ------------------------------------------------------------------
    #  Core: get current exposures
    # ------------------------------------------------------------------

    def get_sector_exposures(self, portfolio: PortfolioState) -> dict[str, SectorExposure]:
        """Calculate current exposure for every sector with positions.

        Returns a dict keyed by sector name.
        """
        total_value = portfolio.total_value
        if total_value <= 0:
            return {}

        sector_notional: dict[str, float] = {}
        sector_symbols: dict[str, list[str]] = {}

        for pos in portfolio.positions:
            sector = classify_sector(pos.symbol)
            notional = abs(pos.notional_value)
            sector_notional[sector] = sector_notional.get(sector, 0.0) + notional
            sector_symbols.setdefault(sector, []).append(pos.symbol)

        result: dict[str, SectorExposure] = {}
        for sector, notional in sector_notional.items():
            weight = notional / total_value
            max_w = self._effective_max(sector)
            headroom = max(0.0, max_w - weight)
            breach = weight > max_w

            if breach:
                status = TrafficLight.RED
            elif weight >= max_w * 0.80:
                status = TrafficLight.AMBER
            else:
                status = TrafficLight.GREEN

            result[sector] = SectorExposure(
                sector=sector,
                current_weight=round(weight, 4),
                max_weight=round(max_w, 4),
                headroom=round(headroom, 4),
                breach=breach,
                status=status,
                symbols=sector_symbols.get(sector, []),
                notional_usd=round(notional, 2),
            )

        return result

    # ------------------------------------------------------------------
    #  Check all limits
    # ------------------------------------------------------------------

    def check_sector_limits(self, portfolio: PortfolioState) -> list[SectorExposure]:
        """Return list of sectors that are currently in breach."""
        exposures = self.get_sector_exposures(portfolio)
        breaches = [exp for exp in exposures.values() if exp.breach]

        if breaches:
            for b in breaches:
                logger.warning(
                    "sector_limit_breach",
                    sector=b.sector,
                    current_weight=round(b.current_weight * 100, 1),
                    max_weight=round(b.max_weight * 100, 1),
                    symbols=b.symbols,
                )
        return breaches

    # ------------------------------------------------------------------
    #  Pre-trade check
    # ------------------------------------------------------------------

    def would_breach(
        self,
        symbol: str,
        trade_notional_usd: float,
        portfolio: PortfolioState,
        side: OrderSide = OrderSide.BUY,
    ) -> SectorBreachResult:
        """Check whether a proposed trade would breach sector limits.

        For BUY orders, notional is added to the sector.
        For SELL orders (closing), notional is subtracted.
        """
        sector = classify_sector(symbol)
        total_value = portfolio.total_value
        if total_value <= 0:
            return SectorBreachResult(message="Portfolio value is zero")

        exposures = self.get_sector_exposures(portfolio)
        current_exp = exposures.get(sector)
        current_notional = current_exp.notional_usd if current_exp else 0.0
        current_weight = current_exp.current_weight if current_exp else 0.0

        if side == OrderSide.BUY:
            new_notional = current_notional + trade_notional_usd
        else:
            new_notional = max(0.0, current_notional - trade_notional_usd)

        # After the trade, portfolio value also changes (cash goes down/up)
        new_total = total_value  # approximate: ignore cash change for limit check
        post_weight = new_notional / new_total if new_total > 0 else 0.0
        max_w = self._effective_max(sector)

        if post_weight > max_w:
            return SectorBreachResult(
                would_breach=True,
                sector=sector,
                current_weight=round(current_weight, 4),
                post_trade_weight=round(post_weight, 4),
                max_weight=round(max_w, 4),
                message=(
                    f"Trade in {symbol} would push {sector} sector to "
                    f"{post_weight:.1%} (limit: {max_w:.1%}). "
                    f"Current: {current_weight:.1%}."
                ),
            )

        return SectorBreachResult(
            would_breach=False,
            sector=sector,
            current_weight=round(current_weight, 4),
            post_trade_weight=round(post_weight, 4),
            max_weight=round(max_w, 4),
            message="OK",
        )

    # ------------------------------------------------------------------
    #  Hard gate
    # ------------------------------------------------------------------

    def enforce(
        self,
        symbol: str,
        trade_notional_usd: float,
        portfolio: PortfolioState,
        side: OrderSide = OrderSide.BUY,
    ) -> tuple[bool, str]:
        """Reject trades that breach sector limits.

        Returns:
            (allowed, reason)
        """
        # Sells/closes are always allowed (they reduce exposure)
        if side == OrderSide.SELL:
            existing = portfolio.get_position(symbol)
            if existing is not None and existing.side == OrderSide.BUY:
                return True, "Closing position always allowed"

        result = self.would_breach(symbol, trade_notional_usd, portfolio, side)
        if result.would_breach:
            logger.warning(
                "sector_trade_rejected",
                symbol=symbol,
                sector=result.sector,
                post_weight=result.post_trade_weight,
                max_weight=result.max_weight,
            )
            return False, result.message

        return True, "OK"

    # ------------------------------------------------------------------
    #  Full report
    # ------------------------------------------------------------------

    def generate_sector_report(self, portfolio: PortfolioState) -> SectorReport:
        """Generate a comprehensive sector exposure report with traffic lights."""
        exposures = self.get_sector_exposures(portfolio)

        sorted_exposures = sorted(
            exposures.values(),
            key=lambda e: e.current_weight,
            reverse=True,
        )
        breaches = [e for e in sorted_exposures if e.breach]

        report = SectorReport(
            exposures=sorted_exposures,
            breaches=breaches,
            any_breach=len(breaches) > 0,
            portfolio_value=portfolio.total_value,
        )

        logger.info(
            "sector_report",
            n_sectors=len(sorted_exposures),
            n_breaches=len(breaches),
            sectors={e.sector: f"{e.current_weight:.1%}" for e in sorted_exposures},
        )
        return report

    # ------------------------------------------------------------------
    #  Helpers
    # ------------------------------------------------------------------

    def _effective_max(self, sector: str) -> float:
        """Effective max weight for a sector, considering CEO overrides.

        If the CEO sets a sector weight to 0 (AVOID), the max drops to 0.
        If the CEO underweights a sector (< 1.0), the max is scaled down
        proportionally. Overweighting does NOT increase the max above the
        CRO's hard limit.
        """
        base_max = self.limits.max_sector_pct  # e.g. 0.20

        ceo_weight = self.ceo_sector_weights.get(sector)
        if ceo_weight is None:
            return base_max

        if ceo_weight <= 0:
            # CEO says AVOID => max = 0
            return 0.0

        if ceo_weight < 1.0:
            # Underweight: scale down max proportionally
            return base_max * ceo_weight

        # Overweight: do NOT exceed the CRO's hard limit
        return base_max
