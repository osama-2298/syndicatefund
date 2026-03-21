"""Virtual USDC portfolio for paper trading weather bets."""

from __future__ import annotations

import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path

import structlog

from syndicate.polymarket.config import PolymarketSettings
from syndicate.polymarket.models import WeatherPortfolio, WeatherPosition

logger = structlog.get_logger()


# ── Market Impact Model ────────────────────────────────────────────────────
#
# Polymarket weather markets are thin.  A typical bin has $50-500 of
# resting liquidity on each side.  The paper trader must simulate what
# would actually happen if we tried to fill a $200 order at a 1-cent
# mid-price — the answer is we'd walk the book and pay far more.
#
# We model this with a simple square-root market impact model:
#
#   impact = k * sqrt(order_usd / available_liquidity)
#
# where k is a scaling constant.  This is the standard model used by
# institutional equity desks (Almgren-Chriss), adapted for thin crypto
# prediction markets.
#
# The available liquidity at a given price is estimated from the market's
# total_volume.  Low-volume markets have less depth.


# Base half-spread in probability points (bid-ask gap / 2)
BASE_HALF_SPREAD = 0.01

# Market impact constant — probability points per sqrt(order/liquidity).
# Calibrated so that buying the entire resting book (order = liquidity)
# moves price by ~10 cents (10 percentage points).
# $50 order in $50 liq → +10c.  $10 in $50 → +4.5c.  $200 in $500 → +6.3c.
IMPACT_K = 0.10

# Estimated resting liquidity per side as fraction of total market volume
# Weather markets are thin; ~10% of total volume sits on each side of a bin
LIQUIDITY_FRACTION = 0.10

# Minimum estimated liquidity per bin (even zero-volume markets have MM bots)
# Polymarket weather bins typically have $50-200 of resting orders
MIN_BIN_LIQUIDITY = 50.0

# Maximum bet size as multiple of estimated bin liquidity
# Even with impact model, don't try to fill more than 2x the book
MAX_BET_TO_LIQUIDITY_RATIO = 2.0


def estimate_bin_liquidity(total_market_volume: float, n_bins: int = 10) -> float:
    """Estimate resting liquidity for one bin on one side.

    A market with $5,000 total volume and 10 bins has roughly
    $5,000 * 10% / 10 = $50 per bin per side.
    """
    per_bin = (total_market_volume * LIQUIDITY_FRACTION) / max(n_bins, 1)
    return max(per_bin, MIN_BIN_LIQUIDITY)


def simulate_fill_price(
    market_price: float,
    order_usd: float,
    bin_liquidity: float = MIN_BIN_LIQUIDITY,
) -> float:
    """Simulate a realistic fill price accounting for spread and market impact.

    Components:
      1. Half-spread: fixed cost of crossing bid-ask
      2. Market impact: sqrt(order_size / liquidity) — large orders move price
      3. Random noise: small uniform jitter for realism

    Returns the volume-weighted average fill price (always > market_price).
    """
    # 1. Half-spread
    spread_cost = BASE_HALF_SPREAD

    # 2. Market impact — square root model
    #    A $100 order against $50 liquidity: impact = 1.0 * sqrt(100/50) = 1.41
    #    which means price moves ~141% of the way through the book — very costly.
    #    A $10 order against $500 liquidity: impact = 1.0 * sqrt(10/500) = 0.14
    ratio = order_usd / max(bin_liquidity, 1.0)
    impact = IMPACT_K * math.sqrt(ratio)

    # Cap impact at 0.80 — beyond this the order is unfillable
    impact = min(impact, 0.80)

    # 3. Random noise (±0.5% for realism)
    noise = random.uniform(0, 0.005)

    fill = market_price + spread_cost + impact + noise

    # Can't pay more than 99c for a YES share
    return min(fill, 0.99)


def max_fillable_amount(
    market_price: float,
    bin_liquidity: float,
    max_acceptable_impact: float = 0.30,
) -> float:
    """Maximum USDC we can deploy before impact exceeds threshold.

    Solves: max_impact = k * sqrt(amount / liquidity)
    → amount = liquidity * (max_impact / k)^2

    With default params: $50 liquidity, 30% max impact
    → max amount = 50 * (0.30/1.0)^2 = $4.50

    This prevents us from placing orders that would walk the
    entire book and fill at 5-10x the mid-price.
    """
    max_amount = bin_liquidity * (max_acceptable_impact / IMPACT_K) ** 2
    return max(0.0, max_amount)


class WeatherPaperTrader:
    """Paper trader for Polymarket weather markets.

    Manages a virtual USDC portfolio: place bets, resolve outcomes,
    and persist state to JSON between restarts.

    Simulates realistic execution with:
    - Bid-ask spread
    - Square-root market impact (Almgren-Chriss style)
    - Liquidity-aware position sizing caps
    """

    def __init__(self, portfolio: WeatherPortfolio | None = None):
        settings = PolymarketSettings()
        self._path: Path = settings.polymarket_data_dir / "weather_portfolio.json"
        self._portfolio: WeatherPortfolio = portfolio or WeatherPortfolio(
            bankroll=settings.polymarket_bankroll,
            cash=settings.polymarket_bankroll,
        )

    # ── Betting ───────────────────────────────────────────────────────────

    def check_daily_loss_limit(self, limit_pct: float = 0.10) -> bool:
        """Return True if daily losses exceed limit_pct of bankroll."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily_pnl = sum(
            p.pnl for p in self._portfolio.positions
            if p.resolved and hasattr(p, 'placed_at') and p.placed_at.strftime("%Y-%m-%d") == today
        )
        return daily_pnl < -(self._portfolio.bankroll * limit_pct)

    def recent_loss_streak(self) -> int:
        """Count consecutive losses from most recent resolved positions."""
        resolved = [p for p in self._portfolio.positions if p.resolved]
        resolved.sort(key=lambda p: p.placed_at, reverse=True)
        streak = 0
        for p in resolved:
            if p.outcome is False:
                streak += 1
            else:
                break
        return streak

    def place_bet(
        self,
        condition_id: str,
        token_id: str,
        city: str,
        date: str,
        bin_label: str,
        entry_price: float,
        quantity: float,
        model_prob: float,
        edge: float,
        forecast_mean: float = 0.0,
        forecast_std: float = 0.0,
        total_market_volume: float = 0.0,
        n_bins: int = 10,
    ) -> WeatherPosition | None:
        """Place a paper bet with realistic market impact simulation.

        The fill price accounts for spread AND market impact based on
        order size relative to estimated bin liquidity.  Large orders
        at low prices will get terrible fills or be rejected entirely.

        Args:
            condition_id: Polymarket condition ID.
            token_id: Polymarket token ID for the specific bin.
            city: City name (e.g. "New York").
            date: Resolution date YYYY-MM-DD.
            bin_label: Human-readable bin label (e.g. "40-41F").
            entry_price: YES share mid-price at entry (0-1).
            quantity: USDC amount to spend (from sizing engine).
            model_prob: Our model's probability for this bin.
            edge: model_prob - entry_price at time of entry.
            forecast_mean: Ensemble forecast mean (for calibration).
            forecast_std: Ensemble forecast std (for calibration).
            total_market_volume: Total market volume in USDC (for liquidity estimate).
            n_bins: Number of bins in this market (for liquidity estimate).

        Returns:
            The created WeatherPosition, or None if blocked.
        """
        if self.check_daily_loss_limit():
            logger.warning("paper_bet_blocked.daily_loss_limit", city=city, date=date)
            return None

        # Estimate liquidity for this bin
        bin_liq = estimate_bin_liquidity(total_market_volume, n_bins)

        # Cap order size by what the book can realistically absorb
        max_fill = max_fillable_amount(entry_price, bin_liq)
        if quantity > max_fill and max_fill > 0:
            logger.info(
                "paper_bet_reduced.liquidity_cap",
                city=city, date=date, bin=bin_label,
                original=round(quantity, 2),
                capped=round(max_fill, 2),
                bin_liquidity=round(bin_liq, 2),
            )
            quantity = max_fill

        if quantity < 1.0:
            logger.info(
                "paper_bet_skipped.too_small_after_liquidity_cap",
                city=city, date=date, bin=bin_label,
                amount=round(quantity, 2),
                bin_liquidity=round(bin_liq, 2),
            )
            return None

        # Simulate fill price with market impact
        fill_price = simulate_fill_price(entry_price, quantity, bin_liq)

        # Recheck edge after impact — if fill eats the edge, skip
        effective_edge = model_prob - fill_price
        if effective_edge <= 0:
            logger.info(
                "paper_bet_skipped.edge_eaten_by_impact",
                city=city, date=date, bin=bin_label,
                mid=round(entry_price, 4), fill=round(fill_price, 4),
                model_prob=round(model_prob, 4),
                impact=round(fill_price - entry_price, 4),
            )
            return None

        position = WeatherPosition(
            condition_id=condition_id,
            token_id=token_id,
            city=city,
            date=date,
            bin_label=bin_label,
            entry_price=entry_price,
            fill_price=fill_price,
            quantity=quantity,
            model_prob=model_prob,
            edge_at_entry=effective_edge,
            forecast_mean=forecast_mean,
            forecast_std=forecast_std,
            placed_at=datetime.now(timezone.utc),
        )

        self._portfolio.cash -= quantity
        self._portfolio.positions.append(position)
        self._portfolio.total_bets += 1

        logger.info(
            "paper_bet_placed",
            city=city,
            date=date,
            bin=bin_label,
            mid_price=round(entry_price, 4),
            fill_price=round(fill_price, 4),
            impact=round(fill_price - entry_price, 4),
            qty=round(quantity, 2),
            edge=round(effective_edge, 4),
            bin_liquidity=round(bin_liq, 2),
            cash_remaining=round(self._portfolio.cash, 2),
        )

        self.save()
        return position

    # ── Resolution ────────────────────────────────────────────────────────

    def resolve_position(self, condition_id: str, won: bool) -> float:
        """Resolve a position and compute P&L using simulated fill price.

        If won: each YES share pays $1. Shares = quantity / fill_price.
                Payout = quantity / fill_price. PnL = payout - quantity.
        If lost: payout = 0. PnL = -quantity (already deducted at entry).

        Uses fill_price (not mid entry_price) for realistic P&L.
        """
        for pos in self._portfolio.positions:
            if pos.condition_id == condition_id and not pos.resolved:
                pos.resolved = True
                pos.outcome = won

                # Use fill_price for P&L — this is the realistic execution price
                price = pos.fill_price if pos.fill_price > 0 else pos.entry_price

                if won:
                    payout = pos.quantity / price
                    pnl = payout - pos.quantity
                    self._portfolio.cash += payout
                    self._portfolio.wins += 1
                else:
                    pnl = -pos.quantity
                    self._portfolio.losses += 1

                pos.pnl = pnl
                self._portfolio.total_pnl += pnl

                logger.info(
                    "position_resolved",
                    condition_id=condition_id,
                    city=pos.city,
                    date=pos.date,
                    won=won,
                    fill_price=round(price, 4),
                    pnl=round(pnl, 2),
                    total_pnl=round(self._portfolio.total_pnl, 2),
                )

                self.save()
                return pnl

        logger.warning("resolve_position.not_found", condition_id=condition_id)
        return 0.0

    # ── Portfolio Access ──────────────────────────────────────────────────

    def get_portfolio(self) -> WeatherPortfolio:
        """Return the current portfolio state."""
        return self._portfolio

    # ── Persistence ───────────────────────────────────────────────────────

    def save(self) -> None:
        """Persist portfolio to JSON."""
        data = self._portfolio.model_dump(mode="json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str))
        tmp.rename(self._path)
        logger.debug("portfolio_saved", path=str(self._path))

    @classmethod
    def load(cls) -> WeatherPaperTrader:
        """Load portfolio from JSON, or create a fresh one."""
        settings = PolymarketSettings()
        path = settings.polymarket_data_dir / "weather_portfolio.json"

        if path.exists():
            try:
                raw = json.loads(path.read_text())
                portfolio = WeatherPortfolio.model_validate(raw)
                logger.info(
                    "portfolio_loaded",
                    path=str(path),
                    cash=round(portfolio.cash, 2),
                    positions=len(portfolio.positions),
                    total_pnl=round(portfolio.total_pnl, 2),
                )
                return cls(portfolio=portfolio)
            except Exception as exc:
                logger.error("portfolio_load_failed", path=str(path), error=str(exc))

        logger.info("portfolio_created_fresh", bankroll=settings.polymarket_bankroll)
        return cls()
