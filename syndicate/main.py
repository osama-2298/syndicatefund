"""
Syndicate — Multi-Coin Pipeline Orchestrator

Architecture flow:
  1. CEO classifies market regime (BTC as proxy)
  2. COO selects which coins to analyze
  3. Data Layer fetches ALL external data (Reddit, CoinGecko, DeFiLlama, Blockchain.com, Fear&Greed)
  4. CRO sets risk rules for this cycle
  5. For each coin: 5 agent teams (Technical, Sentiment, Fundamental, Macro, On-Chain)
  6. Aggregate signals per coin
  7. Risk Manager enforces CRO rules
  8. Portfolio Managers approve/filter by segment
  9. Execute orders via paper trader
 10. Performance Agent reviews and fires/promotes

TODO(Fix 12): Add backtesting — multi-day historical replay with LLM caching.
TODO(Fix 14): Add static knowledge injection — requires curator pipeline or RAG system.
"""

from __future__ import annotations

import logging
import signal
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import structlog

# Sub-agents
from syndicate.agents.technical.trend_agent import TechnicalTrendAgent
from syndicate.agents.technical.signal_agent import TechnicalSignalAgent
from syndicate.agents.technical.timing_agent import TechnicalTimingAgent
from syndicate.agents.sentiment.social_agent import SocialSentimentAgent
from syndicate.agents.sentiment.market_agent import MarketSentimentAgent
from syndicate.agents.sentiment.smart_money_agent import SmartMoneySentimentAgent
from syndicate.agents.fundamental.valuation_agent import ValuationAgent
from syndicate.agents.fundamental.cycle_agent import CyclePositionAgent
from syndicate.agents.macro.crypto_macro_agent import CryptoMacroAgent
from syndicate.agents.macro.external_macro_agent import ExternalMacroAgent
from syndicate.agents.onchain.network_agent import NetworkHealthAgent
from syndicate.agents.onchain.capital_flow_agent import CapitalFlowAgent
# Team managers
from syndicate.agents.technical.technical_manager import TechnicalManager
from syndicate.agents.sentiment.sentiment_manager import SentimentManager
from syndicate.agents.fundamental.fundamental_manager import FundamentalManager
from syndicate.agents.macro.macro_manager import MacroManager
from syndicate.agents.onchain.onchain_manager import OnChainManager
from syndicate.aggregator.signal_aggregator import SignalAggregator
from syndicate.config import settings
from syndicate.data.binance_client import BinanceClient
from syndicate.data.data_layer import DataLayer, MarketSnapshot
from syndicate.data.models import (
    AgentProfile,
    AggregatedSignal,
    Signal,
    SignalAction,
    TeamType,
)
from syndicate.data.technical_indicators import compute_indicators
from syndicate.display import (
    C,
    agent_result,
    banner,
    c,
    coin_header,
    coin_selection_card,
    conf,
    cro_card,
    dim,
    footer,
    multi_verdict_row,
    pct,
    ceo_review_card,
    pm_summary,
    portfolio_card,
    regime_card,
    section,
    strategic_directive_card,
    trade_fill,
)
from syndicate.evaluation.performance_tracker import PerformanceTracker
from syndicate.executive.ceo_agent import CEOAgent
from syndicate.executive.coo_agent import COOAgent
from syndicate.executive.cro_agent import CROAgent
# PerfAgent removed — CEO absorbs the performance review role (post-cycle)
from syndicate.execution.paper_trader import PaperTrader
from syndicate.execution.trade_ledger import TradeLedger
from syndicate.execution.trade_monitor import TradeMonitor
from syndicate.portfolio.manager import PortfolioManagerGroup
from syndicate.risk.risk_manager import RiskManager
from syndicate.core.cycle_snapshot import CycleSnapshot
from syndicate.core.events import emit_event, get_collector, start_cycle_collector, save_events_json, persist_events

logger = structlog.get_logger()

# Quiet structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(colors=True),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
logging.basicConfig(level=logging.WARNING)


def _save_latest_signals(signals: list):
    """Save latest aggregated signals for the API."""
    import json
    from pathlib import Path
    try:
        data = {
            "cycle_timestamp": datetime.now(timezone.utc).isoformat(),
            "signals": [
                {
                    "symbol": s.symbol,
                    "action": s.recommended_action.value,
                    "confidence": round(s.aggregated_confidence, 3),
                    "consensus": round(s.consensus_ratio, 3),
                    "decision_quality": s.weighted_scores.get("_decision_quality", ""),
                    "alerts": s.weighted_scores.get("_alerts", []),
                }
                for s in signals
            ],
        }
        path = Path("data/latest_signals.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))
    except Exception:
        pass  # Non-critical


def _run_single_agent(agent_cls, team_type, symbol, data, api_key, provider):
    """Run a single agent. Thread-safe — each call creates its own agent instance."""
    profile = AgentProfile(
        team=team_type, symbol=symbol,
        model=settings.default_llm_model, provider=provider.value,
    )
    agent = agent_cls(profile=profile, api_key=api_key, provider=provider)
    t0 = time.monotonic()
    signal = agent.analyze(data)
    elapsed = time.monotonic() - t0
    agent_name = agent_cls.__name__.replace("Agent", "").replace("Technical", "")
    return signal, agent_name, elapsed


def _run_team(
    team_name: str,
    team_type: TeamType,
    agent_classes: list,
    manager_cls,
    data: dict,
    symbol: str,
    api_key: str,
    provider,
    executor,
) -> tuple[Signal, list[str]]:
    """
    Run all agents in a team IN PARALLEL, then synthesize through the manager.
    Sub-agents are independent — they never see each other's output.
    """
    from concurrent.futures import Future

    # Launch all sub-agents in parallel
    futures: list[Future] = []
    for agent_cls in agent_classes:
        fut = executor.submit(
            _run_single_agent, agent_cls, team_type, symbol, data, api_key, provider,
        )
        futures.append(fut)

    # Collect results (order preserved)
    agent_signals = []
    display_lines = []
    for fut in futures:
        signal, agent_name, elapsed = fut.result()
        direction = signal.metadata.get("direction", signal.action.value)
        conviction = signal.metadata.get("conviction", int(signal.confidence * 10))
        display_lines.append(f"      {dim(agent_name):<18} {direction} {conviction}/10  {dim(f'{elapsed:.1f}s')}")
        agent_signals.append(signal)

    # Display sub-agent results
    for line in display_lines:
        print(line)

    # Manager synthesizes (sequential — needs all agent signals)
    manager = manager_cls(api_key=api_key, provider=provider, model=settings.default_llm_model)
    t0 = time.monotonic()
    team_signal = manager.synthesize(agent_signals, symbol)
    mgr_elapsed = time.monotonic() - t0

    # Convert TeamSignal to Signal for the aggregator
    final_signal = team_signal.to_signal()

    # Display manager result
    from syndicate.display import action_badge, conf_bar, conf
    agree_str = f"{team_signal.agreement_level:.0%} agree"
    tf_str = f" [{team_signal.timeframe_alignment}]" if team_signal.timeframe_alignment and team_signal.timeframe_alignment != "N/A" else ""
    mgr_line = (
        f"    {c(team_name, C.B_WHITE)}  "
        f"{action_badge(final_signal.action.value)}  "
        f"{conf_bar(final_signal.confidence)} {conf(final_signal.confidence)}  "
        f"{dim(f'{agree_str}{tf_str}  {mgr_elapsed:.1f}s')}"
    )

    return final_signal, [*display_lines, mgr_line]


def _analyze_coin(
    symbol: str,
    snapshot: MarketSnapshot,
    api_key: str,
    provider,
) -> tuple[list[Signal], dict[str, AgentProfile], float]:
    """
    Run all 5 agent teams for a single coin IN PARALLEL.
    Within each team, sub-agents also run in parallel.
    Only manager signals go to the aggregator (5 signals, not 12).

    Parallelization:
      5 teams in parallel (each independent, different data slices)
        └─ Within each: 2-3 sub-agents in parallel, then manager sequential
    """
    from concurrent.futures import ThreadPoolExecutor, Future

    coin = snapshot.coins.get(symbol)
    if coin is None or coin.indicators is None:
        return [], {}, 0.0

    coin_header(symbol, coin.current_price, coin.stats_24h.get("price_change_pct", 0))

    # Team-specific data packets (strict separation)
    team_data = {
        TeamType.TECHNICAL: snapshot.for_technical(symbol),
        TeamType.SENTIMENT: snapshot.for_sentiment(symbol),
        TeamType.FUNDAMENTAL: snapshot.for_fundamental(symbol),
        TeamType.MACRO: snapshot.for_macro(symbol),
        TeamType.ONCHAIN: snapshot.for_onchain(symbol),
    }

    teams = [
        ("Technical", TeamType.TECHNICAL,
         [TechnicalTrendAgent, TechnicalSignalAgent, TechnicalTimingAgent],
         TechnicalManager),
        ("Sentiment", TeamType.SENTIMENT,
         [SocialSentimentAgent, MarketSentimentAgent, SmartMoneySentimentAgent],
         SentimentManager),
        ("Fundamental", TeamType.FUNDAMENTAL,
         [ValuationAgent, CyclePositionAgent],
         FundamentalManager),
        ("Macro", TeamType.MACRO,
         [CryptoMacroAgent, ExternalMacroAgent],
         MacroManager),
        ("On-Chain", TeamType.ONCHAIN,
         [NetworkHealthAgent, CapitalFlowAgent],
         OnChainManager),
    ]

    # Run all 5 teams in parallel
    # Each team internally parallelizes its sub-agents
    # Max workers: 5 teams × 3 agents = 15 concurrent LLM calls (safe for Anthropic rate limits)
    with ThreadPoolExecutor(max_workers=15) as executor:
        team_futures: list[tuple[str, TeamType, Future]] = []

        for team_name, team_type, agent_classes, manager_cls in teams:
            fut = executor.submit(
                _run_team,
                team_name, team_type, agent_classes, manager_cls,
                team_data[team_type], symbol, api_key, provider,
                executor,  # Share the executor for sub-agent parallelism
            )
            team_futures.append((team_name, team_type, fut))

        # Collect results and display in order
        all_manager_signals = []
        agent_profiles = {}

        for team_name, team_type, fut in team_futures:
            try:
                manager_signal, display_lines = fut.result()

                # Display (buffered per team for clean output)
                for line in display_lines:
                    print(line)

                # Set price metadata
                manager_signal.metadata["current_price"] = coin.current_price
                manager_signal.metadata["stats_24h"] = coin.stats_24h
                if coin.indicators_4h and coin.indicators_4h.atr_14:
                    manager_signal.metadata["atr_14"] = coin.indicators_4h.atr_14

                all_manager_signals.append(manager_signal)

                mgr_profile = AgentProfile(
                    agent_id=f"manager_{team_type.value}",
                    team=team_type, symbol=symbol,
                    model=settings.default_llm_model, provider=provider.value,
                )
                agent_profiles[mgr_profile.agent_id] = mgr_profile

            except Exception as e:
                logger.error("team_failed", team=team_name, symbol=symbol, error=str(e))

    return all_manager_signals, agent_profiles, coin.current_price


# ═══════════════════════════════════════════════════════════════════
#  DYNAMIC PIPELINE — uses AgentRegistry to load teams/agents from DB
# ═══════════════════════════════════════════════════════════════════


def _run_single_agent_dynamic(agent_def, registry, symbol, data):
    """Run a single agent via the registry. Thread-safe."""
    agent = registry.instantiate_agent(agent_def, symbol)
    t0 = time.monotonic()
    sig = agent.analyze(data)
    elapsed = time.monotonic() - t0
    return sig, elapsed


def _run_team_dynamic(
    team_name,
    team_agents,
    team_manager_prompt,
    data,
    symbol,
    registry,
    executor,
):
    """Run all agents in a team via the registry, then synthesize through the manager."""
    from concurrent.futures import Future

    futures: list[tuple] = []
    for agent_def in team_agents:
        fut = executor.submit(_run_single_agent_dynamic, agent_def, registry, symbol, data)
        futures.append((agent_def, fut))

    agent_signals = []
    display_lines = []
    for agent_def, fut in futures:
        try:
            sig, elapsed = fut.result()
            direction = sig.metadata.get("direction", sig.action.value)
            conviction = sig.metadata.get("conviction", int(sig.confidence * 10))
            name = agent_def.role[:16]
            display_lines.append(f"      {dim(name):<18} {direction} {conviction}/10  {dim(f'{elapsed:.1f}s')}")
            agent_signals.append(sig)
        except Exception as e:
            logger.error("agent_failed", agent=agent_def.role, error=str(e))

    if not agent_signals:
        return None, display_lines

    # Manager synthesizes
    manager = registry.get_manager_for_team(team_name, team_manager_prompt)
    t0 = time.monotonic()
    team_signal = manager.synthesize(agent_signals, symbol)
    mgr_elapsed = time.monotonic() - t0

    final_signal = team_signal.to_signal()

    from syndicate.display import action_badge, conf_bar
    agree_str = f"{team_signal.agreement_level:.0%} agree"
    tf_str = f" [{team_signal.timeframe_alignment}]" if team_signal.timeframe_alignment and team_signal.timeframe_alignment != "N/A" else ""
    mgr_line = (
        f"    {c(team_name, C.B_WHITE)}  "
        f"{action_badge(final_signal.action.value)}  "
        f"{conf_bar(final_signal.confidence)} {conf(final_signal.confidence)}  "
        f"{dim(f'{agree_str}{tf_str}  {mgr_elapsed:.1f}s')}"
    )

    return final_signal, [*display_lines, mgr_line]


def _analyze_coin_dynamic(
    symbol,
    snapshot,
    registry,
):
    """Registry-based coin analysis — supports founding + contributor agents."""
    from concurrent.futures import ThreadPoolExecutor, Future

    coin = snapshot.coins.get(symbol)
    if coin is None or coin.indicators is None:
        return [], {}, 0.0

    coin_header(symbol, coin.current_price, coin.stats_24h.get("price_change_pct", 0))

    # System teams use the existing for_X() methods for backward compatibility
    _SYSTEM_DATA_METHODS = {
        "technical": snapshot.for_technical,
        "sentiment": snapshot.for_sentiment,
        "fundamental": snapshot.for_fundamental,
        "macro": snapshot.for_macro,
        "onchain": snapshot.for_onchain,
    }

    all_teams = registry.get_all_teams()

    with ThreadPoolExecutor(max_workers=15) as executor:
        team_futures: list[tuple[str, Future]] = []

        for team_id, agents in all_teams.items():
            meta = registry.get_team_meta(team_id)
            if meta is None:
                continue
            team_name = meta["name"]

            # Get data for this team
            system_method = _SYSTEM_DATA_METHODS.get(team_name)
            if system_method:
                data = system_method(symbol)
            else:
                data = snapshot.for_team(meta.get("data_keys", []), symbol)

            if not data:
                continue

            fut = executor.submit(
                _run_team_dynamic,
                team_name, agents, meta.get("manager_prompt"),
                data, symbol, registry, executor,
            )
            team_futures.append((team_name, fut))

        all_manager_signals = []
        agent_profiles = {}

        for team_name, fut in team_futures:
            try:
                result = fut.result()
                if result is None:
                    continue
                final_signal, display_lines = result
                if final_signal is None:
                    continue

                for line in display_lines:
                    print(line)

                final_signal.metadata["current_price"] = coin.current_price
                final_signal.metadata["stats_24h"] = coin.stats_24h
                if coin.indicators_4h and coin.indicators_4h.atr_14:
                    final_signal.metadata["atr_14"] = coin.indicators_4h.atr_14

                all_manager_signals.append(final_signal)

                mgr_profile = AgentProfile(
                    agent_id=f"manager_{team_name}",
                    team=team_name, symbol=symbol,
                    model=settings.default_llm_model,
                    provider=settings.default_llm_provider.value,
                )
                agent_profiles[mgr_profile.agent_id] = mgr_profile

            except Exception as e:
                logger.error("team_failed", team=team_name, symbol=symbol, error=str(e))

    return all_manager_signals, agent_profiles, coin.current_price


def run_pipeline(
    interval: str = "4h",
    candle_count: int = 200,
    binance: BinanceClient | None = None,
    registry=None,
) -> None:
    """Run the full multi-coin pipeline with real data from all sources.

    If ``registry`` is provided (an AgentRegistry loaded from the DB), uses
    dynamic team/agent discovery. Otherwise falls back to the hardcoded
    founding agents — no database required.
    """
    now_utc = datetime.now(timezone.utc)
    now = now_utc.strftime("%Y-%m-%d %H:%M UTC")
    banner("Multi-Coin Cycle", now)

    # Check if this is a decision cycle
    is_decision_cycle = True
    if settings.decision_mode == "daily":
        is_decision_cycle = now_utc.hour < 4  # Only first cycle of the day (00:00 UTC)

    api_key = settings.get_active_llm_key()
    provider = settings.default_llm_provider
    max_coins = settings.max_coins_per_cycle
    cycle_start = time.monotonic()
    cycle_start_wall = time.time()  # Wall-clock for DB record
    start_cycle_collector()
    snapshot_data = CycleSnapshot(timestamp=now_utc.isoformat())

    _binance = binance or BinanceClient()
    _owns_binance = binance is None
    paper_trader = PaperTrader.load(settings.portfolio_state_path)
    tracker = PerformanceTracker(storage_path=settings.perf_history_path)

    # CEO memory — persists across cycles
    from syndicate.executive.ceo_memory import CEOMemory
    ceo_memory = CEOMemory(storage_path=settings.ceo_memory_path)
    trade_monitor = TradeMonitor(storage_path=settings.open_trades_path)
    trade_ledger = TradeLedger(storage_path=settings.trade_ledger_path)

    from syndicate.executive.team_weights import TeamWeightManager, PhaseWeightManager
    team_weights = TeamWeightManager(storage_path=settings.team_weights_path)
    phase_weights = PhaseWeightManager(storage_path=str(Path(settings.team_weights_path).parent / "phase_weights.json"))

    # Diagnostic: detect orphan trades (trade monitor has trade but portfolio has no position)
    if trade_monitor.open_trades:
        for sym in trade_monitor.open_trades:
            if paper_trader.portfolio.get_position(sym) is None:
                logger.warning("orphan_trade", symbol=sym,
                              msg="Trade monitor has open trade but portfolio has no position")

    try:
        # ═══════════════════════════════════════
        # STEP 0: Check Open Trades from Previous Cycles
        # ═══════════════════════════════════════
        if trade_monitor.open_trades:
            section("Trade Monitor — Checking Open Positions")
            outcomes = trade_monitor.check_all(_binance, paper_trader=paper_trader, interval="1h")
            # Record outcomes in the ledger and wire back to signal accuracy
            for o in outcomes:
                trade_ledger.record_outcome(o)
                # Task 2.4: update signal accuracy from actual trade P&L
                if o.source_signal_id:
                    tracker.evaluate_from_trade_outcome(
                        signal_id=o.source_signal_id,
                        profitable=(o.pnl_usd > 0),
                    )
            if outcomes:
                for o in outcomes:
                    # Color based on outcome
                    if o.pnl_pct > 0:
                        icon = c("WIN", C.B_GREEN)
                    elif o.pnl_pct < 0:
                        icon = c("LOSS", C.B_RED)
                    else:
                        icon = dim("FLAT")
                    base = o.symbol.replace("USDT", "")
                    print(f"    {icon}  {base} {o.exit_reason} @ ${o.exit_price:,.2f} "
                          f"→ {o.pnl_pct:+.1%} (${o.pnl_usd:+,.2f}) in {o.holding_hours:.0f}h")
                # Summary
                wins = sum(1 for o in outcomes if o.pnl_pct > 0)
                losses = sum(1 for o in outcomes if o.pnl_pct < 0)
                total_pnl = sum(o.pnl_usd for o in outcomes)
                print(f"    {dim(f'{wins}W / {losses}L  |  Net P&L: ${total_pnl:+,.2f}')}")
            else:
                n = len(trade_monitor.open_trades)
                print(f"    {dim(f'{n} open positions — no exits triggered')}")
        # ═══════════════════════════════════════
        # STEP 1: Intelligence Gathering (ALL SOURCES IN PARALLEL)
        # ═══════════════════════════════════════
        section("Intelligence Gathering")

        from concurrent.futures import ThreadPoolExecutor
        from syndicate.data.fear_greed import get_fear_greed
        from syndicate.data.reddit import get_crypto_reddit_sentiment
        from syndicate.data.coingecko import CoinGeckoClient
        from syndicate.data.defi_llama import DeFiLlamaClient
        from syndicate.data.polymarket import PolymarketClient

        # BTC data for CEO (quick, 2 calls)
        btc_candles = _binance.get_klines(symbol="BTCUSDT", interval="4h", limit=200)
        btc_stats = _binance.get_24h_stats(symbol="BTCUSDT")
        btc_indicators = compute_indicators(btc_candles, "BTCUSDT")

        intel: dict = {}
        t0 = time.monotonic()

        # Define all intelligence fetchers
        def _fetch_fg():
            return "fear_greed", get_fear_greed(days=7)

        def _fetch_reddit():
            return "reddit_sentiment", get_crypto_reddit_sentiment(limit_per_sub=10)

        def _fetch_coingecko():
            g = CoinGeckoClient()
            try:
                gm = g.get_global()
                trending = g.get_trending()
                return "coingecko", {"global_market": gm, "trending": trending}
            finally:
                g.close()

        def _fetch_defillama():
            ll = DeFiLlamaClient()
            try:
                summary = ll.get_defi_summary()
                unlocks = ll.get_token_unlocks()
                dex_volumes = ll.get_dex_volumes()
                return "defi_data", {
                    "defi_summary": summary,
                    "token_unlocks": unlocks,
                    "dex_volumes": dex_volumes,
                }
            finally:
                ll.close()

        def _fetch_polymarket():
            p = PolymarketClient()
            try:
                return "prediction_markets", p.get_all_relevant_markets()
            finally:
                p.close()

        def _fetch_liquidations():
            from syndicate.data.liquidations import LiquidationMonitor
            lm = LiquidationMonitor()
            try:
                return "liquidations", lm.get_recent_liquidations()
            finally:
                lm.close()

        def _fetch_news_sentiment():
            from syndicate.data.news_sentiment import NewsSentimentClient
            nc = NewsSentimentClient(auth_token=getattr(settings, 'cryptopanic_api_key', ''))
            try:
                return "news_sentiment", nc.get_news_sentiment()
            finally:
                nc.close()

        # Run ALL intelligence sources in parallel
        with ThreadPoolExecutor(max_workers=8) as intel_executor:
            futures = [
                intel_executor.submit(_fetch_fg),
                intel_executor.submit(_fetch_reddit),
                intel_executor.submit(_fetch_coingecko),
                intel_executor.submit(_fetch_defillama),
                intel_executor.submit(_fetch_polymarket),
                intel_executor.submit(_fetch_liquidations),
                intel_executor.submit(_fetch_news_sentiment),
            ]

            for fut in futures:
                try:
                    key, data = fut.result()
                    if key == "coingecko":
                        intel["global_market"] = data["global_market"]
                        intel["trending"] = data["trending"]
                    else:
                        intel[key] = data
                except Exception as e:
                    logger.warning("intel_fetch_failed", error=str(e))

        # Display results
        if intel.get("fear_greed"):
            fg = intel["fear_greed"]
            print(f"    {dim('Fear & Greed')}     {fg['current_value']}/100 ({fg['current_label']}) trend: {fg.get('trend', '?')}")
        if intel.get("reddit_sentiment"):
            rs = intel["reddit_sentiment"]
            ratio_pct = round(rs.get("sentiment_ratio", 0.5) * 100)
            print(f"    {dim('Reddit')}          {rs['total_posts']} posts · {ratio_pct}% bullish · {rs['engagement_level']} engagement")
        if intel.get("global_market"):
            gm = intel["global_market"]
            print(f"    {dim('CoinGecko')}       BTC dom {gm.get('btc_dominance', 0):.1f}% · market {gm.get('market_cap_change_24h_pct', 0):+.1f}% 24h")
        if intel.get("trending"):
            names = [t["symbol"] for t in intel["trending"][:5]]
            print(f"    {dim('Trending')}        {', '.join(names)}")
        if intel.get("defi_data"):
            ds = intel["defi_data"].get("defi_summary", {})
            if ds:
                print(f"    {dim('DeFiLlama')}      TVL ${ds.get('total_tvl', 0):,.0f} · {ds.get('num_chains', 0)} chains")

            # Token unlocks
            unlocks = intel["defi_data"].get("token_unlocks", [])
            high_risk = [u for u in unlocks if u.get("risk_level") == "HIGH"]
            if high_risk:
                for u in high_risk[:3]:
                    print(f"    {c('UNLOCK', C.B_YELLOW)} {u['symbol']} — {u['unlock_pct']:.1f}% supply in {u['days_until']}d")

            # DEX volumes
            dex = intel["defi_data"].get("dex_volumes", {})
            if dex.get("total_24h_volume"):
                change = dex.get("volume_change_24h_pct", 0)
                print(f"    {dim('DEX Volume')}     ${dex['total_24h_volume']/1e9:.1f}B 24h ({change:+.1f}%)")
        if intel.get("prediction_markets"):
            pred = intel["prediction_markets"]
            highlights = pred.get("highlights", [])
            if highlights:
                top = highlights[0]
                q = top.get("question", "?")[:50]
                probs = top.get("probabilities", {})
                prob_str = " / ".join(f"{k}:{v:.0f}%" for k, v in list(probs.items())[:2])
                n_markets = len(pred.get("crypto", [])) + len(pred.get("fed", [])) + len(pred.get("economy", []))
                print(f"    {dim('Polymarket')}     {n_markets} markets · top: {q} ({prob_str})")
        if intel.get("liquidations"):
            liq = intel["liquidations"]
            if liq["intensity"] != "LOW":
                print(f"    {dim('Liquidations')}   {liq['intensity']} — ${liq['total_long_liquidated_usd']/1e6:.1f}M longs, ${liq['total_short_liquidated_usd']/1e6:.1f}M shorts ({liq['net_direction']})")
        if intel.get("news_sentiment"):
            ns = intel["news_sentiment"]
            if ns["overall_sentiment"] != "UNKNOWN":
                n_articles = ns["bullish_count"] + ns["bearish_count"] + ns["neutral_count"]
                ratio_pct = round(ns["sentiment_ratio"] * 100)
                print(f"    {dim('News')}            {n_articles} articles · {ratio_pct}% bullish · {ns['overall_sentiment']}")
                if ns["important_news"]:
                    top = ns["important_news"][0]
                    print(f"    {dim('Top Story')}       {top['title'][:60]} ({top['sentiment']})")

        intel_elapsed = time.monotonic() - t0
        print(f"    {dim(f'All sources fetched in parallel · {intel_elapsed:.1f}s')}")

        # ═══════════════════════════════════════
        # DATA-ONLY CYCLE (daily mode)
        # ═══════════════════════════════════════
        if not is_decision_cycle:
            section("Data-Only Cycle")
            print(f"    {c('Data-only cycle', C.B_YELLOW)} (daily mode — next decision at 00:00 UTC)")
            print(f"    {dim('Trade monitoring + intelligence gathered. Skipping analysis/execution.')}")

            # Update prices for existing positions
            position_symbols = []
            if paper_trader.portfolio.positions:
                position_symbols = [p.symbol for p in paper_trader.portfolio.positions]
            if position_symbols:
                price_updates = {}
                for sym in position_symbols:
                    try:
                        stats = _binance.get_24h_stats(symbol=sym)
                        price_updates[sym] = float(stats.get("last_price", 0))
                    except Exception:
                        pass
                if price_updates:
                    paper_trader.update_prices(price_updates)
                    print(f"    {dim(f'Updated prices for {len(price_updates)} positions')}")

            paper_trader.save(settings.portfolio_state_path)

            elapsed_total = time.monotonic() - cycle_start
            print(f"\n  {dim(f'Data-only cycle completed in {elapsed_total:.1f}s')}")
            footer()
            return

        # ═══════════════════════════════════════
        # STEP 2: CEO — Strategic Directive
        # ═══════════════════════════════════════
        section("CEO — Strategic Directive")

        portfolio_summary = paper_trader.get_summary()
        perf_summary = tracker.get_summary()

        ceo = CEOAgent(api_key=api_key, provider=provider, model=settings.default_llm_model)
        last_feedback = ceo_memory.get_last_feedback()
        experience = ceo_memory.get_experience_summary()
        t0 = time.monotonic()
        directive = ceo.direct(
            btc_indicators, btc_stats, intel, portfolio_summary, perf_summary,
            last_feedback, experience,
        )
        ceo_elapsed = time.monotonic() - t0

        if ceo_memory.cycle_count > 0:
            print(f"    {dim(f'CEO experience: {ceo_memory.cycle_count} prior cycles')}")
        strategic_directive_card(directive, ceo_elapsed)

        # Emergency halt check
        if directive.emergency_halt:
            print(f"\n    {c('EMERGENCY HALT — All trading suspended.', C.B_RED)}")
            print(f"    {dim(directive.halt_reason)}")
            footer()
            return

        # ═══════════════════════════════════════
        # STEP 3: COO — Coin Selection (guided by CEO strategy)
        # ═══════════════════════════════════════
        section("COO — Coin Selection")

        t0 = time.monotonic()
        all_stats = _binance.get_all_24h_stats(
            quote_asset="USDT",
            min_volume=settings.min_volume_24h,
        )
        # Pass CEO's focus strategy to COO
        intel["ceo_focus_strategy"] = directive.focus_strategy
        intel["ceo_sector_weights"] = directive.sector_weights
        coo = COOAgent(api_key=api_key, provider=provider, model=settings.default_llm_model)
        selection = coo.select(all_stats, directive.regime, max_coins=max_coins, extra_intelligence=intel)
        coo_elapsed = time.monotonic() - t0

        coin_selection_card(
            selection.selected_coins, selection.scores,
            selection.reasoning, coo_elapsed,
        )

        selected_coins = selection.selected_coins
        if not selected_coins:
            print(f"\n    {dim('No coins selected. Exiting.')}")
            footer()
            return

        # ═══════════════════════════════════════
        # STEP 3b: Hot Coin Injection
        # ═══════════════════════════════════════
        from syndicate.data.hot_coins import detect_hot_coins
        hot_additions = detect_hot_coins(intel, selected_coins, max_additions=3)

        if hot_additions:
            # Verify hot coins exist on Binance AND aren't already selected
            all_binance_symbols = {s["symbol"] for s in all_stats}
            selected_set = set(selected_coins)
            verified_hot = [
                h for h in hot_additions
                if h["symbol"] in all_binance_symbols and h["symbol"] not in selected_set
            ]

            if verified_hot:
                for h in verified_hot:
                    selected_coins.append(h["symbol"])
                    selected_set.add(h["symbol"])
                    base = h["symbol"].replace("USDT", "")
                    print(f"    {c('HOT', C.B_MAGENTA)} {c(base, C.B_WHITE)}  {dim(h['reason'])}")

        # ═══════════════════════════════════════
        # STEP 4: Data Layer — Per-Coin Enrichment
        # ═══════════════════════════════════════
        section("Data Layer — Per-Coin Enrichment")

        data_layer = DataLayer()
        t0 = time.monotonic()
        snapshot = data_layer.fetch_all(selected_coins)
        data_layer.close()
        data_elapsed = time.monotonic() - t0

        # CRITICAL: Set intel on snapshot BEFORE agent analysis begins.
        # Agents read from snapshot via for_sentiment(), for_macro(), etc.
        # This MUST happen after fetch_all() and BEFORE _analyze_coin().
        snapshot.fear_greed = intel.get("fear_greed")
        snapshot.reddit_sentiment = intel.get("reddit_sentiment")
        snapshot.global_market = intel.get("global_market", {})
        snapshot.trending_coins = intel.get("trending", [])
        snapshot.prediction_markets = intel.get("prediction_markets")
        snapshot.news_sentiment = intel.get("news_sentiment")

        # DeFiLlama data — defi_summary may come from defi_data dict or DataLayer enrichment
        defi_data = intel.get("defi_data", {})
        if defi_data:
            if not snapshot.defi_summary and defi_data.get("defi_summary"):
                snapshot.defi_summary = defi_data["defi_summary"]
            if defi_data.get("token_unlocks"):
                snapshot.token_unlocks = defi_data["token_unlocks"]
            if defi_data.get("dex_volumes"):
                snapshot.dex_volumes = defi_data["dex_volumes"]

        # Show enrichment stats
        enriched_gecko = sum(1 for c in snapshot.coins.values() if c.coingecko)
        enriched_deriv = sum(1 for c in snapshot.coins.values() if c.derivatives)
        enriched_paprika = sum(1 for c in snapshot.coins.values() if c.paprika)
        chain_data = sum(1 for c in snapshot.coins.values() if c.chain_tvl)
        if snapshot.btc_onchain:
            bc = snapshot.btc_onchain
            print(f"    {dim('BTC On-Chain')}    hash {bc.get('network_power_eh', 0)} EH/s · {bc.get('n_transactions_24h', 0):,} tx · mempool {bc.get('mempool_count', '?')}")
        # Show derivatives snapshot for BTC
        btc_coin = snapshot.coins.get("BTCUSDT")
        if btc_coin and btc_coin.derivatives:
            d = btc_coin.derivatives
            funding = d.get("funding", {})
            oi = d.get("open_interest", {})
            taker = d.get("taker_volume", {})
            top_ls = d.get("top_trader_ls", {})
            parts = []
            if funding:
                parts.append(f"funding {funding.get('current_rate_pct', 0):+.4f}%")
            if oi:
                parts.append(f"OI {oi.get('open_interest', 0):,.0f} BTC")
            if taker:
                parts.append(f"taker {taker.get('buy_sell_ratio', 1):.3f}")
            if top_ls:
                parts.append(f"whales {top_ls.get('long_pct', 50):.0f}%L")
            if parts:
                print(f"    {dim('Derivatives')}    {' · '.join(parts)}")
            divergence = d.get("smart_money_divergence", "ALIGNED")
            if divergence != "ALIGNED":
                print(f"    {dim('Smart Money')}    {divergence}")
        # Whale flows
        if snapshot.whale_flows:
            wf = snapshot.whale_flows
            total_btc = wf.get("total_exchange_btc", 0)
            n_wallets = wf.get("num_wallets_tracked", 0)
            print(f"    {dim('Whale Flows')}    {total_btc:,.0f} BTC across {n_wallets} exchange wallets")

        n = len(selected_coins)
        print(f"    {dim('Enrichment')}     {enriched_gecko}/{n} CoinGecko · {enriched_deriv}/{n} derivatives · {enriched_paprika}/{n} CoinPaprika · {chain_data}/{n} chain TVL")

        if snapshot.errors:
            for err in snapshot.errors:
                print(f"    {dim('Warning')}        {dim(err)}")

        print(f"    {dim(f'Per-coin data loaded in {data_elapsed:.1f}s')}")

        # ═══════════════════════════════════════
        # STEP 5: CRO — Risk Rules
        # ═══════════════════════════════════════
        section("CRO — Risk Rules")

        cro_perf_summary = tracker.get_summary()
        cro = CROAgent(api_key=api_key, provider=provider, model=settings.default_llm_model)
        t0 = time.monotonic()
        risk_limits, cro_reasoning = cro.set_rules(directive, paper_trader.portfolio, cro_perf_summary)
        cro_elapsed = time.monotonic() - t0

        cro_card(
            {
                "max_position_pct": risk_limits.max_position_pct,
                "max_daily_drawdown_pct": risk_limits.max_daily_drawdown_pct,
                "max_open_positions": risk_limits.max_open_positions,
                "min_signal_confidence": risk_limits.min_signal_confidence,
                "min_consensus_ratio": risk_limits.min_consensus_ratio,
            },
            cro_reasoning,
            cro_elapsed,
        )

        # ═══════════════════════════════════════
        # STEP 6: Analyze Each Coin
        # ═══════════════════════════════════════
        if registry:
            n_teams = len(registry.get_all_teams())
            n_agents = sum(len(a) for a in registry.get_all_teams().values())
            section(f"Agent Analysis — {len(selected_coins)} coins × {n_teams} teams ({n_agents} agents)")
        else:
            section(f"Agent Analysis — {len(selected_coins)} coins × 5 teams")

        all_coin_signals: list[Signal] = []
        all_agent_profiles: dict[str, AgentProfile] = {}
        coin_prices: dict[str, float] = {}

        from concurrent.futures import ThreadPoolExecutor as _CoinPool, as_completed

        if registry:
            def _analyze_and_collect(sym):
                return sym, _analyze_coin_dynamic(sym, snapshot, registry)
        else:
            def _analyze_and_collect(sym):
                return sym, _analyze_coin(sym, snapshot, api_key, provider)

        with _CoinPool(max_workers=2) as coin_pool:
            futs = {coin_pool.submit(_analyze_and_collect, s): s for s in selected_coins}
            for fut in as_completed(futs):
                sym, (signals, profiles, price) = fut.result()
                all_coin_signals.extend(signals)
                all_agent_profiles.update(profiles)
                coin_prices[sym] = price

        # Hydrate agent profiles with historical track record
        agent_historical = tracker.get_agent_stats()
        for agent_id, profile in all_agent_profiles.items():
            hist = agent_historical.get(agent_id)
            if hist and hist["total"] > 0:
                profile.total_signals = hist["total"]
                profile.correct_signals = hist["correct"]

        # ═══════════════════════════════════════
        # STEP 6: Aggregate per coin
        # ═══════════════════════════════════════
        # Build calibration data from trade ledger for conviction adjustment
        calibration_raw = trade_ledger.get_calibration().get("by_conviction", {})
        calibration_data = None
        if calibration_raw:
            calibration_data = {}
            for conv_str, data in calibration_raw.items():
                conv = int(conv_str) if isinstance(conv_str, str) else conv_str
                if data.get("count", 0) >= 3:  # Only calibrate with sufficient data
                    calibration_data[conv] = {
                        "actual_win_rate": data.get("win_rate", 0) / 100.0,
                        "expected_win_rate": conv * 10 / 100.0,
                    }

        # Update phase weights from trade history (4-phase progressive learning)
        closed_trades = len([e for e in trade_ledger.entries if e.exit_reason != "OPEN"])
        phase_weights.update_from_tracker(tracker, closed_trades)
        final_weights = phase_weights.get_weights(team_weights.weights)

        phase_label = {1: "Equal", 2: "Shrunk IC", 3: "Full IC", 4: "IC+Thompson"}
        weight_strs = "  ".join(f"{t[:4]}={w:.2f}" for t, w in final_weights.items())
        print(f"    Phase {phase_weights.phase} ({phase_label[phase_weights.phase]}, {closed_trades} trades): {weight_strs}")

        aggregator = SignalAggregator(
            team_weight_overrides=final_weights,
            regime=directive.regime.value,
            calibration_data=calibration_data,
        )
        aggregated = aggregator.aggregate(all_coin_signals, all_agent_profiles)

        # Persist latest signals for API
        _save_latest_signals(aggregated)

        # Display aggregation alerts
        for agg in aggregated:
            alerts = agg.weighted_scores.get("_alerts", [])
            quality = agg.weighted_scores.get("_decision_quality", "")
            if alerts:
                base = agg.symbol.replace("USDT", "")
                for alert_str in alerts:
                    if "[HIGH]" in alert_str:
                        print(f"    {c('!', C.B_RED)} {base}: {dim(alert_str)}")
                    elif "[MEDIUM]" in alert_str:
                        print(f"    {c('~', C.B_YELLOW)} {base}: {dim(alert_str)}")
                    elif "[INFO]" in alert_str and "UNANIMOUS" in alert_str:
                        print(f"    {c('*', C.B_GREEN)} {base}: {dim(alert_str)}")

        # ═══════════════════════════════════════
        # STEP 7: Risk Manager (enforces CRO rules) + Signal Funnel Tracking
        # ═══════════════════════════════════════
        # Track signal funnel — how many signals are killed at each stage
        funnel = {
            "signals_generated": len(aggregated),
            "after_hold_filter": 0,
            "after_confidence_filter": 0,
            "after_consensus_filter": 0,
            "after_drawdown_check": 0,
            "after_position_limit": 0,
            "after_risk_manager": 0,
            "after_portfolio_manager": 0,
        }

        # Count signals surviving each filter stage
        non_hold = [a for a in aggregated if a.recommended_action != SignalAction.HOLD]
        funnel["after_hold_filter"] = len(non_hold)

        above_confidence = [a for a in non_hold if a.aggregated_confidence >= risk_limits.min_signal_confidence]
        funnel["after_confidence_filter"] = len(above_confidence)

        above_consensus = [a for a in above_confidence if a.consensus_ratio >= risk_limits.min_consensus_ratio]
        funnel["after_consensus_filter"] = len(above_consensus)

        risk_manager = RiskManager(limits=risk_limits, regime=directive.regime)
        risk_orders = risk_manager.evaluate(aggregated, paper_trader.portfolio)
        funnel["after_risk_manager"] = len(risk_orders)

        # ═══════════════════════════════════════
        # STEP 8: Portfolio Managers (segment allocation)
        # ═══════════════════════════════════════
        section("Portfolio Managers")
        pm_group = PortfolioManagerGroup(ceo_sector_weights=directive.sector_weights)
        orders_before_pm = len(risk_orders)
        final_orders = pm_group.review(risk_orders, paper_trader.portfolio)
        orders_after_pm = len(final_orders)
        funnel["after_portfolio_manager"] = orders_after_pm
        segment_exposure = pm_group.get_segment_exposure(paper_trader.portfolio)
        pm_summary(segment_exposure, orders_before_pm, orders_after_pm)

        # ── Signal Funnel Display ──
        section("Signal Funnel")
        fg = funnel["signals_generated"]
        killed_hold = fg - funnel["after_hold_filter"]
        killed_conf = funnel["after_hold_filter"] - funnel["after_confidence_filter"]
        killed_cons = funnel["after_confidence_filter"] - funnel["after_consensus_filter"]
        killed_risk = funnel["after_consensus_filter"] - funnel["after_risk_manager"]
        killed_pm = funnel["after_risk_manager"] - funnel["after_portfolio_manager"]
        print(f"    Signals generated:      {fg}")
        print(f"    {dim('→')} After HOLD filter:     {funnel['after_hold_filter']:<4} ({killed_hold} killed, HOLD)")
        print(f"    {dim('→')} After confidence:      {funnel['after_confidence_filter']:<4} ({killed_conf} killed, < {risk_limits.min_signal_confidence:.0%})")
        print(f"    {dim('→')} After consensus:       {funnel['after_consensus_filter']:<4} ({killed_cons} killed, < {risk_limits.min_consensus_ratio:.0%})")
        print(f"    {dim('→')} After risk manager:    {funnel['after_risk_manager']:<4} ({killed_risk} killed, position/drawdown)")
        print(f"    {dim('→')} After PM filter:       {funnel['after_portfolio_manager']:<4} ({killed_pm} killed, segment limits)")
        conversion = (funnel["after_portfolio_manager"] / max(fg, 1)) * 100
        print(f"    {dim(f'Conversion rate: {conversion:.1f}%')}")

        # Minimum-trade warning
        if funnel["after_portfolio_manager"] < 2:
            logger.warning(
                "low_trade_count",
                orders_produced=funnel["after_portfolio_manager"],
                signals_generated=fg,
                conversion_pct=round(conversion, 1),
                funnel=funnel,
            )
            print(f"    {c('WARNING', C.B_YELLOW)}: Only {funnel['after_portfolio_manager']} orders produced from {fg} signals ({conversion:.1f}% conversion)")

        # Store funnel for CEO post-cycle review context
        _cycle_funnel = funnel

        # ═══════════════════════════════════════
        # STEP 9: Verdicts
        # ═══════════════════════════════════════
        section("Verdicts")
        agg_by_symbol: dict[str, AggregatedSignal] = {a.symbol: a for a in aggregated}
        traded_symbols = {o.symbol for o in final_orders}

        for symbol in selected_coins:
            agg = agg_by_symbol.get(symbol)
            if agg is None:
                multi_verdict_row(symbol, "HOLD", 0, 0, blocked=True, reason="no signal")
                continue

            blocked = symbol not in traded_symbols
            reason = ""
            if blocked:
                if agg.recommended_action.value == "HOLD":
                    reason = "agents recommend HOLD"
                elif agg.aggregated_confidence < risk_limits.min_signal_confidence:
                    reason = f"conf {agg.aggregated_confidence:.0%} < {risk_limits.min_signal_confidence:.0%}"
                elif agg.consensus_ratio < risk_limits.min_consensus_ratio:
                    reason = f"consensus {agg.consensus_ratio:.0%} < {risk_limits.min_consensus_ratio:.0%}"
                else:
                    reason = "risk/PM rules"

            multi_verdict_row(
                symbol, agg.recommended_action.value,
                agg.aggregated_confidence, agg.consensus_ratio,
                blocked=blocked, reason=reason,
            )

        # ═══════════════════════════════════════
        # STEP 10: Execution
        # ═══════════════════════════════════════
        if final_orders:
            section("Execution")
            results = paper_trader.execute_batch(final_orders)
            order_by_symbol = {o.symbol: o for o in final_orders}
            for result in results:
                order = order_by_symbol.get(result.symbol)
                params = order.params if order else None
                trade_fill(result.side.value, result.quantity, result.symbol, result.executed_price, params)

                # Register trade for monitoring + ledger
                if order and order.params.stop_loss_price > 0:
                    trade_monitor.register_trade(
                        symbol=result.symbol,
                        side=result.side,
                        entry_price=result.executed_price,
                        quantity=result.quantity,
                        params=order.params,
                        source_signal_id=order.source_signal_id,
                    )
                    agg = agg_by_symbol.get(result.symbol)
                    trade_ledger.record_entry(
                        symbol=result.symbol,
                        side=result.side.value,
                        entry_price=result.executed_price,
                        quantity=result.quantity,
                        asset_tier=order.params.asset_tier,
                        risk_amount=order.params.risk_amount_usd,
                        stop_loss=order.params.stop_loss_price,
                        take_profit_1=order.params.take_profit_1,
                        conviction=int(agg.aggregated_confidence * 10) if agg else 0,
                        confidence=agg.aggregated_confidence if agg else 0.0,
                        direction=agg.recommended_action.value if agg else "",
                        regime=directive.regime.value,
                        source_signal_id=order.source_signal_id,
                    )
            paper_trader.update_prices(coin_prices)
            paper_trader.save(settings.portfolio_state_path)

        summary = paper_trader.get_summary()
        portfolio_card(summary, paper_trader.portfolio.positions or None)

        # ═══════════════════════════════════════
        # STEP 11: Performance Tracking
        # ═══════════════════════════════════════
        tracker.record_signals(all_coin_signals, coin_prices)
        eval_results = tracker.evaluate_pending(coin_prices)

        if eval_results["evaluated"] > 0:
            print(f"    {dim('Evaluated:')} {eval_results['correct']}/{eval_results['evaluated']} correct")

        # ═══════════════════════════════════════
        # STEP 12: CEO Post-Cycle Review
        # ═══════════════════════════════════════
        section("CEO — Post-Cycle Review")

        team_stats = tracker.get_team_stats()
        perf_summary_after = tracker.get_summary()

        t0 = time.monotonic()
        ceo_feedback = ceo.review(
            directive, all_coin_signals, aggregated,
            len(final_orders), summary, team_stats, perf_summary_after,
        )
        review_elapsed = time.monotonic() - t0

        from syndicate.display import ceo_review_card
        ceo_review_card(ceo_feedback, review_elapsed)

        # Apply CEO team weight decisions for next cycle
        ceo_team_actions = ceo_feedback.get("team_actions", [])
        if ceo_team_actions:
            team_weights.apply_ceo_decisions(ceo_team_actions)

        # Collect trade outcomes as feedback
        trade_feedback = trade_monitor.get_feedback_summary()

        # Persist CEO memory with trade outcomes included
        ceo_memory.record_cycle(
            directive={
                "regime": directive.regime.value,
                "risk_multiplier": directive.risk_multiplier,
                "sector_weights": directive.sector_weights,
                "focus_strategy": directive.focus_strategy,
            },
            results={
                "coins_analyzed": len(selected_coins),
                "signals_generated": len(all_coin_signals),
                "orders_executed": len(final_orders),
                "portfolio_return": summary["return_pct"],
                "drawdown": summary["drawdown_pct"],
                "fear_greed": intel.get("fear_greed", {}).get("current_value", 0),
                "btc_price": coin_prices.get("BTCUSDT", 0),
                "btc_change_24h": float(btc_stats.get("price_change_pct", 0)),
                "btc_dominance": intel.get("global_market", {}).get("btc_dominance", 0),
                "trade_outcomes": trade_feedback,  # Feed trade results into CEO memory
                "ledger_stats": trade_ledger.get_stats(),
                "signal_funnel": _cycle_funnel,  # Signal conversion funnel
            },
            feedback=ceo_feedback,
        )

        # Timing
        elapsed_total = time.monotonic() - cycle_start
        n_signals = len(all_coin_signals)
        n_coins = len(selected_coins)
        n_hot = len(hot_additions) if hot_additions else 0
        n_coo = n_coins - n_hot
        # CEO pre + CEO post + COO + CRO + (agents + managers) per coin
        if registry:
            n_agents_total = sum(len(a) for a in registry.get_all_teams().values())
            n_teams_total = len(registry.get_all_teams())
            n_llm_calls = 4 + ((n_agents_total + n_teams_total) * n_coins)
        else:
            n_llm_calls = 4 + (17 * n_coins)
        hot_str = f" + {n_hot} hot" if n_hot else ""
        print(f"\n  {dim(f'Completed in {elapsed_total:.1f}s · {n_coo} COO{hot_str} = {n_coins} coins · {n_signals} signals · {n_llm_calls} LLM calls')}")

        # ═══════════════════════════════════════
        # FINAL: Trade Ledger Summary
        # ═══════════════════════════════════════
        section("Trade Ledger — Lifetime Performance")
        ledger_summary = trade_ledger.format_summary()
        for line in ledger_summary.split("\n"):
            print(f"    {dim(line)}")

        # Calibration analysis (learning loop)
        calibration = trade_ledger.get_calibration()
        if calibration.get("by_conviction"):
            print(f"\n    {dim('Conviction Calibration:')}")
            for conv, data in calibration["by_conviction"].items():
                if data["count"] >= 3:
                    expected = data["expected_wr"]
                    actual = data["win_rate"]
                    gap = data["gap"]
                    gap_str = f"gap {gap:+.0f}%" if gap != 0 else "calibrated"
                    cnt = data["count"]
                    print(f"    {dim(f'  Conv {conv}: {actual:.0f}% actual vs {expected}% expected ({gap_str}, n={cnt})')}")
            rec = calibration["recommendation"]
            print(f"    {dim(f'  {rec}')}")

        # ═══════════════════════════════════════
        # Save cycle snapshot + write blog post
        # ═══════════════════════════════════════
        snapshot_data.team_stats = tracker.get_team_stats()
        snapshot_data.agent_stats = tracker.get_agent_stats()
        snapshot_data.calibration = trade_ledger.get_calibration()
        snapshot_data.team_weights = dict(final_weights)
        snapshot_data.phase_info = {"phase": phase_weights.phase, "closed_trades": closed_trades}
        snapshot_data.portfolio_summary = summary
        snapshot_data.coins_analyzed = n_coins
        snapshot_data.signals_produced = n_signals
        snapshot_data.orders_executed = len(final_orders)
        snapshot_data.duration_secs = elapsed_total
        snapshot_data.llm_calls = n_llm_calls
        try:
            snap_path = snapshot_data.save()
            print(f"    {dim(f'Cycle snapshot saved: {snap_path}')}")
        except Exception as e:
            logger.warning("snapshot_save_failed", error=str(e))

        # Write a blog post about this cycle
        try:
            import json
            from syndicate.executive.ceo_writer import CEOWriter
            writer = CEOWriter(api_key=api_key, provider=provider, model=settings.default_llm_model)
            snap_dict = json.loads(Path(snap_path).read_text()) if snap_path else {}
            blog_result = writer.write_cycle_blog(snap_dict)
            # Save blog to JSON file (DB write happens async in _record below)
            import json as _json
            blog_entry = {
                "post_type": "blog",
                "title": blog_result.get("title", "Cycle Update"),
                "content": blog_result.get("content", ""),
                "summary": blog_result.get("summary", ""),
                "market_context": {"regime": directive.regime.value,
                                    "btc_price": coin_prices.get("BTCUSDT", 0),
                                    "coins_analyzed": n_coins, "trades": len(final_orders)},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            # Save to JSON for API fallback
            blog_path = Path("data/latest_blog.json")
            blog_path.parent.mkdir(parents=True, exist_ok=True)
            blog_path.write_text(_json.dumps(blog_entry, indent=2, default=str))
            # Also append to blog history
            blog_history_path = Path("data/blog_history.json")
            try:
                history = _json.loads(blog_history_path.read_text()) if blog_history_path.exists() else []
            except Exception:
                history = []
            history.insert(0, blog_entry)
            history = history[:50]  # Keep last 50
            blog_history_path.write_text(_json.dumps(history, indent=2, default=str))
            blog_title = blog_result.get("title", "?")[:60]
            print(f"    {dim(f'Blog posted: {blog_title}')}")

            # ── Moltbook: autonomous post ──
            if settings.moltbook_enabled and settings.moltbook_api_key:
                try:
                    from syndicate.moltbook.poster import MoltbookPoster
                    moltbook_poster = MoltbookPoster(
                        api_key=api_key,
                        provider=provider,
                        model=settings.default_llm_model,
                        moltbook_api_key=settings.moltbook_api_key,
                    )
                    mb_result = moltbook_poster.post_cycle_update(blog_entry)
                    if mb_result:
                        print(f"    {dim(f'Moltbook posted: {mb_result.get(\"id\", \"?\")[:20]}')}")
                    else:
                        print(f"    {dim('Moltbook post skipped (adaptation failed)')}")
                except Exception as e:
                    logger.warning("moltbook_post_failed", error=str(e))
                    print(f"    {dim(f'Moltbook failed: {str(e)[:60]}')}")

        except Exception as e:
            logger.warning("cycle_blog_failed", error=str(e))

        # Emit cycle_end event + persist events
        emit_event("cycle_end", "complete", "System",
                    f"Cycle completed in {elapsed_total:.1f}s — {n_coins} coins, {n_signals} signals, {len(final_orders)} trades",
                    {"duration_secs": round(elapsed_total, 1), "coins_analyzed": n_coins,
                     "signals_produced": n_signals, "orders_executed": len(final_orders),
                     "portfolio_value": summary.get("total_value", 100000)})
        collector = get_collector()
        if collector:
            save_events_json(collector)

        # ═══════════════════════════════════════
        # Record cycle to database (if DB available)
        # ═══════════════════════════════════════
        try:
            import asyncio
            from syndicate.core.orchestrator import record_cycle_to_db
            from syndicate.db.session import async_session_factory

            _evt_collector = collector
            _blog_entry = blog_entry if 'blog_entry' in dir() else None

            async def _record():
                from syndicate.db.models import CeoPostRow
                async with async_session_factory() as session:
                    cycle_id = await record_cycle_to_db(
                        db_session=session,
                        started_at=datetime.fromtimestamp(cycle_start_wall, tz=timezone.utc),
                        completed_at=datetime.now(timezone.utc),
                        duration_secs=elapsed_total,
                        regime=directive.regime.value,
                        coins_analyzed=n_coins,
                        signals_produced=n_signals,
                        orders_executed=len(final_orders),
                        portfolio_value=summary.get("total_value", 100000),
                    )
                    # Save blog post to DB
                    if _blog_entry:
                        post = CeoPostRow(
                            post_type=_blog_entry["post_type"],
                            title=_blog_entry["title"],
                            content=_blog_entry["content"],
                            summary=_blog_entry.get("summary", ""),
                            market_context=_blog_entry.get("market_context"),
                        )
                        session.add(post)
                    await session.commit()
                    # Persist pipeline events
                    if _evt_collector:
                        await persist_events(cycle_id, _evt_collector)

            # Always use a fresh event loop from sync thread context
            _loop = asyncio.new_event_loop()
            try:
                _loop.run_until_complete(_record())
            finally:
                _loop.close()
        except Exception as e:
            logger.warning("cycle_db_record_failed", error=str(e))

    finally:
        paper_trader.save(settings.portfolio_state_path)
        if _owns_binance:
            _binance.close()

    footer()


CYCLE_INTERVAL_HOURS = 4


def _next_4h_boundary() -> datetime:
    """Return the next 4H candle boundary (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC)."""
    now = datetime.now(timezone.utc)
    # Which 4H slot are we in? (0, 4, 8, 12, 16, 20)
    current_slot = (now.hour // CYCLE_INTERVAL_HOURS) * CYCLE_INTERVAL_HOURS
    next_slot = current_slot + CYCLE_INTERVAL_HOURS
    boundary = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=next_slot)
    # If next_slot >= 24, it rolls to tomorrow (timedelta handles this)
    return boundary


def _seconds_until(target: datetime) -> float:
    return max(0, (target - datetime.now(timezone.utc)).total_seconds())


def _format_duration(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"


def _try_load_registry():
    """Try to load the agent registry from the database. Returns None if DB unavailable."""
    import asyncio

    async def _load():
        from syndicate.core.agent_registry import AgentRegistry
        from syndicate.db.session import async_session_factory
        async with async_session_factory() as session:
            reg = AgentRegistry(session)
            await reg.load_all()
            return reg

    try:
        return asyncio.run(_load())
    except Exception as e:
        logger.info("registry_unavailable", reason=str(e)[:80])
        return None


def main() -> None:
    """Entry point — runs a single cycle."""
    try:
        settings.get_active_llm_key()
    except ValueError as e:
        print(f"\n  {c('Error:', C.B_RED)} {e}")
        print(f"  Copy .env.example to .env and add your API key.\n")
        sys.exit(1)

    registry = _try_load_registry()
    if registry:
        print(f"  {dim('Registry loaded from database')}")
    else:
        print(f"  {dim('No database — using hardcoded founding agents')}")

    binance = BinanceClient()
    try:
        run_pipeline(binance=binance, registry=registry)
    finally:
        binance.close()


def run_loop() -> None:
    """
    Continuous cycle loop — runs the pipeline every 4 hours, aligned to candle boundaries.

    Aligns to UTC 4H boundaries: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00.
    Runs immediately on start, then sleeps until the next boundary.
    Survives cycle errors — logs and waits for next interval.
    Clean shutdown on Ctrl+C / SIGTERM.
    """
    try:
        settings.get_active_llm_key()
    except ValueError as e:
        print(f"\n  {c('Error:', C.B_RED)} {e}")
        print(f"  Copy .env.example to .env and add your API key.\n")
        sys.exit(1)

    shutdown_requested = False

    def _handle_signal(signum, frame):
        nonlocal shutdown_requested
        shutdown_requested = True
        sig_name = signal.Signals(signum).name
        print(f"\n  {c(f'{sig_name} received — finishing current cycle then shutting down.', C.B_YELLOW)}")

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    binance = BinanceClient()
    cycle_count = 0

    print(f"\n  {c('SYNDICATE CONTINUOUS MODE', C.B_WHITE)}")
    print(f"  {dim(f'Cycle interval: {CYCLE_INTERVAL_HOURS}H · Aligned to UTC candle boundaries')}")
    print(f"  {dim('Press Ctrl+C to stop gracefully')}\n")

    try:
        while not shutdown_requested:
            cycle_count += 1
            now = datetime.now(timezone.utc)
            ts = now.strftime("%Y-%m-%d %H:%M UTC")
            print(f"  {dim(f'[Cycle {cycle_count}] Starting at {ts}')}")

            # Reload registry each cycle to pick up new agents
            registry = _try_load_registry()

            try:
                run_pipeline(binance=binance, registry=registry)
            except Exception as e:
                logger.error("cycle_failed", cycle=cycle_count, error=str(e))
                print(f"\n  {c('Cycle failed:', C.B_RED)} {e}")
                print(f"  {dim('Will retry at next interval.')}")

            if shutdown_requested:
                break

            # Sleep until next 4H boundary
            next_run = _next_4h_boundary()
            wait_secs = _seconds_until(next_run)

            if wait_secs < 30:
                # We're right at a boundary — skip to the next one
                next_run += timedelta(hours=CYCLE_INTERVAL_HOURS)
                wait_secs = _seconds_until(next_run)

            next_ts = next_run.strftime("%Y-%m-%d %H:%M UTC")
            wait_str = _format_duration(wait_secs)
            print(f"\n  {dim(f'Next cycle: {next_ts} (in {wait_str})')}")
            print(f"  {dim('Sleeping... (Ctrl+C to stop)')}\n")

            # Sleep in 30s chunks so we can respond to shutdown signals
            sleep_end = time.monotonic() + wait_secs
            while time.monotonic() < sleep_end and not shutdown_requested:
                remaining = sleep_end - time.monotonic()
                time.sleep(min(remaining, 30))

    finally:
        binance.close()
        print(f"\n  {dim(f'Shutdown complete. Ran {cycle_count} cycle(s).')}\n")


def run_server() -> None:
    """Start the FastAPI server with background cycle loop."""
    import uvicorn

    try:
        settings.get_active_llm_key()
    except ValueError as e:
        print(f"\n  {c('Error:', C.B_RED)} {e}")
        print(f"  Copy .env.example to .env and add your API key.\n")
        sys.exit(1)

    from syndicate.api.app import app

    # Railway sets PORT env var — use it if available, else fall back to serve_port
    port = settings.port if settings.port > 0 else settings.serve_port

    print(f"\n  {c('SYNDICATE API SERVER', C.B_WHITE)}")
    print(f"  {dim(f'Starting on {settings.serve_host}:{port}')}")
    print(f"  {dim('Cycle loop runs in background every 4H')}\n")

    uvicorn.run(
        app,
        host=settings.serve_host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    if "--serve" in sys.argv:
        run_server()
    elif "--loop" in sys.argv:
        run_loop()
    else:
        main()
