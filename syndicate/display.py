"""
Terminal display engine for Syndicate.

Design principles:
- Visual hierarchy: the most important info (verdict) should scream
- Scannable: a glance tells you what happened
- Aligned: columns line up, padding is consistent
- Colored with purpose: green=bullish, red=bearish, yellow=caution, cyan=brand
"""

from __future__ import annotations

import shutil


# ── ANSI Codes ──

class C:
    """ANSI escape sequences."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"

    B_RED = "\033[91m"
    B_GREEN = "\033[92m"
    B_YELLOW = "\033[93m"
    B_BLUE = "\033[94m"
    B_MAGENTA = "\033[95m"
    B_CYAN = "\033[96m"
    B_WHITE = "\033[97m"

    # Backgrounds
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"
    BG_YELLOW = "\033[43m"
    BG_CYAN = "\033[46m"
    BG_GRAY = "\033[100m"


def _term_width() -> int:
    """Get terminal width, default 80."""
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


# ── Primitives ──

def c(text: str, color: str) -> str:
    return f"{color}{text}{C.RESET}"


def bold(text: str) -> str:
    return f"{C.BOLD}{text}{C.RESET}"


def dim(text: str) -> str:
    return f"{C.DIM}{text}{C.RESET}"


def badge(text: str, bg: str, fg: str = C.B_WHITE) -> str:
    """Render a colored badge like  BUY  or  HOLD ."""
    return f"{C.BOLD}{bg}{fg} {text} {C.RESET}"


# ── Trading-specific formatters ──

def action_badge(action: str) -> str:
    """Prominent colored badge for trading actions."""
    styles = {
        "BUY": (C.BG_GREEN, C.B_WHITE),
        "SELL": (C.BG_RED, C.B_WHITE),
        "SHORT": (C.BG_RED, C.B_WHITE),
        "HOLD": (C.BG_YELLOW, "\033[30m"),  # black text on yellow
        "COVER": (C.BG_CYAN, C.B_WHITE),
    }
    bg, fg = styles.get(action, (C.BG_GRAY, C.B_WHITE))
    padded = f"{action:^7}"
    return f"{C.BOLD}{bg}{fg}{padded}{C.RESET}"


def action_text(action: str) -> str:
    """Colored text for inline action mentions."""
    colors = {
        "BUY": C.B_GREEN,
        "SELL": C.B_RED,
        "SHORT": C.B_RED,
        "HOLD": C.B_YELLOW,
        "COVER": C.B_CYAN,
    }
    return f"{C.BOLD}{colors.get(action, C.WHITE)}{action}{C.RESET}"


def conf(confidence: float) -> str:
    """Color-coded confidence percentage."""
    pct = f"{confidence:.0%}"
    if confidence >= 0.70:
        return c(pct, C.B_GREEN)
    elif confidence >= 0.55:
        return c(pct, C.B_YELLOW)
    return c(pct, C.B_RED)


def conf_bar(confidence: float, width: int = 10) -> str:
    """Mini bar chart for confidence: [========--]."""
    filled = int(confidence * width)
    empty = width - filled

    if confidence >= 0.70:
        color = C.B_GREEN
    elif confidence >= 0.55:
        color = C.B_YELLOW
    else:
        color = C.B_RED

    bar = f"{color}{'█' * filled}{C.RESET}{C.DIM}{'░' * empty}{C.RESET}"
    return f"{bar}"


def pnl(value: float) -> str:
    """Color a P&L value."""
    if value > 0:
        return c(f"+${value:,.2f}", C.B_GREEN)
    elif value < 0:
        return c(f"-${abs(value):,.2f}", C.B_RED)
    return dim("$0.00")


def pct(value: float) -> str:
    """Color a percentage."""
    if value > 0:
        return c(f"+{value:.2f}%", C.B_GREEN)
    elif value < 0:
        return c(f"{value:.2f}%", C.B_RED)
    return dim("0.00%")


def usd(value: float) -> str:
    """Format USD amount."""
    return f"${value:,.2f}"


# ── Layout Components ──

def banner(symbol: str, timestamp: str) -> None:
    """Print the Syndicate header."""
    w = min(_term_width(), 72)
    bar = c("━" * w, C.CYAN)

    print(f"\n{bar}")
    print(f"  {C.BOLD}{C.B_CYAN}SYNDICATE{C.RESET}  {dim('Distributed AI Hedge Fund')}")
    print(bar)
    print()
    print(f"    {dim('Symbol')}   {bold(symbol)}")
    print(
        f"    {dim('Teams')}    "
        f"{c('Technical', C.B_BLUE)}  "
        f"{c('Sentiment', C.B_MAGENTA)}  "
        f"{c('Fundamental', C.B_YELLOW)}"
    )
    print(f"    {dim('Time')}     {dim(timestamp)}")


def section(title: str) -> None:
    """Print a section divider."""
    w = min(_term_width(), 72)
    print(f"\n  {c('─' * w, C.DIM)}")
    print(f"  {C.BOLD}{C.WHITE}{title}{C.RESET}")
    print()


def step_start(n: int, total: int, label: str) -> None:
    """Print a step starting indicator."""
    num = c(f"{n}/{total}", C.CYAN)
    print(f"\n  {C.BOLD}{num}{C.RESET}  {label}")


def step_done(n: int, total: int, label: str, detail: str = "") -> None:
    """Print a completed step with checkmark."""
    check = c("✓", C.B_GREEN)
    extra = f"  {dim(detail)}" if detail else ""
    print(f"  {check}  {label}{extra}")


def market_card(price: float, change: float, volume: float, candles: int, interval: str) -> None:
    """Print market data in a compact card."""
    print(f"    {dim('Price')}       {C.BOLD}{C.WHITE}${price:,.2f}{C.RESET}   {pct(change)}")
    print(f"    {dim('Volume 24h')}  {dim(usd(volume))}")
    print(f"    {dim('Data')}        {dim(f'{candles} candles @ {interval}')}")


def indicator_chips(rsi: float | None, macd_cross: str | None, price_vs_sma: str | None, vol_ratio: float | None) -> None:
    """Print indicators as compact color-coded chips."""
    chips = []

    if rsi is not None:
        if rsi > 70:
            chips.append(c(f"RSI {rsi:.0f}", C.B_RED))
        elif rsi < 30:
            chips.append(c(f"RSI {rsi:.0f}", C.B_GREEN))
        else:
            chips.append(f"RSI {rsi:.0f}")

    if macd_cross:
        color = C.B_GREEN if macd_cross == "bullish" else C.B_RED
        chips.append(f"MACD {c(macd_cross, color)}")

    if price_vs_sma:
        color = C.B_GREEN if price_vs_sma == "above" else C.B_RED
        chips.append(f"vs SMA50 {c(price_vs_sma, color)}")

    if vol_ratio is not None:
        if vol_ratio > 1.5:
            chips.append(c(f"Vol {vol_ratio:.1f}x", C.B_GREEN))
        elif vol_ratio < 0.7:
            chips.append(c(f"Vol {vol_ratio:.1f}x", C.B_RED))
        else:
            chips.append(dim(f"Vol {vol_ratio:.1f}x"))

    print(f"    {dim('  ·  ').join(chips)}")


def agent_result(team: str, action: str, confidence: float, elapsed: float) -> None:
    """Print a single agent's result inline as it completes."""
    team_colors = {
        "Technical": C.B_BLUE,
        "Sentiment": C.B_MAGENTA,
        "Fundamental": C.B_YELLOW,
    }
    team_c = team_colors.get(team, C.WHITE)
    time_str = dim(f"{elapsed:.1f}s")

    print(
        f"    {c(team, team_c):<24}  "
        f"{action_badge(action)}  "
        f"{conf_bar(confidence)} {conf(confidence)}  "
        f"{time_str}"
    )


def signal_table(signals: list[tuple[str, str, float, str]]) -> None:
    """
    Print the signal comparison table.
    Each signal is (team_name, action, confidence, reasoning).
    """
    section("Signal Breakdown")

    # Column widths
    team_w = 14
    action_w = 9
    conf_w = 12
    bar_w = 10

    # Header
    print(
        f"    {dim('Team'):<{team_w}}  "
        f"{dim('Signal'):^{action_w}}  "
        f"{dim('Conf'):>{conf_w}}  "
        f"{dim(''):>{bar_w}}  "
        f"{dim('Reasoning')}"
    )
    print(f"    {dim('─' * 68)}")

    team_colors = {
        "Technical": C.B_BLUE,
        "Sentiment": C.B_MAGENTA,
        "Fundamental": C.B_YELLOW,
    }

    for team_name, action, confidence, reasoning in signals:
        tc = team_colors.get(team_name, C.WHITE)
        reason_clean = reasoning.replace("\n", " ")
        if len(reason_clean) > 40:
            reason_clean = reason_clean[:39] + "…"

        print(
            f"    {c(team_name, tc):<{team_w + 9}}  "
            f"{action_badge(action)}  "
            f"{conf(confidence):>{conf_w + 9}}  "
            f"{conf_bar(confidence, bar_w)}  "
            f"{dim(reason_clean)}"
        )

    print()


def verdict(action: str, confidence: float, consensus: float, blocked: bool = False, block_reason: str = "") -> None:
    """
    The hero moment — the final verdict.
    This is the most important visual in the entire output.
    """
    section("Verdict")

    if blocked:
        _black = "\033[30m"
        print(f"    {badge('NO TRADE', C.BG_YELLOW, _black)}  {dim(block_reason)}")
        print()
        print(f"    {dim('Signal was')} {action_text(action)} {dim('at')} {conf(confidence)} "
              f"{dim('confidence with')} {consensus:.0%} {dim('consensus')}")
        print(f"    {dim('but was blocked by risk management.')}")
    else:
        # Big prominent verdict
        print(f"    {action_badge(action)}  {conf_bar(confidence, 15)}  {conf(confidence)} {dim('confidence')}")
        print()
        print(f"    {dim('Consensus:')} {consensus:.0%} {dim('of teams agree')}")

    print()


def portfolio_card(summary: dict, positions: list = None) -> None:
    """Print portfolio summary as a compact card."""
    w = min(_term_width(), 72)
    bar = c("─" * w, C.DIM)

    print(f"  {bar}")
    print(f"  {C.BOLD}{C.WHITE}Portfolio{C.RESET}")
    print()

    total = summary["total_value"]
    ret = summary["return_pct"]

    # Main number — big and prominent
    ret_str = pct(ret)
    print(f"    {C.BOLD}${total:>14,.2f}{C.RESET}  {ret_str}")
    print()

    # Compact breakdown
    cash_str = dim(usd(summary["cash"]))
    pos_str = dim(usd(summary["positions_value"]))
    print(f"    {dim('Cash')} {cash_str}   {dim('Positions')} {pos_str}")

    total_pnl = summary["total_pnl"]
    if total_pnl != 0:
        print(f"    {dim('P&L')}  {pnl(total_pnl)}  {dim('|')}  "
              f"{dim('Realized')} {pnl(summary['realized_pnl'])}  "
              f"{dim('Unrealized')} {pnl(summary['unrealized_pnl'])}")

    if summary["drawdown_pct"] > 0:
        dd = summary["drawdown_pct"]
        print(f"    {dim('Drawdown')} {c(f'-{dd:.2f}%', C.B_RED)}")

    open_pos = summary["open_positions"]
    total_trades = summary["total_trades"]
    print(f"    {dim(f'{open_pos} positions  ·  {total_trades} trades')}")

    # Position details
    if positions:
        print()
        print(f"    {dim('Symbol'):<16} {dim('Side'):<8} {dim('Entry'):>12} {dim('Now'):>12} {dim('P&L'):>12} {dim('P&L%'):>8}")
        print(f"    {dim('─' * 60)}")
        for pos in positions:
            pnl_val = pos.unrealized_pnl
            pnl_pct_val = pos.pnl_pct * 100
            side_str = c(pos.side.value, C.B_GREEN if pos.side.value == "BUY" else C.B_RED)
            print(
                f"    {pos.symbol:<16} {side_str:<17} "
                f"${pos.entry_price:>10,.2f} ${pos.current_price:>10,.2f} "
                f"{pnl(pnl_val):>20} {pct(pnl_pct_val):>14}"
            )

    print()


def trade_fill(side: str, quantity: float, symbol: str, price: float, params=None) -> None:
    """Print a trade execution with risk parameters."""
    side_badge = action_badge(side)
    print(f"    {c('FILLED', C.B_GREEN)}  {side_badge} {quantity:.6f} {symbol} @ {bold(usd(price))}  {dim('[PAPER]')}")
    if params and params.stop_loss_price > 0:
        sl = params.stop_loss_price
        tp1 = params.take_profit_1
        risk = params.risk_amount_usd
        tier = params.asset_tier
        hours = params.max_holding_hours
        print(
            f"              {dim('SL')} ${sl:,.2f} ({params.stop_loss_pct:.1f}%)  "
            f"{dim('TP1')} ${tp1:,.2f}  "
            f"{dim('TP2')} ${params.take_profit_2:,.2f}  "
            f"{dim('risk')} ${risk:,.0f}  "
            f"{dim(f'{tier} · {hours}h max')}"
        )


def regime_card(regime: str, confidence: float, risk_multiplier: float, reasoning: str, elapsed: float) -> None:
    """Print the CEO's regime classification (legacy)."""
    _print_regime_badge(regime, confidence, risk_multiplier, elapsed)
    reason_clean = reasoning.replace("\n", " ")
    if len(reason_clean) > 60:
        reason_clean = reason_clean[:59] + "…"
    print(f"    {dim('Thesis')}   {dim(reason_clean)}")


def _print_regime_badge(regime: str, confidence: float, risk_multiplier: float, elapsed: float) -> None:
    regime_styles = {
        "bull": (C.BG_GREEN, C.B_WHITE, "BULL"),
        "bear": (C.BG_RED, C.B_WHITE, "BEAR"),
        "ranging": (C.BG_YELLOW, "\033[30m", "RANGING"),
        "crisis": (C.BG_RED, C.B_WHITE, "CRISIS"),
    }
    bg, fg, label = regime_styles.get(regime, (C.BG_GRAY, C.B_WHITE, regime.upper()))
    regime_badge = f"{C.BOLD}{bg}{fg} {label:^8} {C.RESET}"
    print(f"    {dim('Regime')}      {regime_badge}  {conf_bar(confidence)} {conf(confidence)}  {dim(f'{elapsed:.1f}s')}")
    mult_color = C.B_GREEN if risk_multiplier >= 1.0 else C.B_YELLOW if risk_multiplier >= 0.6 else C.B_RED
    print(f"    {dim('Risk')}        {c(f'{risk_multiplier:.1f}x', mult_color)} {dim('multiplier')}")


def strategic_directive_card(directive, elapsed: float) -> None:
    """Print the full CEO strategic directive."""
    _print_regime_badge(directive.regime.value, directive.regime_confidence, directive.risk_multiplier, elapsed)

    # Emergency halt
    if directive.emergency_halt:
        print(f"    {badge('EMERGENCY HALT', C.BG_RED, C.B_WHITE)}  {directive.halt_reason}")
        return

    # Sector weights
    weights = directive.sector_weights
    if weights:
        parts = []
        for sector, weight in sorted(weights.items(), key=lambda x: -x[1]):
            if weight >= 1.3:
                parts.append(c(f"{sector} {weight:.1f}x", C.B_GREEN))
            elif weight >= 0.8:
                parts.append(f"{sector} {weight:.1f}x")
            elif weight > 0:
                parts.append(c(f"{sector} {weight:.1f}x", C.B_YELLOW))
            else:
                parts.append(c(f"{sector} AVOID", C.B_RED))
        print(f"    {dim('Allocation')}  {dim(' · ').join(parts)}")

    # Focus strategy
    if directive.focus_strategy:
        focus = directive.focus_strategy
        if len(focus) > 70:
            focus = focus[:69] + "…"
        print(f"    {dim('Strategy')}    {bold(focus)}")

    # Reasoning
    if directive.reasoning:
        reason = directive.reasoning.replace("\n", " ")
        if len(reason) > 80:
            reason = reason[:79] + "…"
        print(f"    {dim('Thesis')}      {dim(reason)}")


def coin_selection_card(coins: list[str], scores: list, reasoning: str, elapsed: float) -> None:
    """Print the COO's coin selection."""
    coin_strs = []
    for coin in coins:
        base = coin.replace("USDT", "")
        coin_strs.append(bold(base))

    print(f"    {dim('Coins')}    {c('·', C.DIM).join(f' {cs} ' for cs in coin_strs)}  {dim(f'{elapsed:.1f}s')}")

    reason_clean = reasoning.replace("\n", " ")
    if len(reason_clean) > 60:
        reason_clean = reason_clean[:59] + "…"
    print(f"    {dim('Reason')}   {dim(reason_clean)}")


def coin_header(symbol: str, price: float, change: float) -> None:
    """Print a compact header for each coin being analyzed."""
    base = symbol.replace("USDT", "")
    print(f"\n    {C.BOLD}{C.WHITE}{base}{C.RESET}  "
          f"${price:,.2f}  {pct(change)}")


def multi_verdict_row(symbol: str, action: str, confidence: float, consensus: float, blocked: bool, reason: str = "") -> None:
    """Print one row in the multi-coin verdict table."""
    base = symbol.replace("USDT", "")

    if blocked:
        status = badge("SKIP", C.BG_YELLOW, "\033[30m")
        detail = dim(reason) if reason else ""
    else:
        status = action_badge(action)
        detail = f"{conf_bar(confidence)} {conf(confidence)}"

    print(f"    {base:<8}  {status}  {detail}  {dim(f'{consensus:.0%} consensus')}")


def cro_card(limits_dict: dict, reasoning: str, elapsed: float) -> None:
    """Print the CRO's risk rules."""
    pos_pct = limits_dict.get("max_position_pct", 0.05) * 100
    dd_pct = limits_dict.get("max_drawdown_pct", 0.03) * 100
    max_pos = limits_dict.get("max_open_positions", 10)
    min_conf = limits_dict.get("min_signal_confidence", 0.50) * 100
    min_cons = limits_dict.get("min_consensus_ratio", 0.50) * 100

    print(
        f"    {dim('Rules')}    "
        f"pos {bold(f'{pos_pct:.0f}%')}  "
        f"dd {bold(f'{dd_pct:.0f}%')}  "
        f"slots {bold(f'{max_pos}')}  "
        f"conf {bold(f'{min_conf:.0f}%')}  "
        f"cons {bold(f'{min_cons:.0f}%')}  "
        f"{dim(f'{elapsed:.1f}s')}"
    )

    reason_clean = reasoning.replace("\n", " ")
    if len(reason_clean) > 60:
        reason_clean = reason_clean[:59] + "…"
    print(f"    {dim('Posture')}  {dim(reason_clean)}")


def perf_review_card(review) -> None:
    """Print the Performance Agent's review (legacy)."""
    pass


def ceo_review_card(review: dict, elapsed: float) -> None:
    """Print the CEO's post-cycle review."""
    if not isinstance(review, dict):
        print(f"    {dim(f'Review unavailable (got {type(review).__name__})')}")
        print(f"    {dim(f'{elapsed:.1f}s')}")
        return
    # Team capital allocation decisions
    actions = review.get("team_actions", [])
    action_badges = {
        "INCREASE_CAPITAL": ("  +  ", C.BG_GREEN, C.B_WHITE),
        "MAINTAIN": ("  =  ", C.BG_GRAY, C.B_WHITE),
        "REDUCE_CAPITAL": ("  -  ", C.BG_YELLOW, "\033[30m"),
        "PROBATION": (" !!  ", C.BG_YELLOW, "\033[30m"),
        "FIRE": ("FIRE ", C.BG_RED, C.B_WHITE),
    }

    for a in actions:
        team = a.get("team", "?")
        action = a.get("action", "MAINTAIN")
        weight = a.get("new_weight", 1.0)
        reason = a.get("reason", "")

        badge_text, bg, fg = action_badges.get(action, ("  ?  ", C.BG_GRAY, C.B_WHITE))
        b = badge(badge_text, bg, fg)

        weight_str = f"{weight:.1f}x"
        if weight > 1.0:
            weight_str = c(weight_str, C.B_GREEN)
        elif weight < 1.0:
            weight_str = c(weight_str, C.B_YELLOW)
        elif weight == 0:
            weight_str = c("0.0x", C.B_RED)

        reason_short = reason[:50] + "…" if len(reason) > 50 else reason
        print(f"    {b}  {team:<14} {weight_str:>14}  {dim(reason_short)}")

    # Strategy adjustment
    strat_adj = review.get("strategy_adjustment", "")
    if strat_adj:
        print(f"\n    {dim('Next cycle:')}  {bold(strat_adj[:70])}")

    # Override
    override = review.get("override_action", "NONE")
    if override != "NONE":
        override_reason = review.get("override_reason", "")
        print(f"\n    {badge(override, C.BG_RED, C.B_WHITE)}  {override_reason}")

    # Regime validation
    regime_valid = review.get("regime_still_valid", True)
    if not regime_valid:
        print(f"    {c('Regime call was WRONG', C.B_YELLOW)} — will adjust next cycle")

    # Assessment
    assess = review.get("assessment", "").replace("\n", " ")
    if len(assess) > 80:
        assess = assess[:79] + "…"
    print(f"    {dim(assess)}")
    print(f"    {dim(f'{elapsed:.1f}s')}")


def pm_summary(segment_exposure: dict[str, float], orders_in: int, orders_out: int) -> None:
    """Print the PM layer summary."""
    if segment_exposure:
        parts = []
        for seg, pct_val in sorted(segment_exposure.items(), key=lambda x: -x[1]):
            parts.append(f"{seg} {pct_val:.0f}%")
        print(f"    {dim('Exposure')}  {dim(' · ').join(parts)}")

    if orders_in != orders_out:
        filtered = orders_in - orders_out
        print(f"    {dim('Orders')}    {orders_in} submitted → {orders_out} approved  "
              f"{dim(f'({filtered} filtered by segment limits)')}")
    elif orders_in > 0:
        print(f"    {dim('Orders')}    {orders_out} approved by PMs")
    else:
        print(f"    {dim('No orders to review.')}")


def footer() -> None:
    """Print closing line."""
    print(f"  {dim('─' * min(_term_width(), 72))}")
    print(f"  {dim('Analysis complete.')}\n")
