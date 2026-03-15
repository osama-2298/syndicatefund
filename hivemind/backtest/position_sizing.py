"""
Adaptive position sizing strategies for the backtester.

Three modes:
  1. Fixed Fraction — risk a fixed % of portfolio per trade (current default)
  2. Kelly Criterion — data-driven optimal sizing from rolling trade history
  3. Volatility Targeting — size to target a specific portfolio volatility

Plus an "adaptive" mode that takes the conservative intersection (minimum) of
Kelly and vol-target sizing.

References:
  - Kelly (1956): "A New Interpretation of Information Rate"
  - Zarattini et al. (2025): 25% target vol for crypto trend-following
  - Thorp (2006): quarter-Kelly gives ~51% of profit with ~9% of variance
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from enum import Enum


class SizingMode(str, Enum):
    """Position sizing strategy."""

    FIXED = "fixed"
    KELLY = "kelly"
    VOL_TARGET = "vol_target"
    ADAPTIVE = "adaptive"  # min(kelly, vol_target)


@dataclass
class TradeRecord:
    """A single closed trade result for the rolling window."""

    win: bool
    pnl_pct: float  # e.g. 0.05 for +5%, -0.03 for -3%


@dataclass
class PositionSizer:
    """Adaptive position sizer that tracks trade history and computes optimal sizing.

    Usage:
        sizer = PositionSizer(mode=SizingMode.ADAPTIVE)

        # On each trade close:
        sizer.record_trade(win=True, pnl_pct=0.05)

        # Before each new entry:
        fraction = sizer.compute_position_fraction(
            portfolio_value=100_000,
            current_vol=0.60,
            price=50_000,
        )
    """

    mode: SizingMode = SizingMode.FIXED

    # Fixed fraction parameters
    fixed_fraction: float = 0.02  # 2% of portfolio per trade

    # Kelly parameters
    kelly_window: int = 30  # rolling window of trades
    kelly_min_trades: int = 20  # minimum trades before Kelly kicks in
    kelly_fraction_multiplier: float = 0.25  # quarter-Kelly for safety
    kelly_max_fraction: float = 0.05  # cap at 5% of portfolio

    # Volatility targeting parameters
    target_annual_vol: float = 0.25  # 25% annualized (Zarattini 2025)

    # Trade history (rolling buffer)
    trade_history: deque[TradeRecord] = field(default_factory=lambda: deque(maxlen=30))

    def __post_init__(self) -> None:
        # Ensure deque has correct maxlen matching kelly_window
        if not isinstance(self.trade_history, deque) or self.trade_history.maxlen != self.kelly_window:
            self.trade_history = deque(self.trade_history, maxlen=self.kelly_window)

    def record_trade(self, win: bool, pnl_pct: float) -> None:
        """Record a closed trade into the rolling buffer.

        Args:
            win: Whether the trade was profitable.
            pnl_pct: P&L as a decimal fraction (e.g. 0.05 for +5%).
        """
        self.trade_history.append(TradeRecord(win=win, pnl_pct=pnl_pct))

    # ------------------------------------------------------------------
    # Core sizing functions
    # ------------------------------------------------------------------

    def compute_position_fraction(
        self,
        portfolio_value: float = 0.0,
        current_vol: float = 0.0,
        price: float = 0.0,
    ) -> float:
        """Compute the fraction of portfolio to risk on the next trade.

        Returns a value between 0.0 and kelly_max_fraction (default 5%).
        This is the percentage of portfolio value to allocate as the position's
        risk budget (not the full notional — the risk manager converts this
        to notional via stop distance).

        Args:
            portfolio_value: Current total portfolio value (needed for vol_target).
            current_vol: Asset's annualized volatility (needed for vol_target).
            price: Current asset price (needed for vol_target).

        Returns:
            Position fraction as a decimal (e.g. 0.02 for 2%).
        """
        if self.mode == SizingMode.FIXED:
            return self.fixed_fraction

        if self.mode == SizingMode.KELLY:
            return self._kelly_sizing()

        if self.mode == SizingMode.VOL_TARGET:
            return self._vol_target_sizing(portfolio_value, current_vol, price)

        if self.mode == SizingMode.ADAPTIVE:
            kelly_frac = self._kelly_sizing()
            vol_frac = self._vol_target_sizing(portfolio_value, current_vol, price)
            # Conservative intersection: take the minimum of the two
            # If vol_target returns 0 (no vol data), fall back to Kelly alone
            if vol_frac <= 0:
                return kelly_frac
            if kelly_frac <= 0:
                return vol_frac
            return min(kelly_frac, vol_frac)

        # Fallback
        return self.fixed_fraction

    # ------------------------------------------------------------------
    # Kelly Criterion
    # ------------------------------------------------------------------

    def _kelly_sizing(self) -> float:
        """Compute position size using quarter-Kelly criterion.

        Falls back to fixed_fraction when fewer than kelly_min_trades
        are in the rolling window.

        Kelly formula: f* = W - (1-W)/R
          where W = win rate, R = avg_win / avg_loss ratio

        We apply quarter-Kelly (25% of optimal) for safety.
        Research (Thorp 2006): this gives ~51% of profit with ~9% of variance.
        """
        if len(self.trade_history) < self.kelly_min_trades:
            return self.fixed_fraction

        stats = self._compute_rolling_stats()
        if stats is None:
            return self.fixed_fraction

        win_rate, avg_win, avg_loss = stats
        raw_kelly = kelly_fraction(win_rate, avg_win, avg_loss)

        # Apply quarter-Kelly multiplier
        adjusted = raw_kelly * self.kelly_fraction_multiplier

        # Cap at maximum fraction
        return min(max(0.0, adjusted), self.kelly_max_fraction)

    def _compute_rolling_stats(self) -> tuple[float, float, float] | None:
        """Compute win rate, average win, and average loss from the rolling window.

        Returns:
            (win_rate, avg_win_pct, avg_loss_pct) or None if insufficient data.
            avg_loss is returned as a positive number for the ratio calculation.
        """
        if not self.trade_history:
            return None

        wins = [t.pnl_pct for t in self.trade_history if t.win and t.pnl_pct > 0]
        losses = [t.pnl_pct for t in self.trade_history if not t.win and t.pnl_pct < 0]

        total = len(self.trade_history)
        win_count = len(wins)

        if total == 0:
            return None

        win_rate = win_count / total
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0

        return win_rate, avg_win, avg_loss

    # ------------------------------------------------------------------
    # Volatility Targeting
    # ------------------------------------------------------------------

    def _vol_target_sizing(
        self,
        portfolio_value: float,
        current_vol: float,
        price: float,
    ) -> float:
        """Compute position size targeting a specific portfolio volatility.

        Based on Zarattini 2025 — 25% target annualized volatility.
        Automatically sizes up in low-vol environments and down in high-vol.

        The returned fraction is the ratio of target notional to portfolio value,
        which represents the position weight (not risk amount).

        We cap at kelly_max_fraction to stay consistent with other modes.
        """
        if portfolio_value <= 0 or price <= 0:
            return self.fixed_fraction

        qty = volatility_target_size(
            portfolio_value=portfolio_value,
            target_annual_vol=self.target_annual_vol,
            current_vol=current_vol,
            price=price,
        )

        if qty <= 0:
            return self.fixed_fraction

        # Convert quantity back to a portfolio fraction
        target_notional = qty * price
        fraction = target_notional / portfolio_value

        # Cap at maximum
        return min(max(0.0, fraction), self.kelly_max_fraction)


# ======================================================================
# Standalone functions (used by PositionSizer and available for direct use)
# ======================================================================


def kelly_fraction(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """Kelly optimal fraction: f* = W - (1-W)/R where W=win rate, R=win/loss ratio.

    Args:
        win_rate: Fraction of trades that are winners (0.0 to 1.0).
        avg_win: Average winning trade P&L as a positive decimal (e.g. 0.05).
        avg_loss: Average losing trade P&L as a positive decimal (e.g. 0.03).

    Returns:
        Kelly optimal fraction (can be negative if strategy has negative edge).
        Clamped to >= 0.
    """
    if avg_loss == 0:
        return 0.0
    R = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    f = win_rate - (1 - win_rate) / R if R > 0 else 0
    return max(0, f)


def volatility_target_size(
    portfolio_value: float,
    target_annual_vol: float,
    current_vol: float,
    price: float,
) -> float:
    """Size position to target a specific portfolio volatility.

    Based on the Zarattini 2025 paper methodology.

    Args:
        portfolio_value: Total portfolio value in USD.
        target_annual_vol: Target annualized volatility as decimal (e.g. 0.25 for 25%).
        current_vol: Asset's annualized volatility as decimal (from ATR or rolling std).
        price: Current price of the asset.

    Returns:
        Quantity of the asset to hold.
    """
    if current_vol <= 0:
        return 0.0
    if price <= 0:
        return 0.0
    # Target notional = portfolio * target_vol / asset_vol
    target_notional = portfolio_value * target_annual_vol / current_vol
    return target_notional / price


def atr_to_annual_vol(atr: float, price: float, period_hours: float = 4.0) -> float:
    """Convert ATR to annualized volatility estimate.

    ATR measures average true range over a period. We convert to annualized
    volatility by:
      1. ATR / price = per-period volatility (as fraction)
      2. Annualize: multiply by sqrt(periods_per_year)

    For 4h candles: 365 * 24 / 4 = 2190 periods per year.
    For 1d candles: 365 periods per year.

    Args:
        atr: Average True Range value.
        price: Current price of the asset.
        period_hours: Hours per candle period (default 4 for 4h candles).

    Returns:
        Annualized volatility as a decimal (e.g. 0.60 for 60%).
    """
    if price <= 0 or atr <= 0:
        return 0.0
    per_period_vol = atr / price
    periods_per_year = (365 * 24) / period_hours
    return per_period_vol * math.sqrt(periods_per_year)
