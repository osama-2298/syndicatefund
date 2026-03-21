"""
Portfolio-Level Risk Manager.

Implements the portfolio-level risk controls that real hedge funds use
but were missing from Syndicate Fund v1:

1. Progressive Drawdown Ladder (Millennium-style):
   -1.5% → flag for monitoring
   -3.0% → reduce position sizes by 50%, no new meme/midcap trades
   -5.0% → close worst performers, only BTC/ETH allowed
   -8.0% → full halt, close all positions

2. Portfolio Heat Tracking:
   Sum of all risk-at-loss (distance to stop × position size)
   Capped at 5-7% of portfolio value

3. Correlation Monitoring:
   Rolling 30-day pairwise correlation between held assets
   When average exceeds 0.7, reduce gross exposure by 25%

4. Gross/Net Exposure Management:
   Track and enforce exposure limits by regime

5. Expected Return Gate:
   Only take trades where E[return] > transaction costs
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum

import numpy as np
import structlog

from syndicate.data.models import MarketRegime, OrderSide, PortfolioState
from syndicate.risk.trade_params import TIER_CONFIG, classify_tier

logger = structlog.get_logger()


class DrawdownLevel(IntEnum):
    """Progressive drawdown ladder levels."""
    OK = 0           # Normal trading
    FLAGGED = 1      # -1.5% — monitoring, no action yet
    REDUCED = 2      # -3.0% — position sizes halved, no meme/midcap
    BTC_ETH_ONLY = 3 # -5.0% — close worst performers, only BTC/ETH
    HALTED = 4       # -8.0% — full trading halt


DRAWDOWN_LADDER = [
    (0.015, DrawdownLevel.FLAGGED,      "Portfolio down 1.5% from peak — flagged for monitoring"),
    (0.030, DrawdownLevel.REDUCED,      "Portfolio down 3.0% — position sizes halved, no meme/midcap"),
    (0.050, DrawdownLevel.BTC_ETH_ONLY, "Portfolio down 5.0% — only BTC/ETH trades allowed"),
    (0.080, DrawdownLevel.HALTED,       "Portfolio down 8.0% — ALL trading halted"),
]

# Allowed tiers per drawdown level
ALLOWED_TIERS = {
    DrawdownLevel.OK: {"btc", "top5", "large_cap", "mid_cap", "meme"},
    DrawdownLevel.FLAGGED: {"btc", "top5", "large_cap", "mid_cap", "meme"},
    DrawdownLevel.REDUCED: {"btc", "top5", "large_cap"},
    DrawdownLevel.BTC_ETH_ONLY: {"btc", "top5"},
    DrawdownLevel.HALTED: set(),
}

# Position size multiplier per drawdown level
SIZE_MULTIPLIER = {
    DrawdownLevel.OK: 1.0,
    DrawdownLevel.FLAGGED: 1.0,
    DrawdownLevel.REDUCED: 0.50,
    DrawdownLevel.BTC_ETH_ONLY: 0.25,
    DrawdownLevel.HALTED: 0.0,
}

# Max portfolio heat (sum of risk-at-loss / portfolio value)
MAX_PORTFOLIO_HEAT = 0.07  # 7%

# Correlation thresholds
CORRELATION_WARNING = 0.60
CORRELATION_REDUCE = 0.70
CORRELATION_CRITICAL = 0.80

# Gross/net exposure targets by regime
EXPOSURE_TARGETS = {
    MarketRegime.BULL: {"max_gross": 1.0, "target_net": (0.30, 0.60)},
    MarketRegime.RANGING: {"max_gross": 0.80, "target_net": (-0.10, 0.20)},
    MarketRegime.BEAR: {"max_gross": 0.60, "target_net": (-0.30, 0.10)},
    MarketRegime.CRISIS: {"max_gross": 0.30, "target_net": (-0.10, 0.10)},
}


@dataclass
class PortfolioRiskSnapshot:
    """Result of a portfolio risk check."""

    # Drawdown
    drawdown_pct: float = 0.0
    drawdown_level: DrawdownLevel = DrawdownLevel.OK
    drawdown_message: str = ""

    # Portfolio heat
    portfolio_heat: float = 0.0
    heat_budget_remaining: float = MAX_PORTFOLIO_HEAT
    heat_exceeded: bool = False

    # Correlation
    avg_correlation: float = 0.0
    correlation_warning: bool = False
    correlation_matrix: dict = field(default_factory=dict)

    # Exposure
    gross_exposure: float = 0.0
    net_exposure: float = 0.0

    # Position count
    positions_count: int = 0

    # Actions required
    actions: list[str] = field(default_factory=list)

    # Allowed tiers for new trades
    allowed_tiers: set[str] = field(default_factory=lambda: {"btc", "top5", "large_cap", "mid_cap", "meme"})

    # Position size multiplier
    size_multiplier: float = 1.0

    # Timestamp
    snapshot_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def trading_allowed(self) -> bool:
        return self.drawdown_level < DrawdownLevel.HALTED

    def to_dict(self) -> dict:
        return {
            "drawdown_pct": round(self.drawdown_pct * 100, 3),
            "drawdown_level": self.drawdown_level.name,
            "drawdown_message": self.drawdown_message,
            "portfolio_heat": round(self.portfolio_heat * 100, 3),
            "heat_budget_remaining": round(self.heat_budget_remaining * 100, 3),
            "heat_exceeded": self.heat_exceeded,
            "avg_correlation": round(self.avg_correlation, 4),
            "correlation_warning": self.correlation_warning,
            "gross_exposure": round(self.gross_exposure * 100, 2),
            "net_exposure": round(self.net_exposure * 100, 2),
            "positions_count": self.positions_count,
            "actions": self.actions,
            "allowed_tiers": sorted(self.allowed_tiers),
            "size_multiplier": self.size_multiplier,
            "trading_allowed": self.trading_allowed,
            "snapshot_at": self.snapshot_at.isoformat(),
        }


class PortfolioRiskManager:
    """
    Portfolio-level risk management.

    Runs in both the fast loop (15-min risk checks) and the slow loop
    (before trade execution). Produces a PortfolioRiskSnapshot that
    tells the pipeline what's allowed and what isn't.
    """

    def __init__(
        self,
        max_heat: float = MAX_PORTFOLIO_HEAT,
        correlation_reduce_threshold: float = CORRELATION_REDUCE,
    ) -> None:
        self.max_heat = max_heat
        self.correlation_reduce_threshold = correlation_reduce_threshold
        self._returns_history: dict[str, list[float]] = {}

    def check(
        self,
        portfolio: PortfolioState,
        open_trades: list[dict] | None = None,
        returns_history: dict[str, list[float]] | None = None,
        regime: MarketRegime | None = None,
    ) -> PortfolioRiskSnapshot:
        """
        Run all portfolio-level risk checks.

        Args:
            portfolio: Current portfolio state with positions.
            open_trades: List of open trade dicts with stop_loss info.
            returns_history: {symbol: [daily_returns]} for correlation calc.
            regime: Current market regime for exposure targets.

        Returns:
            PortfolioRiskSnapshot with risk metrics and required actions.
        """
        snapshot = PortfolioRiskSnapshot(
            positions_count=len(portfolio.positions),
        )

        # 1. Drawdown ladder
        self._check_drawdown(portfolio, snapshot)

        # 2. Portfolio heat
        self._check_heat(portfolio, open_trades, snapshot)

        # 3. Correlation
        if returns_history:
            self._check_correlation(returns_history, snapshot)

        # 4. Exposure
        self._check_exposure(portfolio, regime, snapshot)

        # Log the result
        logger.info(
            "portfolio_risk_check",
            drawdown_level=snapshot.drawdown_level.name,
            portfolio_heat=round(snapshot.portfolio_heat * 100, 2),
            avg_correlation=round(snapshot.avg_correlation, 3),
            gross_exposure=round(snapshot.gross_exposure * 100, 1),
            net_exposure=round(snapshot.net_exposure * 100, 1),
            actions=snapshot.actions,
            trading_allowed=snapshot.trading_allowed,
        )

        return snapshot

    def _check_drawdown(self, portfolio: PortfolioState, snapshot: PortfolioRiskSnapshot) -> None:
        """Progressive drawdown ladder check."""
        dd = portfolio.drawdown_pct
        snapshot.drawdown_pct = dd

        level = DrawdownLevel.OK
        message = "Portfolio within normal range"

        for threshold, dd_level, msg in DRAWDOWN_LADDER:
            if dd >= threshold:
                level = dd_level
                message = msg

        snapshot.drawdown_level = level
        snapshot.drawdown_message = message
        snapshot.allowed_tiers = ALLOWED_TIERS[level].copy()
        snapshot.size_multiplier = SIZE_MULTIPLIER[level]

        if level >= DrawdownLevel.FLAGGED:
            snapshot.actions.append(f"DRAWDOWN_{level.name}: {message}")

        if level >= DrawdownLevel.REDUCED:
            logger.warning(
                "drawdown_ladder_triggered",
                level=level.name,
                drawdown_pct=round(dd * 100, 2),
                message=message,
            )

    def _check_heat(
        self,
        portfolio: PortfolioState,
        open_trades: list[dict] | None,
        snapshot: PortfolioRiskSnapshot,
    ) -> None:
        """
        Portfolio heat = sum of risk-at-loss for all open positions.

        Risk-at-loss per position = |entry_price - stop_loss| × quantity
        If no stop info available, estimate as ATR-based stop distance.
        """
        total_value = portfolio.total_value
        if total_value <= 0:
            return

        total_risk = 0.0

        if open_trades:
            # Use actual stop loss distances from open trades
            for trade in open_trades:
                entry = trade.get("entry_price", 0)
                stop = trade.get("stop_loss", 0)
                qty = trade.get("quantity", 0)
                if entry > 0 and stop > 0 and qty > 0:
                    risk = abs(entry - stop) * qty
                    total_risk += risk
        else:
            # Estimate from positions using tier-based fallback stops
            for pos in portfolio.positions:
                tier = classify_tier(pos.symbol)
                config = TIER_CONFIG.get(tier, TIER_CONFIG["mid_cap"])
                fallback_pct = config["fallback_stop_pct"]
                risk = pos.entry_price * fallback_pct * pos.quantity
                total_risk += risk

        heat = total_risk / total_value
        snapshot.portfolio_heat = heat
        snapshot.heat_budget_remaining = max(0, self.max_heat - heat)
        snapshot.heat_exceeded = heat > self.max_heat

        if snapshot.heat_exceeded:
            snapshot.actions.append(
                f"HEAT_EXCEEDED: Portfolio heat {heat*100:.1f}% exceeds {self.max_heat*100:.0f}% limit. "
                f"No new positions until heat decreases."
            )

    def _check_correlation(
        self,
        returns_history: dict[str, list[float]],
        snapshot: PortfolioRiskSnapshot,
    ) -> None:
        """
        Rolling pairwise correlation between held assets.

        Uses the last 30 daily returns (or available data) to compute
        average pairwise correlation. Crypto assets become highly
        correlated in selloffs — this detects that early.
        """
        symbols = list(returns_history.keys())
        if len(symbols) < 2:
            snapshot.avg_correlation = 0.0
            return

        # Build returns matrix
        # Use the minimum length available across all symbols
        min_len = min(len(r) for r in returns_history.values())
        if min_len < 5:
            snapshot.avg_correlation = 0.0
            return

        # Use last 30 periods (or available)
        window = min(min_len, 30)
        matrix = []
        valid_symbols = []
        for sym in symbols:
            returns = returns_history[sym][-window:]
            if len(returns) >= 5 and np.std(returns) > 1e-10:
                matrix.append(returns[-window:])
                valid_symbols.append(sym)

        if len(valid_symbols) < 2:
            snapshot.avg_correlation = 0.0
            return

        # Compute correlation matrix
        try:
            corr_matrix = np.corrcoef(matrix)
            # Average of upper triangle (excluding diagonal)
            n = len(valid_symbols)
            pairwise_corrs = []
            corr_dict = {}
            for i in range(n):
                for j in range(i + 1, n):
                    corr_val = float(corr_matrix[i, j])
                    if not np.isnan(corr_val):
                        pairwise_corrs.append(corr_val)
                        corr_dict[f"{valid_symbols[i]}/{valid_symbols[j]}"] = round(corr_val, 4)

            if pairwise_corrs:
                avg_corr = float(np.mean(pairwise_corrs))
                snapshot.avg_correlation = avg_corr
                snapshot.correlation_matrix = corr_dict

                if avg_corr >= CORRELATION_CRITICAL:
                    snapshot.correlation_warning = True
                    snapshot.size_multiplier *= 0.50
                    snapshot.actions.append(
                        f"CORRELATION_CRITICAL: Avg pairwise correlation {avg_corr:.2f} >= {CORRELATION_CRITICAL}. "
                        f"Position sizes halved."
                    )
                elif avg_corr >= self.correlation_reduce_threshold:
                    snapshot.correlation_warning = True
                    snapshot.size_multiplier *= 0.75
                    snapshot.actions.append(
                        f"CORRELATION_HIGH: Avg pairwise correlation {avg_corr:.2f} >= {self.correlation_reduce_threshold}. "
                        f"Position sizes reduced 25%."
                    )
                elif avg_corr >= CORRELATION_WARNING:
                    snapshot.actions.append(
                        f"CORRELATION_WATCH: Avg pairwise correlation {avg_corr:.2f} approaching threshold."
                    )
        except Exception as e:
            logger.warning("correlation_calc_error", error=str(e))
            snapshot.avg_correlation = 0.0

    def _check_exposure(
        self,
        portfolio: PortfolioState,
        regime: MarketRegime | None,
        snapshot: PortfolioRiskSnapshot,
    ) -> None:
        """
        Gross and net exposure management.

        Gross = sum(|position_value|) / portfolio_value
        Net = (long_value - short_value) / portfolio_value
        """
        total_value = portfolio.total_value
        if total_value <= 0:
            return

        long_value = 0.0
        short_value = 0.0

        for pos in portfolio.positions:
            notional = abs(pos.notional_value)
            if pos.side == OrderSide.BUY:
                long_value += notional
            else:
                short_value += notional

        gross = (long_value + short_value) / total_value
        net = (long_value - short_value) / total_value

        snapshot.gross_exposure = gross
        snapshot.net_exposure = net

        # Check against regime targets
        if regime and regime in EXPOSURE_TARGETS:
            targets = EXPOSURE_TARGETS[regime]
            max_gross = targets["max_gross"]
            net_range = targets["target_net"]

            if gross > max_gross:
                snapshot.actions.append(
                    f"EXPOSURE_HIGH: Gross {gross*100:.0f}% exceeds "
                    f"{regime.value} target of {max_gross*100:.0f}%."
                )

            if net < net_range[0] or net > net_range[1]:
                snapshot.actions.append(
                    f"EXPOSURE_IMBALANCED: Net {net*100:.0f}% outside "
                    f"{regime.value} target range "
                    f"[{net_range[0]*100:.0f}%, {net_range[1]*100:.0f}%]."
                )

    def can_open_position(
        self,
        symbol: str,
        risk_snapshot: PortfolioRiskSnapshot,
        risk_amount_usd: float = 0.0,
        portfolio_value: float = 0.0,
    ) -> tuple[bool, str]:
        """
        Check if a new position is allowed given current risk state.

        Returns (allowed, reason).
        """
        tier = classify_tier(symbol)

        # Check drawdown level
        if not risk_snapshot.trading_allowed:
            return False, f"Trading halted: {risk_snapshot.drawdown_message}"

        # Check allowed tiers
        if tier not in risk_snapshot.allowed_tiers:
            return False, (
                f"Tier '{tier}' not allowed at drawdown level "
                f"{risk_snapshot.drawdown_level.name}"
            )

        # Check portfolio heat
        if risk_snapshot.heat_exceeded and risk_amount_usd > 0:
            return False, (
                f"Portfolio heat {risk_snapshot.portfolio_heat*100:.1f}% "
                f"exceeds {self.max_heat*100:.0f}% limit"
            )

        # Check if adding this trade would exceed heat limit
        if portfolio_value > 0 and risk_amount_usd > 0:
            additional_heat = risk_amount_usd / portfolio_value
            if additional_heat > risk_snapshot.heat_budget_remaining:
                return False, (
                    f"Trade risk ${risk_amount_usd:.0f} would exceed remaining "
                    f"heat budget of ${risk_snapshot.heat_budget_remaining * portfolio_value:.0f}"
                )

        return True, "OK"

    def adjust_position_size(
        self,
        quantity: float,
        risk_snapshot: PortfolioRiskSnapshot,
    ) -> float:
        """
        Apply portfolio-level size adjustments to a position.

        Multipliers from drawdown ladder and correlation checks
        stack multiplicatively.
        """
        return quantity * risk_snapshot.size_multiplier

    @staticmethod
    def expected_return_positive(
        win_rate: float,
        avg_win_pct: float,
        avg_loss_pct: float,
        fee_pct: float = 0.0010,  # 0.10% taker fee (each side)
        slippage_pct: float = 0.0005,  # 0.05% estimated slippage
    ) -> tuple[bool, float]:
        """
        Expected return gate — only take trades where E[R] > costs.

        E[R] = (win_rate × avg_win) - ((1 - win_rate) × avg_loss) - costs

        Returns (is_positive, expected_return).
        """
        total_cost = (fee_pct + slippage_pct) * 2  # entry + exit
        expected = (win_rate * avg_win_pct) - ((1 - win_rate) * avg_loss_pct) - total_cost

        return expected > 0, expected
