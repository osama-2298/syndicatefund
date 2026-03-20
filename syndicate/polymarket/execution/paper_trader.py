"""Virtual USDC portfolio for paper trading weather bets."""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path

import structlog

from syndicate.polymarket.config import PolymarketSettings
from syndicate.polymarket.models import WeatherPortfolio, WeatherPosition

logger = structlog.get_logger()

# Spread/slippage simulation parameters for realistic paper trading
DEFAULT_HALF_SPREAD = 0.015   # 1.5% half-spread (bid-ask gap / 2)
DEFAULT_SLIPPAGE = 0.005      # 0.5% additional slippage on market orders


def simulate_fill_price(
    market_price: float,
    half_spread: float = DEFAULT_HALF_SPREAD,
    slippage: float = DEFAULT_SLIPPAGE,
) -> float:
    """Simulate a realistic fill price for a BUY order.

    A market mid-price of 0.40 with 1.5% half-spread means the ask is ~0.415.
    Add random slippage of 0-0.5% to model market impact.

    Returns the simulated fill price (always >= market_price).
    """
    ask_price = market_price + half_spread
    random_slip = random.uniform(0, slippage)
    fill = ask_price + random_slip
    return min(fill, 0.99)  # Can't pay more than 99c


class WeatherPaperTrader:
    """Paper trader for Polymarket weather markets.

    Manages a virtual USDC portfolio: place bets, resolve outcomes,
    and persist state to JSON between restarts.

    Includes spread/slippage simulation for realistic P&L tracking.
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
        """Return True if daily losses exceed limit_pct of bankroll.

        Checks P&L of positions resolved today.
        """
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
    ) -> WeatherPosition | None:
        """Place a paper bet with simulated spread/slippage.

        The fill price is worse than the mid-price by ~2% (spread + slippage).
        This makes paper trading realistic — real Polymarket fills are never at mid.

        Args:
            condition_id: Polymarket condition ID.
            token_id: Polymarket token ID for the specific bin.
            city: City name (e.g. "New York").
            date: Resolution date YYYY-MM-DD.
            bin_label: Human-readable bin label (e.g. "40-41F").
            entry_price: YES share mid-price at entry (0-1).
            quantity: USDC amount to spend.
            model_prob: Our model's probability for this bin.
            edge: model_prob - entry_price at time of entry.
            forecast_mean: Ensemble forecast mean (stored for calibration at resolution).
            forecast_std: Ensemble forecast std (stored for calibration at resolution).

        Returns:
            The created WeatherPosition, or None if blocked by safety rails.
        """
        if self.check_daily_loss_limit():
            logger.warning("paper_bet_blocked.daily_loss_limit", city=city, date=date)
            return None

        # Simulate realistic fill price (worse than mid by spread + slippage)
        fill_price = simulate_fill_price(entry_price)

        # Recheck edge after simulated fill — if fill eats the edge, skip
        effective_edge = model_prob - fill_price
        if effective_edge <= 0:
            logger.info(
                "paper_bet_skipped.edge_eaten_by_spread",
                city=city, date=date, bin=bin_label,
                mid=round(entry_price, 4), fill=round(fill_price, 4),
                model_prob=round(model_prob, 4),
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
            qty=round(quantity, 2),
            edge=round(effective_edge, 4),
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
        self._path.write_text(json.dumps(data, indent=2, default=str))
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
