"""Binary Kelly criterion position sizing for weather bets."""

from __future__ import annotations

import structlog

from syndicate.polymarket.models import BinProbability, WeatherPortfolio

log = structlog.get_logger(__name__)


def kelly_size(
    model_prob: float,
    market_price: float,
    bankroll: float,
    fractional: float = 0.25,   # Quarter-Kelly
    max_fraction: float = 0.25,  # Max 25% of bankroll per bet
) -> float:
    """Compute optimal bet size using binary Kelly criterion.

    For a YES bet at price p with model probability q:
        Kelly fraction = (q - p) / (1 - p)

    We use fractional Kelly (default 25%) and cap at max_fraction.

    Args:
        model_prob: Our estimated probability of the outcome (0-1).
        market_price: Current YES price on the market (0-1).
        bankroll: Total bankroll in USDC.
        fractional: Kelly fraction to apply (0.25 = quarter-Kelly).
        max_fraction: Maximum fraction of bankroll per single bet.

    Returns:
        USDC amount to bet.
    """
    if model_prob <= market_price:
        return 0.0  # No edge

    if market_price >= 1.0:
        return 0.0  # Can't buy at 100%

    edge = model_prob - market_price
    kelly_fraction = edge / (1.0 - market_price)

    # Apply fractional Kelly and cap
    fraction = min(kelly_fraction * fractional, max_fraction)

    amount = fraction * bankroll
    return max(0.0, amount)


def check_exposure_limits(
    portfolio: WeatherPortfolio,
    city: str,
    date: str,
    bet_amount: float,
    max_per_city: float = 0.15,  # Max 15% of bankroll per city
    max_per_day: float = 0.30,   # Max 30% per resolution day
) -> float:
    """Reduce bet_amount if it would exceed city or day exposure limits.

    Args:
        portfolio: Current portfolio state.
        city: City for the proposed bet.
        date: Resolution date (YYYY-MM-DD) for the proposed bet.
        bet_amount: Proposed bet amount in USDC.
        max_per_city: Max fraction of bankroll exposed to a single city.
        max_per_day: Max fraction of bankroll exposed to a single resolution day.

    Returns:
        Adjusted bet amount (possibly 0 if limits reached).
    """
    bankroll = portfolio.bankroll

    if bankroll <= 0:
        return 0.0

    # Current exposure by city
    city_exposure = sum(
        p.quantity for p in portfolio.positions
        if not p.resolved and p.city == city
    )
    city_remaining = max(0.0, bankroll * max_per_city - city_exposure)

    # Current exposure by day
    day_exposure = sum(
        p.quantity for p in portfolio.positions
        if not p.resolved and p.date == date
    )
    day_remaining = max(0.0, bankroll * max_per_day - day_exposure)

    adjusted = min(bet_amount, city_remaining, day_remaining)

    if adjusted < bet_amount:
        log.info(
            "check_exposure_limits.reduced",
            city=city,
            date=date,
            original=round(bet_amount, 2),
            adjusted=round(adjusted, 2),
            city_exposure=round(city_exposure, 2),
            city_remaining=round(city_remaining, 2),
            day_exposure=round(day_exposure, 2),
            day_remaining=round(day_remaining, 2),
        )

    return max(0.0, adjusted)


def size_position(
    prob: BinProbability,
    portfolio: WeatherPortfolio,
    city: str,
    date: str,
    fractional: float = 0.25,
    max_fraction: float = 0.25,
    max_per_city: float = 0.15,
    max_per_day: float = 0.30,
    min_bet: float = 5.0,  # Minimum $5 bet (matches MIN_BET_SIZE)
) -> float:
    """Full sizing pipeline: Kelly -> exposure limits -> minimum check.

    Steps:
      1. Compute Kelly-optimal bet size (fractional, capped)
      2. Apply city and day exposure limits
      3. Check minimum bet threshold
      4. Check available cash

    Note: the paper trader's place_bet() applies an additional
    liquidity-aware cap based on estimated bin depth.  This function
    computes the *desired* size; place_bet() enforces the *fillable* size.

    Args:
        prob: BinProbability with model_prob, market_price, and edge.
        portfolio: Current portfolio state.
        city: City for the proposed bet.
        date: Resolution date (YYYY-MM-DD).
        fractional: Kelly fraction (default quarter-Kelly).
        max_fraction: Max fraction of bankroll per bet.
        max_per_city: Max fraction of bankroll per city.
        max_per_day: Max fraction of bankroll per resolution day.
        min_bet: Minimum bet size in USDC.

    Returns:
        Final USDC amount to bet, or 0.0 if not worth it.
    """
    # Step 1: Kelly sizing — use current cash, not initial bankroll
    # Using bankroll when cash is depleted leads to reckless over-sizing.
    effective_bankroll = min(portfolio.bankroll, portfolio.cash)
    raw_size = kelly_size(
        model_prob=prob.model_prob,
        market_price=prob.market_price,
        bankroll=effective_bankroll,
        fractional=fractional,
        max_fraction=max_fraction,
    )

    if raw_size <= 0.0:
        return 0.0

    # Step 2: Exposure limits
    limited_size = check_exposure_limits(
        portfolio=portfolio,
        city=city,
        date=date,
        bet_amount=raw_size,
        max_per_city=max_per_city,
        max_per_day=max_per_day,
    )

    if limited_size <= 0.0:
        return 0.0

    # Step 3: Check minimum bet
    if limited_size < min_bet:
        log.debug(
            "size_position.below_minimum",
            city=city,
            date=date,
            size=round(limited_size, 2),
            min_bet=min_bet,
        )
        return 0.0

    # Step 4: Check available cash
    final_size = min(limited_size, portfolio.cash)

    if final_size < min_bet:
        log.debug(
            "size_position.insufficient_cash",
            city=city,
            date=date,
            cash=round(portfolio.cash, 2),
            needed=round(limited_size, 2),
        )
        return 0.0

    log.info(
        "size_position.done",
        city=city,
        date=date,
        bin_label=prob.label,
        model_prob=round(prob.model_prob, 4),
        market_price=round(prob.market_price, 4),
        edge=round(prob.edge, 4),
        kelly_raw=round(raw_size, 2),
        final_size=round(final_size, 2),
    )

    return final_size
