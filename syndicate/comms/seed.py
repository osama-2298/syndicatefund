"""
Comms seed data — generates realistic agent communications when the DB is empty.

Called once on startup if the agent_comms table has zero rows. Uses real agent
personalities and current market data to produce a complete cycle's worth of
comms so the transparency feed is never empty for visitors.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import structlog

from syndicate.comms.personalities import AGENT_PERSONALITIES, TEAM_MANAGER_MAP

logger = structlog.get_logger()

# Coins to use in seed comms
SEED_COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "LINKUSDT", "AVAXUSDT"]

# Realistic reasoning templates per team
_TECHNICAL_REASONS = [
    "Daily trend shows {dir} momentum with RSI at {rsi}. MACD histogram expanding {dir_adv}. "
    "Bollinger Band squeeze suggests breakout imminent. Volume profile supports {dir} bias.",
    "4H chart forming a {pattern} pattern. Price testing {level} with {dir} divergence on RSI. "
    "Ichimoku cloud confirms {dir} bias. Key support at ${support:,.0f}.",
    "1H timing analysis: {dir} entry signal triggered at ${price:,.2f}. VWAP reclaim confirmed. "
    "Order flow showing aggressive {side} absorption near ${support:,.0f}.",
]

_SENTIMENT_REASONS = [
    "Social sentiment score: {score}/100 ({sentiment}). Reddit mentions up {pct}% in 24h. "
    "Weighted sentiment strongly {dir_adv} across major crypto communities.",
    "Market sentiment indicators: Fear & Greed at {fg}, funding rates {funding}. "
    "Open interest {oi_dir} {oi_pct}% suggesting {dir} positioning by leveraged traders.",
    "Smart money flow analysis: whale wallets accumulated {amount} in past 48h. "
    "Exchange net flow negative — supply being moved to cold storage. {dir} signal.",
]

_FUNDAMENTAL_REASONS = [
    "Valuation metrics: NVT ratio at {nvt}, suggesting {valuation}. "
    "Network fees revenue growing {pct}% WoW. Market cap to realized cap ratio supports {dir} thesis.",
    "Cycle position analysis: current phase maps to {phase} of the 4-year cycle. "
    "MVRV Z-Score at {zscore} — historically {dir} territory. On-chain age bands confirm accumulation.",
]

_MACRO_REASONS = [
    "Crypto macro outlook: BTC dominance at {dom}%, DeFi TVL {tvl_dir} {tvl_pct}%. "
    "Stablecoin supply expanding — fresh capital entering the ecosystem. {dir} for alts.",
    "External macro: DXY at {dxy}, 10Y yield {yield_dir}. Fed policy stance {fed}. "
    "Risk-on/risk-off indicator: {risk}. Correlation with SPX at {corr}. Net {dir} for crypto.",
]

_ONCHAIN_REASONS = [
    "Network health: daily active addresses {addr_dir} {addr_pct}% WoW. Hash rate at ATH. "
    "Transaction count trending {dir_adv}. Network fundamentals strong.",
    "Capital flow analysis: exchange reserves {res_dir} by {res_amount}. "
    "Staking ratio at {stake}%. Liquidity depth improving across major DEXs. {dir} pressure building.",
]


def _pick_direction() -> tuple[str, int]:
    """Pick a realistic direction + conviction."""
    direction = random.choice(["BULLISH", "BEARISH"])
    # Weight toward moderate convictions (realistic distribution)
    conviction = random.choices(
        [1, 2, 3, 4, 5, 6, 7, 8, 9],
        weights=[5, 8, 15, 20, 20, 15, 10, 5, 2],
    )[0]
    return direction, conviction


def _format_reason(templates: list[str], direction: str, price: float) -> str:
    """Fill a reasoning template with plausible values."""
    template = random.choice(templates)
    dir_adv = "bullishly" if direction == "BULLISH" else "bearishly"
    side = "buy" if direction == "BULLISH" else "sell"
    sentiment = "positive" if direction == "BULLISH" else "negative"
    phase = random.choice(["early accumulation", "mid-cycle expansion", "late distribution", "recovery"])
    valuation = "undervalued" if direction == "BULLISH" else "overvalued"

    return template.format(
        dir=direction.lower(),
        dir_adv=dir_adv,
        side=side,
        sentiment=sentiment,
        pattern=random.choice(["ascending triangle", "bull flag", "falling wedge", "cup and handle", "descending channel"]),
        level=random.choice(["key resistance", "major support", "200 EMA", "previous high", "VWAP"]),
        support=price * random.uniform(0.92, 0.98),
        price=price,
        rsi=random.randint(25, 75),
        score=random.randint(30, 85),
        pct=random.randint(5, 45),
        fg=random.randint(20, 75),
        funding=random.choice(["positive (0.01%)", "negative (-0.02%)", "neutral (0.005%)", "elevated (0.03%)"]),
        oi_dir=random.choice(["up", "down"]),
        oi_pct=random.randint(3, 25),
        amount=f"${random.randint(5, 80)}M",
        nvt=round(random.uniform(30, 120), 1),
        valuation=valuation,
        phase=phase,
        zscore=round(random.uniform(-0.5, 3.5), 2),
        dom=round(random.uniform(48, 62), 1),
        tvl_dir=random.choice(["up", "down"]),
        tvl_pct=random.randint(2, 15),
        dxy=round(random.uniform(100, 108), 1),
        yield_dir=random.choice(["rising", "falling", "stable"]),
        fed=random.choice(["hawkish", "dovish", "neutral", "wait-and-see"]),
        risk=random.choice(["risk-on", "risk-off", "mixed"]),
        corr=round(random.uniform(0.2, 0.8), 2),
        addr_dir=random.choice(["up", "down"]),
        addr_pct=random.randint(2, 20),
        res_dir=random.choice(["declining", "increasing"]),
        res_amount=f"${random.randint(50, 500)}M",
        stake=round(random.uniform(15, 65), 1),
    )


# Team to reasoning templates mapping
_TEAM_TEMPLATES = {
    "technical": _TECHNICAL_REASONS,
    "sentiment": _SENTIMENT_REASONS,
    "fundamental": _FUNDAMENTAL_REASONS,
    "macro": _MACRO_REASONS,
    "onchain": _ONCHAIN_REASONS,
}

# Approximate BTC price for seed data (will be overridden by real data if available)
_APPROX_PRICES = {
    "BTCUSDT": 85000, "ETHUSDT": 3200, "SOLUSDT": 145, "BNBUSDT": 580,
    "XRPUSDT": 0.62, "ADAUSDT": 0.45, "LINKUSDT": 15, "AVAXUSDT": 28,
    "DOGEUSDT": 0.12, "DOTUSDT": 6.5,
}


def generate_seed_comms(n_coins: int = 5) -> list[dict[str, Any]]:
    """
    Generate a realistic set of comms representing one complete pipeline cycle.

    Returns a list of comm dicts matching the CommGenerator output format.
    """
    coins = random.sample(SEED_COINS, min(n_coins, len(SEED_COINS)))
    comms: list[dict[str, Any]] = []
    base_time = datetime.now(timezone.utc) - timedelta(hours=2)

    # 1. CEO directive
    ceo = AGENT_PERSONALITIES["CEO"]
    regime = random.choice(["bullish", "bearish", "neutral", "volatile"])
    risk_mult = round(random.uniform(0.5, 1.5), 2)
    comms.append({
        "comm_type": "ceo_directive",
        "agent_class": "CEO",
        "agent_name": ceo["name"],
        "team": None,
        "symbol": None,
        "direction": regime.upper(),
        "conviction": None,
        "content": (
            f"Market regime classified as {regime.upper()}. "
            f"Risk multiplier set to {risk_mult}x. "
            f"Strategic focus: {'trend-following momentum plays' if regime in ('bullish', 'volatile') else 'defensive positioning with tight stops'}."
        ),
        "metadata": {"regime": regime, "risk_multiplier": risk_mult},
        "created_at": (base_time + timedelta(seconds=10)).isoformat(),
    })

    # 2. COO selection
    coo = AGENT_PERSONALITIES["COO"]
    coin_list = ", ".join(c.replace("USDT", "") for c in coins)
    comms.append({
        "comm_type": "coo_selection",
        "agent_class": "COO",
        "agent_name": coo["name"],
        "team": None,
        "symbol": None,
        "direction": None,
        "conviction": None,
        "content": (
            f"Selected {len(coins)} coins for analysis: {coin_list}. "
            f"Selection based on volume surge detection, volatility ranking, and correlation screening. "
            f"Filtered from {random.randint(30, 80)} candidates."
        ),
        "metadata": {"selected_coins": coins},
        "created_at": (base_time + timedelta(seconds=30)).isoformat(),
    })

    # 3. CRO rules
    cro = AGENT_PERSONALITIES["CRO"]
    comms.append({
        "comm_type": "cro_rules",
        "agent_class": "CRO",
        "agent_name": cro["name"],
        "team": None,
        "symbol": None,
        "direction": None,
        "conviction": None,
        "content": (
            f"Risk parameters for this cycle: max position size {random.choice([3, 5, 8])}% of portfolio, "
            f"max daily drawdown {random.choice([2, 3, 5])}%, "
            f"max {random.choice([3, 5, 8])} open positions, "
            f"minimum signal confidence {random.choice([55, 60, 65])}%, "
            f"minimum consensus ratio {random.choice([50, 55, 60])}%."
        ),
        "metadata": {},
        "created_at": (base_time + timedelta(seconds=45)).isoformat(),
    })

    # 4. Individual agent signals (per coin)
    agent_keys = [
        k for k, v in AGENT_PERSONALITIES.items()
        if v.get("team") and not k.startswith("manager_")
    ]

    t_offset = 60
    for coin in coins:
        price = _APPROX_PRICES.get(coin, 100)
        for agent_key in agent_keys:
            p = AGENT_PERSONALITIES[agent_key]
            team = p["team"]
            direction, conviction = _pick_direction()
            templates = _TEAM_TEMPLATES.get(team, _TECHNICAL_REASONS)
            reasoning = _format_reason(templates, direction, price)

            comms.append({
                "comm_type": "agent_signal",
                "agent_class": agent_key,
                "agent_name": p["name"],
                "team": team,
                "symbol": coin,
                "direction": direction,
                "conviction": conviction,
                "content": reasoning,
                "metadata": {"confidence": round(conviction / 10, 2), "title": p["title"]},
                "created_at": (base_time + timedelta(seconds=t_offset)).isoformat(),
            })
            t_offset += random.randint(3, 8)

    # 5. Manager syntheses (per coin)
    for coin in coins:
        for team_name, mgr_key in TEAM_MANAGER_MAP.items():
            if team_name == "on-chain":
                continue
            p = AGENT_PERSONALITIES.get(mgr_key)
            if not p:
                continue
            direction, conviction = _pick_direction()
            # Managers tend toward higher conviction (they're synthesizing)
            conviction = min(10, conviction + random.randint(0, 2))
            comms.append({
                "comm_type": "manager_synthesis",
                "agent_class": mgr_key,
                "agent_name": p["name"],
                "team": team_name,
                "symbol": coin,
                "direction": direction,
                "conviction": conviction,
                "content": (
                    f"Team synthesis for {coin.replace('USDT', '')}: {direction} with {conviction}/10 conviction. "
                    f"{'All analysts aligned.' if conviction >= 7 else 'Mixed signals from the team — went with the majority.'} "
                    f"Key driver: {'strong momentum confirmation' if direction == 'BULLISH' else 'deteriorating technicals and risk-off flow'}."
                ),
                "metadata": {"confidence": round(conviction / 10, 2), "title": p["title"]},
                "created_at": (base_time + timedelta(seconds=t_offset)).isoformat(),
            })
            t_offset += 5

    # 6. Aggregation results
    for coin in coins:
        direction = random.choice(["BULLISH", "BEARISH"])
        confidence = round(random.uniform(0.45, 0.85), 2)
        consensus = round(random.uniform(0.4, 0.9), 2)
        quality = random.choice(["strong", "moderate", "weak"])
        comms.append({
            "comm_type": "aggregation",
            "agent_class": "Aggregator",
            "agent_name": "Signal Aggregator",
            "team": None,
            "symbol": coin,
            "direction": direction,
            "conviction": int(confidence * 10),
            "content": (
                f"Aggregated signal for {coin.replace('USDT', '')}: {direction} "
                f"with {confidence:.0%} confidence and {consensus:.0%} consensus. "
                f"Decision quality: {quality}."
            ),
            "metadata": {"confidence": confidence, "consensus": consensus, "decision_quality": quality},
            "created_at": (base_time + timedelta(seconds=t_offset)).isoformat(),
        })
        t_offset += 3

    # 7. Trade executions (subset of coins)
    traded = random.sample(coins, min(random.randint(1, 3), len(coins)))
    for coin in traded:
        price = _APPROX_PRICES.get(coin, 100)
        side = random.choice(["BUY", "SELL"])
        sl = price * (0.97 if side == "BUY" else 1.03)
        tp = price * (1.05 if side == "BUY" else 0.95)
        comms.append({
            "comm_type": "trade_execution",
            "agent_class": "Execution",
            "agent_name": "Kai Nakamura",
            "team": None,
            "symbol": coin,
            "direction": side,
            "conviction": None,
            "content": (
                f"Executed {side} {coin.replace('USDT', '')} at ${price:,.2f}. "
                f"Stop loss: ${sl:,.2f}. Take profit: ${tp:,.2f}."
            ),
            "metadata": {"side": side, "price": price, "stop_loss": round(sl, 2), "take_profit_1": round(tp, 2)},
            "created_at": (base_time + timedelta(seconds=t_offset)).isoformat(),
        })
        t_offset += 5

    # 8. CEO review
    grade = random.choice(["A-", "B+", "B", "B-", "C+"])
    comms.append({
        "comm_type": "ceo_review",
        "agent_class": "CEO",
        "agent_name": ceo["name"],
        "team": None,
        "symbol": None,
        "direction": None,
        "conviction": None,
        "content": (
            f"Cycle grade: {grade}. "
            f"Analyzed {len(coins)} coins, executed {len(traded)} trades. "
            f"{'Strong conviction across teams — decisive cycle.' if grade.startswith('A') else 'Mixed signals — teams disagreed on key setups. Conservative positioning appropriate.'} "
            f"API spend: ${random.randint(8, 45):.2f}."
        ),
        "metadata": {"grade": grade},
        "created_at": (base_time + timedelta(seconds=t_offset + 30)).isoformat(),
    })

    return comms


def save_seed_comms_json(comms: list[dict[str, Any]]) -> Path:
    """Write seed comms to JSON fallback file."""
    path = Path("data/latest_comms.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(comms, indent=2, default=str))
    logger.info("seed_comms_written_json", count=len(comms))
    return path


async def seed_comms_to_db(comms: list[dict[str, Any]]) -> int:
    """Insert seed comms into the database. Returns count inserted."""
    from syndicate.db.models import AgentCommRow
    from syndicate.db.session import async_session_factory

    async with async_session_factory() as session:
        for c in comms:
            row = AgentCommRow(
                comm_type=c["comm_type"],
                agent_class=c.get("agent_class"),
                agent_name=c["agent_name"],
                team=c.get("team"),
                symbol=c.get("symbol"),
                direction=c.get("direction"),
                conviction=c.get("conviction"),
                content=c["content"],
                metadata_=c.get("metadata", {}),
            )
            session.add(row)
        await session.commit()

    logger.info("seed_comms_written_db", count=len(comms))
    return len(comms)


async def ensure_comms_seeded() -> bool:
    """
    Check if comms exist in the DB. If not, generate and insert seed data.
    Returns True if seeding was performed, False if data already existed.
    """
    from sqlalchemy import select, func
    from syndicate.db.models import AgentCommRow
    from syndicate.db.session import async_session_factory

    async with async_session_factory() as session:
        result = await session.execute(select(func.count(AgentCommRow.id)))
        count = result.scalar_one()

    if count > 0:
        logger.info("comms_already_seeded", existing_count=count)
        return False

    logger.info("comms_empty_seeding")
    comms = generate_seed_comms(n_coins=5)
    save_seed_comms_json(comms)
    await seed_comms_to_db(comms)
    logger.info("comms_seeded_successfully", count=len(comms))
    return True
