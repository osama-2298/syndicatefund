#!/usr/bin/env python3
"""
Hivemind Simulation — Watch the entire AI hedge fund pipeline in action.
No API keys needed. Uses simulated data to demonstrate the full flow.
"""

import random
import time
import sys

# ── ANSI Colors ──
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"
GRAY = "\033[90m"
BG_GREEN = "\033[42m"
BG_RED = "\033[41m"
BG_YELLOW = "\033[43m"
BG_CYAN = "\033[46m"
BG_GRAY = "\033[100m"

def c(text, color): return f"{color}{text}{RESET}"
def bold(text): return f"{BOLD}{text}{RESET}"
def dim(text): return f"{DIM}{text}{RESET}"

def badge(text, bg, fg=WHITE):
    return f"{BOLD}{bg}{fg} {text} {RESET}"

def action_badge(action):
    styles = {
        "BUY": (BG_GREEN, WHITE), "SELL": (BG_RED, WHITE),
        "SHORT": (BG_RED, WHITE), "HOLD": (BG_YELLOW, "\033[30m"),
    }
    bg, fg = styles.get(action, (BG_GRAY, WHITE))
    return f"{BOLD}{bg}{fg}{action:^7}{RESET}"

def conf_bar(val, width=10):
    filled = int(val * width)
    color = GREEN if val >= 0.7 else YELLOW if val >= 0.55 else RED
    return f"{color}{'█' * filled}{RESET}{DIM}{'░' * (width - filled)}{RESET}"

def conf_pct(val):
    color = GREEN if val >= 0.7 else YELLOW if val >= 0.55 else RED
    return c(f"{val:.0%}", color)

def pct(val):
    color = GREEN if val > 0 else RED if val < 0 else DIM
    return c(f"{val:+.2f}%", color)

def section(title):
    print(f"\n  {c('─' * 72, DIM)}")
    print(f"  {BOLD}{WHITE}{title}{RESET}\n")

def typing(text, delay=0.02):
    """Print text character by character for dramatic effect."""
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def slow_print(text, delay=0.05):
    """Print with a short pause for readability."""
    time.sleep(delay)
    print(text)

# ── Simulated Data ──

COINS = {
    "BTCUSDT": {"price": 97_432.50, "change": 2.34, "sector": "L1"},
    "ETHUSDT": {"price": 3_821.40, "change": -1.12, "sector": "L1"},
    "SOLUSDT": {"price": 187.65, "change": 5.67, "sector": "L1"},
    "ARBUSDT": {"price": 1.42, "change": -3.21, "sector": "L2"},
    "PEPEUSDT": {"price": 0.00001834, "change": 12.45, "sector": "Meme"},
}

TEAMS = [
    ("Technical",   BLUE,    ["TrendAgent(1D)", "SignalAgent(4H)", "TimingAgent(1H)"]),
    ("Sentiment",   MAGENTA, ["SocialAgent", "MarketAgent", "SmartMoneyAgent"]),
    ("Fundamental", YELLOW,  ["ValuationAgent", "CycleAgent"]),
    ("Macro",       CYAN,    ["CryptoMacroAgent", "ExternalMacroAgent"]),
    ("On-Chain",    GREEN,   ["NetworkAgent", "CapitalFlowAgent"]),
]


def simulate():
    print(f"\n{c('━' * 72, CYAN)}")
    print(f"  {BOLD}{CYAN}HIVEMIND{RESET}  {dim('Distributed AI Hedge Fund — SIMULATION MODE')}")
    print(c('━' * 72, CYAN))
    print()
    print(f"    {dim('Mode')}     {c('SIMULATION', YELLOW)} {dim('(no API keys needed)')}")
    print(f"    {dim('Teams')}    {c('Technical', BLUE)}  {c('Sentiment', MAGENTA)}  {c('Fundamental', YELLOW)}  {c('Macro', CYAN)}  {c('On-Chain', GREEN)}")
    print(f"    {dim('Time')}     {dim('2026-03-14 12:00 UTC')}")
    time.sleep(1)

    # ═══════════════════════════════════════
    # STEP 0: Trade Monitor
    # ═══════════════════════════════════════
    section("Step 0 — Trade Monitor (checking previous trades)")
    time.sleep(0.5)

    prev_trades = [
        ("LINK", "TP1 (33%)", 18.42, 4.2, 156.80, 72),
        ("AVAX", "STOP LOSS", 38.10, -2.8, -224.00, 48),
    ]
    for sym, reason, price, pnl_pct, pnl_usd, hours in prev_trades:
        icon = c("WIN", GREEN) if pnl_pct > 0 else c("LOSS", RED)
        slow_print(f"    {icon}  {sym} {reason} @ ${price:,.2f} → {pct(pnl_pct)} (${pnl_usd:+,.2f}) in {hours}h", 0.3)

    print(f"    {dim('1W / 1L  |  Net P&L: -$67.20')}")
    time.sleep(0.5)

    # ═══════════════════════════════════════
    # STEP 1: Intelligence Gathering
    # ═══════════════════════════════════════
    section("Step 1 — Intelligence Gathering (11 data sources)")
    time.sleep(0.5)

    intel_sources = [
        ("Fear & Greed",  "72/100 (Greed) trend: rising",         0.4),
        ("Reddit",        "847 posts · 64% bullish · HIGH engagement", 0.6),
        ("CoinGecko",     "BTC dom 52.3% · market +1.8% 24h",    0.3),
        ("Trending",      "PEPE, WIF, SOL, RENDER, TIA",          0.2),
        ("DeFiLlama",     "TVL $98.4B · 142 chains",              0.4),
        ("Polymarket",    "105 markets · top: Fed rate cut Jun (72%)", 0.5),
        ("Binance Spot",  "BTCUSDT 200 candles @ 4H",             0.2),
        ("Derivatives",   "funding +0.0124% · OI 68,421 BTC",    0.3),
        ("Blockchain",    "hash 645 EH/s · 312K tx · mempool 14K", 0.3),
        ("Whale Flows",   "2,341,050 BTC across 89 exchange wallets", 0.2),
        ("CoinPaprika",   "Beta values for 5 coins",              0.2),
    ]

    for name, detail, delay in intel_sources:
        slow_print(f"    {dim(f'{name:<16}')} {detail}", delay)

    print(f"    {dim('All 11 sources fetched in parallel · 3.2s')}")
    time.sleep(0.5)

    # ═══════════════════════════════════════
    # STEP 2: CEO Strategic Directive
    # ═══════════════════════════════════════
    section("Step 2 — CEO Strategic Directive")
    time.sleep(0.3)

    print(f"    {dim('CEO loading knowledge base...')} {dim('4,800 lines of crypto history')}")
    time.sleep(0.8)
    print(f"    {dim('CEO analyzing 3 prior cycles of experience...')}")
    time.sleep(0.6)

    regime_badge = f"{BOLD}{BG_GREEN}{WHITE} {'BULL':^8} {RESET}"
    print(f"    {dim('Regime')}      {regime_badge}  {conf_bar(0.78)} {conf_pct(0.78)}  {dim('4.2s')}")
    mult_color = GREEN
    print(f"    {dim('Risk')}        {c('1.1x', mult_color)} {dim('multiplier')}")
    print(f"    {dim('Allocation')}  {c('L1 1.3x', GREEN)} · DeFi 1.0x · {c('L2 0.8x', YELLOW)} · {c('Meme 0.5x', YELLOW)}")
    print(f"    {dim('Strategy')}    {bold('Favor high-cap L1s on pullbacks. BTC post-halving momentum intact.')}")
    print(f"    {dim('Thesis')}      {dim('F&G at 72 with rising trend. BTC above 200D SMA. Funding positive but not overheated.')}")
    time.sleep(0.5)

    # ═══════════════════════════════════════
    # STEP 3: COO Coin Selection
    # ═══════════════════════════════════════
    section("Step 3 — COO Coin Selection")
    time.sleep(0.3)

    print(f"    {dim('Scanning 487 USDT pairs on Binance...')}")
    time.sleep(0.5)
    print(f"    {dim('Filtering by volume > $10M 24h...')}")
    time.sleep(0.3)

    coin_strs = " · ".join(bold(s.replace("USDT", "")) for s in COINS)
    print(f"    {dim('Coins')}    {coin_strs}  {dim('3.1s')}")
    print(f"    {dim('Reason')}   {dim('BTC/ETH core + SOL momentum play + ARB L2 value + PEPE viral surge')}")
    time.sleep(0.3)

    # Hot coin injection
    print(f"    {c('HOT', MAGENTA)} {bold('PEPE')}  {dim('Reddit surge + CoinGecko trending #1')}")
    time.sleep(0.5)

    # ═══════════════════════════════════════
    # STEP 4: Data Enrichment
    # ═══════════════════════════════════════
    section("Step 4 — Data Layer (Per-Coin Enrichment)")
    time.sleep(0.3)

    print(f"    {dim('BTC On-Chain')}    hash 645 EH/s · 312,481 tx · mempool 14,203")
    print(f"    {dim('Derivatives')}    funding +0.0124% · OI 68,421 BTC · taker 1.032 · whales 54%L")
    print(f"    {dim('Whale Flows')}    2,341,050 BTC across 89 exchange wallets")
    print(f"    {dim('Enrichment')}     5/5 CoinGecko · 5/5 derivatives · 5/5 CoinPaprika · 3/5 chain TVL")
    print(f"    {dim('Per-coin data loaded in 2.8s')}")
    time.sleep(0.5)

    # ═══════════════════════════════════════
    # STEP 5: CRO Risk Rules
    # ═══════════════════════════════════════
    section("Step 5 — CRO Risk Rules")
    time.sleep(0.3)

    print(
        f"    {dim('Rules')}    "
        f"pos {bold('8%')}  "
        f"dd {bold('5%')}  "
        f"slots {bold('6')}  "
        f"conf {bold('60%')}  "
        f"cons {bold('55%')}  "
        f"{dim('2.1s')}"
    )
    print(f"    {dim('Posture')}  {dim('Moderately aggressive — bull regime, increase position sizes, tighten meme limits')}")
    time.sleep(0.5)

    # ═══════════════════════════════════════
    # STEP 6: Agent Analysis (the big one!)
    # ═══════════════════════════════════════
    section(f"Step 6 — Agent Analysis ({len(COINS)} coins × 5 teams = 60 AI calls)")

    # Pre-generate all results for consistency
    coin_results = {}
    for symbol, info in COINS.items():
        teams_result = []
        for team_name, team_color, agents in TEAMS:
            agent_results = []
            team_direction = random.choice(["BULLISH", "BEARISH"])
            for agent_name in agents:
                direction = team_direction if random.random() > 0.3 else ("BEARISH" if team_direction == "BULLISH" else "BULLISH")
                conviction = random.randint(3, 9)
                elapsed = random.uniform(1.5, 5.0)
                agent_results.append((agent_name, direction, conviction, elapsed))

            # Manager synthesis
            avg_conv = sum(a[2] for a in agent_results) / len(agent_results)
            agree = sum(1 for a in agent_results if a[1] == team_direction) / len(agent_results)
            manager_conf = min(0.95, avg_conv / 10 * (0.5 + 0.5 * agree))
            manager_action = "BUY" if team_direction == "BULLISH" else "SHORT"
            teams_result.append((team_name, team_color, agent_results, manager_action, manager_conf, agree))

        coin_results[symbol] = teams_result

    for symbol, info in COINS.items():
        base = symbol.replace("USDT", "")
        price = info["price"]
        change = info["change"]
        print(f"\n    {BOLD}{WHITE}{base}{RESET}  ${price:,.2f}  {pct(change)}")
        time.sleep(0.3)

        for team_name, team_color, agent_results, mgr_action, mgr_conf, agree in coin_results[symbol]:
            # Print sub-agents
            for agent_name, direction, conviction, elapsed in agent_results:
                slow_print(
                    f"      {dim(f'{agent_name:<18}')} {direction} {conviction}/10  {dim(f'{elapsed:.1f}s')}",
                    0.08
                )

            # Print manager synthesis
            tf_str = ""
            if team_name == "Technical":
                tf_str = " [partial alignment]"

            print(
                f"    {c(team_name, team_color)}  "
                f"{action_badge(mgr_action)}  "
                f"{conf_bar(mgr_conf)} {conf_pct(mgr_conf)}  "
                f"{dim(f'{agree:.0%} agree{tf_str}  {random.uniform(2, 4):.1f}s')}"
            )
            time.sleep(0.15)

    time.sleep(0.5)

    # ═══════════════════════════════════════
    # STEP 7: Signal Aggregation
    # ═══════════════════════════════════════
    section("Step 7 — Signal Aggregation (conflict-aware)")
    time.sleep(0.3)

    agg_results = {}
    for symbol in COINS:
        teams = coin_results[symbol]
        buy_count = sum(1 for t in teams if t[3] == "BUY")
        consensus = buy_count / len(teams)
        avg_conf = sum(t[4] for t in teams) / len(teams)
        action = "BUY" if buy_count >= 3 else "SHORT" if buy_count <= 1 else "HOLD"
        agg_results[symbol] = (action, avg_conf, consensus)

        base = symbol.replace("USDT", "")
        alerts = []
        if consensus >= 0.8:
            alerts.append(f"    {c('*', GREEN)} {base}: {dim('[INFO] UNANIMOUS — 4+/5 teams aligned')}")
        elif consensus <= 0.4:
            alerts.append(f"    {c('!', RED)} {base}: {dim('[HIGH] CONFLICT — teams sharply divided')}")

        for a in alerts:
            slow_print(a, 0.1)

    time.sleep(0.5)

    # ═══════════════════════════════════════
    # STEP 8: Risk Manager
    # ═══════════════════════════════════════
    section("Step 8 — Risk Manager (ATR-based stops)")
    time.sleep(0.3)

    for symbol, (action, conf, consensus) in agg_results.items():
        base = symbol.replace("USDT", "")
        if action != "HOLD":
            tier = {"BTCUSDT": "BTC", "ETHUSDT": "Top 5", "SOLUSDT": "Large", "ARBUSDT": "Mid", "PEPEUSDT": "Meme"}[symbol]
            sl_mult = {"BTC": 2.0, "Top 5": 2.5, "Large": 3.0, "Mid": 3.5, "Meme": 4.5}[tier]
            risk_pct = {"BTC": 1.5, "Top 5": 1.2, "Large": 1.0, "Mid": 0.75, "Meme": 0.25}[tier]
            slow_print(f"    {base:<8}  SL: {sl_mult}x ATR  Risk: {risk_pct}%  Tier: {tier}", 0.15)

    time.sleep(0.5)

    # ═══════════════════════════════════════
    # STEP 9: Portfolio Managers
    # ═══════════════════════════════════════
    section("Step 9 — Portfolio Managers (sector allocation)")
    time.sleep(0.3)

    print(f"    {dim('Exposure')}  L1 45% · DeFi 12% · L2 8% · Meme 3%")
    tradeable = [s for s, (a, _, _) in agg_results.items() if a != "HOLD"]
    blocked_by_pm = max(0, len(tradeable) - 3)
    print(f"    {dim('Orders')}    {len(tradeable)} submitted → {len(tradeable) - blocked_by_pm} approved  {dim(f'({blocked_by_pm} filtered by segment limits)')}")
    time.sleep(0.5)

    # ═══════════════════════════════════════
    # STEP 10: Verdicts
    # ═══════════════════════════════════════
    section("Step 10 — Verdicts")
    time.sleep(0.3)

    final_trades = []
    for i, (symbol, (action, conf, consensus)) in enumerate(agg_results.items()):
        base = symbol.replace("USDT", "")
        blocked = (action == "HOLD") or (conf < 0.6) or (consensus < 0.55) or (i >= len(tradeable) - blocked_by_pm + 3)

        if blocked:
            reason = ""
            if action == "HOLD":
                reason = "agents recommend HOLD"
            elif conf < 0.6:
                reason = f"conf {conf:.0%} < 60%"
            elif consensus < 0.55:
                reason = f"consensus {consensus:.0%} < 55%"
            else:
                reason = "risk/PM rules"
            status = badge("SKIP", BG_YELLOW, "\033[30m")
            detail = dim(reason)
        else:
            status = action_badge(action)
            detail = f"{conf_bar(conf)} {conf_pct(conf)}"
            final_trades.append((symbol, action, conf))

        slow_print(f"    {base:<8}  {status}  {detail}  {dim(f'{consensus:.0%} consensus')}", 0.2)

    time.sleep(0.5)

    # ═══════════════════════════════════════
    # STEP 11: Execution
    # ═══════════════════════════════════════
    if final_trades:
        section("Step 11 — Execution (Paper Trading)")
        time.sleep(0.3)

        for symbol, action, conf in final_trades:
            price = COINS[symbol]["price"]
            # Calculate position size based on risk
            risk_usd = 100_000 * 0.01  # 1% of portfolio
            quantity = risk_usd / price

            side = action
            side_badge = action_badge(side)
            print(f"    {c('FILLED', GREEN)}  {side_badge} {quantity:.6f} {symbol} @ {bold(f'${price:,.2f}')}  {dim('[PAPER]')}")

            # Show risk params
            sl_pct = random.uniform(3, 8)
            sl_price = price * (1 - sl_pct / 100) if side == "BUY" else price * (1 + sl_pct / 100)
            tp1 = price * (1 + sl_pct * 1.5 / 100) if side == "BUY" else price * (1 - sl_pct * 1.5 / 100)
            tp2 = price * (1 + sl_pct * 3 / 100) if side == "BUY" else price * (1 - sl_pct * 3 / 100)
            tier = {"BTCUSDT": "BTC", "ETHUSDT": "Top 5", "SOLUSDT": "Large", "ARBUSDT": "Mid", "PEPEUSDT": "Meme"}.get(symbol, "Mid")
            hours = {"BTC": 450, "Top 5": 300, "Large": 210, "Mid": 150, "Meme": 60}.get(tier, 150)
            print(
                f"              {dim('SL')} ${sl_price:,.2f} ({sl_pct:.1f}%)  "
                f"{dim('TP1')} ${tp1:,.2f}  "
                f"{dim('TP2')} ${tp2:,.2f}  "
                f"{dim('risk')} ${risk_usd:,.0f}  "
                f"{dim(f'{tier} · {hours}h max')}"
            )
            time.sleep(0.4)

    # ═══════════════════════════════════════
    # Portfolio Summary
    # ═══════════════════════════════════════
    total_invested = len(final_trades) * 1000
    total_value = 100_000 - total_invested + total_invested * random.uniform(0.99, 1.01)
    ret = (total_value / 100_000 - 1) * 100

    print(f"\n  {c('─' * 72, DIM)}")
    print(f"  {BOLD}{WHITE}Portfolio{RESET}\n")
    print(f"    {BOLD}${total_value:>14,.2f}{RESET}  {pct(ret)}")
    print()
    print(f"    {dim('Cash')} {dim(f'${100_000 - total_invested:,.2f}')}   {dim('Positions')} {dim(f'${total_invested:,.2f}')}")
    print(f"    {dim(f'{len(final_trades)} positions  ·  {len(final_trades) + 2} trades')}")
    time.sleep(0.5)

    # ═══════════════════════════════════════
    # STEP 12: CEO Post-Cycle Review
    # ═══════════════════════════════════════
    section("Step 12 — CEO Post-Cycle Review")
    time.sleep(0.3)

    team_actions = [
        ("Technical",   "INCREASE_CAPITAL", 1.2, "Strong directional calls, 68% accuracy"),
        ("Sentiment",   "MAINTAIN",         1.0, "Adequate performance, needs more cycle data"),
        ("Fundamental", "MAINTAIN",         1.0, "Consistent but conservative calls"),
        ("Macro",       "REDUCE_CAPITAL",   0.7, "Missed rate cut signal, overweight recession fear"),
        ("On-Chain",    "MAINTAIN",         1.0, "Whale flow detection improving"),
    ]

    action_badges_map = {
        "INCREASE_CAPITAL": ("  +  ", BG_GREEN, WHITE),
        "MAINTAIN": ("  =  ", BG_GRAY, WHITE),
        "REDUCE_CAPITAL": ("  -  ", BG_YELLOW, "\033[30m"),
    }

    for team, action, weight, reason in team_actions:
        badge_text, bg, fg = action_badges_map[action]
        b = badge(badge_text, bg, fg)
        weight_str = f"{weight:.1f}x"
        if weight > 1.0:
            weight_str = c(weight_str, GREEN)
        elif weight < 1.0:
            weight_str = c(weight_str, YELLOW)
        slow_print(f"    {b}  {team:<14} {weight_str:>14}  {dim(reason)}", 0.2)

    print(f"\n    {dim('Next cycle:')}  {bold('Increase L1 exposure on dips. Watch for Fed signal reversal.')}")
    print(f"    {dim('Cycle performed within expectations. Technical team promoted. Macro team on watch.')}")
    print(f"    {dim('4.8s')}")
    time.sleep(0.5)

    # ═══════════════════════════════════════
    # Trade Ledger
    # ═══════════════════════════════════════
    section("Trade Ledger — Lifetime Performance")
    print(f"    {dim('Total trades:    14')}")
    print(f"    {dim('Win rate:        57% (8W / 6L)')}")
    print(f"    {dim('Net P&L:         +$1,247.83')}")
    print(f"    {dim('Best trade:      SOL +8.4% ($672)')}")
    print(f"    {dim('Worst trade:     ARB -5.2% (-$416)')}")
    print(f"    {dim('Avg hold time:   94h')}")
    print(f"    {dim('Current streak:  2W')}")
    time.sleep(0.3)

    # ═══════════════════════════════════════
    # Timing Summary
    # ═══════════════════════════════════════
    n_coins = len(COINS)
    n_llm = 4 + (17 * n_coins)
    print(f"\n  {dim(f'Completed in 47.3s · 5 coins · 25 signals · {n_llm} LLM calls')}")

    print(f"\n  {c('─' * 72, DIM)}")
    print(f"  {dim('Simulation complete.')}\n")
    print(f"  {dim('To run with real data:')}")
    print(f"  {dim('  1. Add ANTHROPIC_API_KEY to .env')}")
    print(f"  {dim('  2. python -m hivemind.main')}\n")


if __name__ == "__main__":
    simulate()
