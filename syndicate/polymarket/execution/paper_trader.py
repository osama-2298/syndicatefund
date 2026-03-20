"""Virtual USDC portfolio for paper trading weather bets."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import structlog

from syndicate.polymarket.config import PolymarketSettings
from syndicate.polymarket.models import WeatherPortfolio, WeatherPosition

logger = structlog.get_logger()


class WeatherPaperTrader:
    """Paper trader for Polymarket weather markets.

    Manages a virtual USDC portfolio: place bets, resolve outcomes,
    and persist state to JSON between restarts.
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
    ) -> WeatherPosition | None:
        """Place a paper bet and deduct quantity from cash.

        Args:
            condition_id: Polymarket condition ID.
            token_id: Polymarket token ID for the specific bin.
            city: City name (e.g. "New York").
            date: Resolution date YYYY-MM-DD.
            bin_label: Human-readable bin label (e.g. "40-41F").
            entry_price: YES share price at entry (0-1).
            quantity: USDC amount to spend.
            model_prob: Our model's probability for this bin.
            edge: model_prob - entry_price at time of entry.

        Returns:
            The created WeatherPosition, or None if blocked by safety rails.
        """
        if self.check_daily_loss_limit():
            logger.warning("paper_bet_blocked.daily_loss_limit", city=city, date=date)
            return None

        position = WeatherPosition(
            condition_id=condition_id,
            token_id=token_id,
            city=city,
            date=date,
            bin_label=bin_label,
            entry_price=entry_price,
            quantity=quantity,
            model_prob=model_prob,
            edge_at_entry=edge,
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
            price=round(entry_price, 4),
            qty=round(quantity, 2),
            edge=round(edge, 4),
            cash_remaining=round(self._portfolio.cash, 2),
        )

        self.save()
        return position

    # ── Resolution ────────────────────────────────────────────────────────

    def resolve_position(self, condition_id: str, won: bool) -> float:
        """Resolve a position and compute P&L.

        If won: each YES share pays $1. Shares = quantity / entry_price.
                Payout = quantity / entry_price. PnL = payout - quantity.
        If lost: payout = 0. PnL = -quantity (already deducted at entry).

        Args:
            condition_id: Polymarket condition ID to resolve.
            won: Whether the position's outcome occurred.

        Returns:
            The realized P&L in USDC.
        """
        for pos in self._portfolio.positions:
            if pos.condition_id == condition_id and not pos.resolved:
                pos.resolved = True
                pos.outcome = won

                if won:
                    payout = pos.quantity / pos.entry_price
                    pnl = payout - pos.quantity
                    self._portfolio.cash += payout
                    self._portfolio.wins += 1
                else:
                    pnl = -pos.quantity
                    # Cash already deducted at entry; lost position pays nothing.
                    self._portfolio.losses += 1

                pos.pnl = pnl
                self._portfolio.total_pnl += pnl

                logger.info(
                    "position_resolved",
                    condition_id=condition_id,
                    city=pos.city,
                    date=pos.date,
                    won=won,
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
