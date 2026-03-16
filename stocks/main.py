"""
Stocks Syndicate — Multi-Stock Pipeline Orchestrator

14-step pipeline (12 crypto steps + earnings blackout + news team):
  0. Check open trades from prior cycles
  1. Intelligence gathering (parallel: SPY data, VIX/indices, CNN F&G, Reddit stocks, FRED, Polymarket, news, sector perf)
  2. Stock CEO → Strategic Directive (regime, GICS sector weights, focus strategy)
  3. Stock COO → Stock Selection from universe
  3b. Hot Stock Injection (Reddit/news-driven)
  4. Data Layer → Per-stock enrichment (Yahoo Finance + EDGAR + news)
  5. Stock CRO → Risk Rules
  6. Agent Analysis (6 teams × N stocks, parallel)
  7. Signal Aggregation (Bayesian)
  7b. Earnings Blackout Filter (NEW — block positions within 3 days of earnings)
  8. Risk Manager
  9. GICS Portfolio Managers
  10. Verdicts
  11. Execution (market hours aware)
  12. Performance Tracking
  13. Stock CEO Post-Cycle Review (6 teams)
"""

from __future__ import annotations

import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime, timezone

import structlog

# Shared base classes from syndicate
from syndicate.agents.base import BaseAgent
from syndicate.config import settings as syndicate_settings
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
    action_badge,
    banner,
    c,
    coin_header,
    conf,
    conf_bar,
    cro_card,
    dim,
    footer,
    multi_verdict_row,
    pct,
    ceo_review_card,
    pm_summary,
    portfolio_card,
    section,
    strategic_directive_card,
    trade_fill,
)
from syndicate.evaluation.performance_tracker import PerformanceTracker
from syndicate.execution.trade_ledger import TradeLedger
from syndicate.execution.trade_monitor import TradeMonitor
from syndicate.risk.risk_manager import RiskManager

# Stock-specific imports
from stocks.agents.technical.trend_agent import StockTrendAgent
from stocks.agents.technical.signal_agent import StockSignalAgent
from stocks.agents.technical.timing_agent import StockTimingAgent
from stocks.agents.technical.technical_manager import StockTechnicalManager
from stocks.agents.sentiment.social_agent import StockSocialAgent
from stocks.agents.sentiment.market_agent import StockMarketSentimentAgent
from stocks.agents.sentiment.smart_money_agent import StockSmartMoneyAgent
from stocks.agents.sentiment.sentiment_manager import StockSentimentManager
from stocks.agents.fundamental.valuation_agent import StockValuationAgent
from stocks.agents.fundamental.earnings_agent import StockEarningsAgent
from stocks.agents.fundamental.quality_agent import StockQualityAgent
from stocks.agents.fundamental.fundamental_manager import StockFundamentalManager
from stocks.agents.macro.us_reports_agent import StockUSReportsAgent
from stocks.agents.macro.rates_dollar_agent import StockRatesDollarAgent
from stocks.agents.macro.sector_rotation_agent import StockSectorRotationAgent
from stocks.agents.macro.macro_manager import StockMacroManager
from stocks.agents.institutional.ownership_agent import StockOwnershipAgent
from stocks.agents.institutional.flow_agent import StockFlowAgent
from stocks.agents.institutional.institutional_manager import StockInstitutionalManager
from stocks.agents.news.news_agent import StockNewsAgent
from stocks.agents.news.news_impact_agent import StockNewsImpactAgent
from stocks.agents.news.news_manager import StockNewsManager
from stocks.aggregator import SignalAggregator
from stocks.config import stock_settings
from stocks.data.data_layer import StockDataLayer, StockMarketSnapshot
from stocks.data.market_indices import get_market_indices, get_cnn_fear_greed
from stocks.data.reddit_stocks import get_stock_reddit_sentiment
from stocks.data.sector_perf import get_sector_performance
from stocks.data.stock_news import get_market_news
from stocks.data.yahoo_finance import get_stock_candles, get_stock_stats_24h
from stocks.executive.ceo_agent import StockCEOAgent
from stocks.executive.ceo_memory import StockCEOMemory
from stocks.executive.coo_agent import StockCOOAgent
from stocks.executive.cro_agent import StockCROAgent
from stocks.executive.team_weights import StockTeamWeightManager
from stocks.execution.paper_trader import StockPaperTrader
from stocks.portfolio.manager import StockPortfolioManagerGroup, preload_sectors
from stocks.risk.trade_params import compute_stock_trade_params, size_stock_position

logger = structlog.get_logger()

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


def _run_single_agent(agent_cls, team_type, symbol, data, api_key, provider):
    """Run a single agent. Thread-safe."""
    profile = AgentProfile(
        team=team_type, symbol=symbol,
        model=syndicate_settings.default_llm_model, provider=provider.value,
    )
    agent = agent_cls(profile=profile, api_key=api_key, provider=provider)
    t0 = time.monotonic()
    signal = agent.analyze(data)
    elapsed = time.monotonic() - t0
    agent_name = agent_cls.__name__.replace("Stock", "").replace("Agent", "")
    return signal, agent_name, elapsed


def _run_team(team_name, team_type, agent_classes, manager_cls, data, symbol, api_key, provider, executor):
    """Run all agents in a team in parallel, then synthesize."""
    futures = []
    for agent_cls in agent_classes:
        fut = executor.submit(_run_single_agent, agent_cls, team_type, symbol, data, api_key, provider)
        futures.append(fut)

    agent_signals = []
    display_lines = []
    for fut in futures:
        signal, agent_name, elapsed = fut.result()
        direction = signal.metadata.get("direction", signal.action.value)
        conviction = signal.metadata.get("conviction", int(signal.confidence * 10))
        display_lines.append(f"      {dim(agent_name):<18} {direction} {conviction}/10  {dim(f'{elapsed:.1f}s')}")
        agent_signals.append(signal)

    for line in display_lines:
        print(line)

    manager = manager_cls(api_key=api_key, provider=provider, model=syndicate_settings.default_llm_model)
    t0 = time.monotonic()
    team_signal = manager.synthesize(agent_signals, symbol)
    mgr_elapsed = time.monotonic() - t0

    final_signal = team_signal.to_signal()
    agree_str = f"{team_signal.agreement_level:.0%} agree"
    tf_str = f" [{team_signal.timeframe_alignment}]" if team_signal.timeframe_alignment and team_signal.timeframe_alignment != "N/A" else ""
    mgr_line = (
        f"    {c(team_name, C.B_WHITE)}  "
        f"{action_badge(final_signal.action.value)}  "
        f"{conf_bar(final_signal.confidence)} {conf(final_signal.confidence)}  "
        f"{dim(f'{agree_str}{tf_str}  {mgr_elapsed:.1f}s')}"
    )

    return final_signal, [*display_lines, mgr_line]


def _analyze_stock(symbol, snapshot, api_key, provider):
    """Run all 6 agent teams for a single stock."""
    stock = snapshot.stocks.get(symbol)
    if stock is None or stock.indicators_1d is None:
        return [], {}, 0.0

    coin_header(symbol, stock.current_price, stock.stats.get("price_change_pct", 0))

    team_data = {
        TeamType.TECHNICAL: snapshot.for_technical(symbol),
        TeamType.SENTIMENT: snapshot.for_sentiment(symbol),
        TeamType.FUNDAMENTAL: snapshot.for_fundamental(symbol),
        TeamType.MACRO: snapshot.for_macro(symbol),
        TeamType.INSTITUTIONAL: snapshot.for_institutional(symbol),
        TeamType.NEWS: snapshot.for_news(symbol),
    }

    teams = [
        ("Technical", TeamType.TECHNICAL,
         [StockTrendAgent, StockSignalAgent, StockTimingAgent], StockTechnicalManager),
        ("Sentiment", TeamType.SENTIMENT,
         [StockSocialAgent, StockMarketSentimentAgent, StockSmartMoneyAgent], StockSentimentManager),
        ("Fundamental", TeamType.FUNDAMENTAL,
         [StockValuationAgent, StockEarningsAgent, StockQualityAgent], StockFundamentalManager),
        ("Macro", TeamType.MACRO,
         [StockUSReportsAgent, StockRatesDollarAgent, StockSectorRotationAgent], StockMacroManager),
        ("Institutional", TeamType.INSTITUTIONAL,
         [StockOwnershipAgent, StockFlowAgent], StockInstitutionalManager),
        ("News", TeamType.NEWS,
         [StockNewsAgent, StockNewsImpactAgent], StockNewsManager),
    ]

    with ThreadPoolExecutor(max_workers=18) as executor:
        team_futures = []
        for team_name, team_type, agent_classes, manager_cls in teams:
            fut = executor.submit(
                _run_team, team_name, team_type, agent_classes, manager_cls,
                team_data[team_type], symbol, api_key, provider, executor,
            )
            team_futures.append((team_name, team_type, fut))

        all_manager_signals = []
        agent_profiles = {}

        for team_name, team_type, fut in team_futures:
            try:
                manager_signal, display_lines = fut.result()
                for line in display_lines:
                    print(line)

                manager_signal.metadata["current_price"] = stock.current_price
                manager_signal.metadata["stats_24h"] = stock.stats
                if stock.indicators_1d and stock.indicators_1d.atr_14:
                    manager_signal.metadata["atr_14"] = stock.indicators_1d.atr_14

                # Flag earnings blackout in metadata
                if stock.earnings and stock.earnings.in_blackout:
                    manager_signal.metadata["earnings_blackout"] = True

                all_manager_signals.append(manager_signal)

                mgr_profile = AgentProfile(
                    agent_id=f"manager_{team_type.value}", team=team_type, symbol=symbol,
                    model=syndicate_settings.default_llm_model, provider=provider.value,
                )
                agent_profiles[mgr_profile.agent_id] = mgr_profile

            except Exception as e:
                logger.error("stock_team_failed", team=team_name, symbol=symbol, error=str(e))

    return all_manager_signals, agent_profiles, stock.current_price


def _apply_earnings_blackout(aggregated: list[AggregatedSignal], snapshot: StockMarketSnapshot) -> list[AggregatedSignal]:
    """Post-aggregation earnings blackout filter."""
    for agg in aggregated:
        stock = snapshot.stocks.get(agg.symbol)
        if stock and stock.earnings and stock.earnings.in_blackout:
            if agg.recommended_action in (SignalAction.BUY, SignalAction.SHORT):
                agg.recommended_action = SignalAction.HOLD
                agg.aggregated_confidence = 0.0
                agg.weighted_scores["_earnings_blackout"] = True
                agg.weighted_scores["_alerts"] = agg.weighted_scores.get("_alerts", []) + [
                    f"[HIGH] EARNINGS_BLACKOUT: {agg.symbol} has earnings in {stock.earnings.days_to_earnings} days — position blocked"
                ]
                logger.info("earnings_blackout_filter", symbol=agg.symbol, days=stock.earnings.days_to_earnings)
    return aggregated


def run_pipeline() -> None:
    """Run the full stock market analysis pipeline."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    banner("Stock Market Cycle", now)

    api_key = syndicate_settings.get_active_llm_key()
    provider = syndicate_settings.default_llm_provider
    max_stocks = stock_settings.max_stocks_per_cycle
    cycle_start = time.monotonic()

    paper_trader = StockPaperTrader(initial_cash=100_000.0)
    tracker = PerformanceTracker(storage_path=stock_settings.stock_performance_path)
    ceo_memory = StockCEOMemory(storage_path=stock_settings.stock_ceo_memory_path)
    trade_monitor = TradeMonitor(storage_path=stock_settings.stock_open_trades_path)
    trade_ledger = TradeLedger(storage_path=stock_settings.stock_trade_ledger_path)
    team_weights = StockTeamWeightManager(storage_path=stock_settings.stock_team_weights_path)

    try:
        # ═══════════════════════════════════════
        # STEP 0: Check Open Trades
        # ═══════════════════════════════════════
        if trade_monitor.open_trades:
            section("Trade Monitor — Checking Open Positions")
            # For stocks, we'd need a different candle source than Binance
            # For now, log open positions
            n = len(trade_monitor.open_trades)
            print(f"    {dim(f'{n} open stock positions tracked')}")

        # ═══════════════════════════════════════
        # STEP 1: Intelligence Gathering
        # ═══════════════════════════════════════
        section("Intelligence Gathering")

        intel: dict = {}
        t0 = time.monotonic()

        def _fetch_indices():
            return "indices", get_market_indices()

        def _fetch_cnn_fg():
            return "cnn_fear_greed", get_cnn_fear_greed()

        def _fetch_reddit():
            return "reddit_sentiment", get_stock_reddit_sentiment(limit_per_sub=10)

        def _fetch_sectors():
            return "sector_performance", get_sector_performance()

        def _fetch_market_news():
            return "market_news", get_market_news()

        def _fetch_us_reports():
            from syndicate.data.us_economic_reports import fetch_us_reports
            return "us_economic_reports", fetch_us_reports(importance_min=3)

        def _fetch_polymarket():
            from syndicate.data.polymarket import PolymarketClient
            p = PolymarketClient()
            try:
                return "prediction_markets", p.get_all_relevant_markets()
            finally:
                p.close()

        with ThreadPoolExecutor(max_workers=7) as intel_executor:
            futures = [
                intel_executor.submit(_fetch_indices),
                intel_executor.submit(_fetch_cnn_fg),
                intel_executor.submit(_fetch_reddit),
                intel_executor.submit(_fetch_sectors),
                intel_executor.submit(_fetch_market_news),
                intel_executor.submit(_fetch_us_reports),
                intel_executor.submit(_fetch_polymarket),
            ]
            for fut in futures:
                try:
                    key, data = fut.result()
                    intel[key] = data
                except Exception as e:
                    logger.warning("stock_intel_fetch_failed", error=str(e))

        # SPY indicators for CEO
        spy_candles = get_stock_candles("SPY", period="1y", interval="1d")
        spy_indicators = compute_indicators(spy_candles, "SPY") if spy_candles else None

        # Display intel
        indices = intel.get("indices")
        if indices and indices.spy_price:
            print(f"    {dim('SPY')}             ${indices.spy_price:,.2f} ({indices.spy_change_pct or 0:+.2f}%)")
        if indices and indices.vix:
            print(f"    {dim('VIX')}             {indices.vix:.1f}")
        fg = intel.get("cnn_fear_greed", {})
        if fg:
            print(f"    {dim('CNN F&G')}         {fg.get('current_value', '?')}/100 ({fg.get('current_label', '?')})")
        reddit = intel.get("reddit_sentiment")
        if reddit:
            ratio_pct = round(reddit.get("sentiment_ratio", 0.5) * 100)
            print(f"    {dim('Reddit')}          {reddit.get('total_posts', 0)} posts · {ratio_pct}% bullish")
        sector_perf = intel.get("sector_performance")
        if sector_perf and sector_perf.hot_sectors:
            print(f"    {dim('Hot Sectors')}     {', '.join(sector_perf.hot_sectors)}")
        us_reports = intel.get("us_economic_reports")
        if us_reports:
            summary = us_reports.summary
            print(f"    {dim('US Reports')}     bias: {summary.get('net_bias', '?')} · inflation: {summary.get('inflation_trend', '?')}")

        intel_elapsed = time.monotonic() - t0
        print(f"    {dim(f'All sources fetched in {intel_elapsed:.1f}s')}")

        # ═══════════════════════════════════════
        # STEP 2: Stock CEO — Strategic Directive
        # ═══════════════════════════════════════
        section("Stock CEO — Strategic Directive")

        portfolio_summary = paper_trader.get_summary()
        perf_summary = tracker.get_summary()

        ceo = StockCEOAgent(api_key=api_key, provider=provider, model=syndicate_settings.default_llm_model)
        last_feedback = ceo_memory.get_last_feedback()
        experience = ceo_memory.get_experience_summary()
        t0 = time.monotonic()
        directive = ceo.direct(spy_indicators, intel, portfolio_summary, perf_summary, last_feedback, experience)
        ceo_elapsed = time.monotonic() - t0

        if ceo_memory.cycle_count > 0:
            print(f"    {dim(f'CEO experience: {ceo_memory.cycle_count} prior cycles')}")
        strategic_directive_card(directive, ceo_elapsed)

        if directive.emergency_halt:
            print(f"\n    {c('EMERGENCY HALT — All trading suspended.', C.B_RED)}")
            print(f"    {dim(directive.halt_reason)}")
            footer()
            return

        # ═══════════════════════════════════════
        # STEP 3: Stock COO — Stock Selection
        # ═══════════════════════════════════════
        section("Stock COO — Stock Selection")

        # Get basic stats for universe (top movers)
        t0 = time.monotonic()
        from stocks.watchlist import StockWatchlist
        watchlist = StockWatchlist()
        watchlist.refresh_if_stale()
        universe = watchlist.sp500 or ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "JPM", "V", "UNH",
                                        "MA", "HD", "PG", "JNJ", "XOM", "BAC", "COST", "ABBV", "CRM", "AMD"]

        # Fetch basic stats for top stocks
        all_stats = []
        def _fetch_stat(sym):
            return get_stock_stats_24h(sym)

        with ThreadPoolExecutor(max_workers=10) as pool:
            stat_results = list(pool.map(_fetch_stat, universe[:50]))  # Top 50 from universe

        all_stats = [s for s in stat_results if s and s.get("close", 0) > 0]

        intel["ceo_focus_strategy"] = directive.focus_strategy
        intel["ceo_sector_weights"] = directive.sector_weights

        coo = StockCOOAgent(api_key=api_key, provider=provider, model=syndicate_settings.default_llm_model)
        selection = coo.select(all_stats, directive.regime, max_stocks=max_stocks, extra_intelligence=intel)
        coo_elapsed = time.monotonic() - t0

        selected_stocks = selection.selected_stocks
        if not selected_stocks:
            print(f"\n    {dim('No stocks selected. Exiting.')}")
            footer()
            return

        # Display selection
        print(f"    {c('Selected:', C.B_WHITE)} {', '.join(selected_stocks)}")
        print(f"    {dim(selection.reasoning)}")
        print(f"    {dim(f'{coo_elapsed:.1f}s')}")

        # ═══════════════════════════════════════
        # STEP 3b: Hot Stock Injection from Reddit
        # ═══════════════════════════════════════
        if reddit and reddit.get("stock_mentions"):
            mentions = reddit["stock_mentions"]
            selected_set = set(selected_stocks)
            hot_additions = []
            for ticker, count in list(mentions.items())[:5]:
                if ticker not in selected_set and count >= 3:
                    hot_additions.append(ticker)
                    if len(hot_additions) >= stock_settings.hot_stock_max_additions:
                        break

            for h in hot_additions:
                selected_stocks.append(h)
                print(f"    {c('HOT', C.B_MAGENTA)} {c(h, C.B_WHITE)}  {dim(f'{mentions[h]} Reddit mentions')}")

        # ═══════════════════════════════════════
        # STEP 4: Data Layer — Per-Stock Enrichment
        # ═══════════════════════════════════════
        section("Data Layer — Per-Stock Enrichment")

        data_layer = StockDataLayer()
        t0 = time.monotonic()
        snapshot = data_layer.fetch_all(selected_stocks)
        data_elapsed = time.monotonic() - t0

        # Copy global intel into snapshot
        snapshot.indices = intel.get("indices")
        snapshot.sector_performance = intel.get("sector_performance")
        snapshot.reddit_sentiment = intel.get("reddit_sentiment")
        snapshot.market_news = intel.get("market_news", [])
        snapshot.us_economic_reports = intel.get("us_economic_reports")
        snapshot.prediction_markets = intel.get("prediction_markets")
        snapshot.cnn_fear_greed = intel.get("cnn_fear_greed")

        # Pre-populate sector cache
        fundamentals_map = {sym: s.fundamentals for sym, s in snapshot.stocks.items() if s.fundamentals}
        preload_sectors(selected_stocks, fundamentals_map)

        enriched = sum(1 for s in snapshot.stocks.values() if s.fundamentals)
        earnings = sum(1 for s in snapshot.stocks.values() if s.earnings)
        blackouts = sum(1 for s in snapshot.stocks.values() if s.earnings and s.earnings.in_blackout)
        print(f"    {dim('Enrichment')}     {enriched}/{len(selected_stocks)} fundamentals · {earnings} earnings · {blackouts} in blackout")
        print(f"    {dim(f'Data loaded in {data_elapsed:.1f}s')}")

        # ═══════════════════════════════════════
        # STEP 5: Stock CRO — Risk Rules
        # ═══════════════════════════════════════
        section("Stock CRO — Risk Rules")

        cro = StockCROAgent(api_key=api_key, provider=provider, model=syndicate_settings.default_llm_model)
        t0 = time.monotonic()
        risk_limits, cro_reasoning = cro.set_rules(directive, paper_trader.portfolio, perf_summary)
        cro_elapsed = time.monotonic() - t0

        cro_card(
            {
                "max_position_pct": risk_limits.max_position_pct,
                "max_daily_drawdown_pct": risk_limits.max_daily_drawdown_pct,
                "max_open_positions": risk_limits.max_open_positions,
                "min_signal_confidence": risk_limits.min_signal_confidence,
                "min_consensus_ratio": risk_limits.min_consensus_ratio,
            },
            cro_reasoning, cro_elapsed,
        )

        # ═══════════════════════════════════════
        # STEP 6: Analyze Each Stock (6 teams × N stocks)
        # ═══════════════════════════════════════
        section(f"Agent Analysis — {len(selected_stocks)} stocks × 6 teams")

        all_stock_signals: list[Signal] = []
        all_agent_profiles: dict[str, AgentProfile] = {}
        stock_prices: dict[str, float] = {}

        for symbol in selected_stocks:
            signals, profiles, price = _analyze_stock(symbol, snapshot, api_key, provider)
            all_stock_signals.extend(signals)
            all_agent_profiles.update(profiles)
            stock_prices[symbol] = price

        # ═══════════════════════════════════════
        # STEP 7: Aggregate per stock
        # ═══════════════════════════════════════
        aggregator = SignalAggregator(
            team_weight_overrides=team_weights.weights,
            regime=directive.regime.value,
        )
        aggregated = aggregator.aggregate(all_stock_signals, all_agent_profiles)

        # ═══════════════════════════════════════
        # STEP 7b: Earnings Blackout Filter
        # ═══════════════════════════════════════
        aggregated = _apply_earnings_blackout(aggregated, snapshot)

        # Display alerts
        for agg in aggregated:
            alerts = agg.weighted_scores.get("_alerts", [])
            if alerts:
                for alert_str in alerts:
                    if "[HIGH]" in alert_str:
                        print(f"    {c('!', C.B_RED)} {agg.symbol}: {dim(alert_str)}")
                    elif "[MEDIUM]" in alert_str:
                        print(f"    {c('~', C.B_YELLOW)} {agg.symbol}: {dim(alert_str)}")

        # ═══════════════════════════════════════
        # STEP 8: Risk Manager
        # ═══════════════════════════════════════
        risk_manager = RiskManager(limits=risk_limits, regime=directive.regime)
        risk_orders = risk_manager.evaluate(aggregated, paper_trader.portfolio)

        # ═══════════════════════════════════════
        # STEP 9: GICS Portfolio Managers
        # ═══════════════════════════════════════
        section("Portfolio Managers (GICS Sectors)")
        pm_group = StockPortfolioManagerGroup(ceo_sector_weights=directive.sector_weights)
        orders_before = len(risk_orders)
        final_orders = pm_group.review(risk_orders, paper_trader.portfolio)
        orders_after = len(final_orders)
        sector_exposure = pm_group.get_sector_exposure(paper_trader.portfolio)
        pm_summary(sector_exposure, orders_before, orders_after)

        # ═══════════════════════════════════════
        # STEP 10: Verdicts
        # ═══════════════════════════════════════
        section("Verdicts")
        agg_by_symbol = {a.symbol: a for a in aggregated}
        traded_symbols = {o.symbol for o in final_orders}

        for symbol in selected_stocks:
            agg = agg_by_symbol.get(symbol)
            if agg is None:
                multi_verdict_row(symbol, "HOLD", 0, 0, blocked=True, reason="no signal")
                continue

            blocked = symbol not in traded_symbols
            reason = ""
            if blocked:
                if agg.weighted_scores.get("_earnings_blackout"):
                    reason = "EARNINGS BLACKOUT"
                elif agg.recommended_action.value == "HOLD":
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
        # STEP 11: Execution
        # ═══════════════════════════════════════
        if final_orders:
            section("Execution")
            results = paper_trader.execute_batch(final_orders)
            order_by_symbol = {o.symbol: o for o in final_orders}
            for result in results:
                order = order_by_symbol.get(result.symbol)
                params = order.params if order else None
                trade_fill(result.side.value, result.quantity, result.symbol, result.executed_price, params)

                if order and order.params.stop_loss_price > 0:
                    trade_monitor.register_trade(
                        symbol=result.symbol, side=result.side,
                        entry_price=result.executed_price, quantity=result.quantity,
                        params=order.params,
                    )
                    trade_ledger.record_entry(
                        symbol=result.symbol, side=result.side.value,
                        entry_price=result.executed_price, quantity=result.quantity,
                        asset_tier=order.params.asset_tier,
                        risk_amount=order.params.risk_amount_usd,
                        stop_loss=order.params.stop_loss_price,
                        take_profit_1=order.params.take_profit_1,
                    )
            paper_trader.update_prices(stock_prices)

        summary = paper_trader.get_summary()
        portfolio_card(summary, paper_trader.portfolio.positions or None)

        # ═══════════════════════════════════════
        # STEP 12: Performance Tracking
        # ═══════════════════════════════════════
        tracker.record_signals(all_stock_signals, stock_prices)
        eval_results = tracker.evaluate_pending(stock_prices)
        if eval_results["evaluated"] > 0:
            print(f"    {dim('Evaluated:')} {eval_results['correct']}/{eval_results['evaluated']} correct")

        # ═══════════════════════════════════════
        # STEP 13: Stock CEO Post-Cycle Review
        # ═══════════════════════════════════════
        section("Stock CEO — Post-Cycle Review")

        team_stats = tracker.get_team_stats()
        perf_after = tracker.get_summary()

        t0 = time.monotonic()
        ceo_feedback = ceo.review(
            directive, all_stock_signals, aggregated,
            len(final_orders), summary, team_stats, perf_after,
        )
        review_elapsed = time.monotonic() - t0

        ceo_review_card(ceo_feedback, review_elapsed)

        # Apply CEO team decisions
        ceo_team_actions = ceo_feedback.get("team_actions", [])
        if ceo_team_actions:
            team_weights.apply_ceo_decisions(ceo_team_actions)

        # Persist CEO memory
        ceo_memory.record_cycle(
            directive={
                "regime": directive.regime.value,
                "risk_multiplier": directive.risk_multiplier,
                "sector_weights": directive.sector_weights,
                "focus_strategy": directive.focus_strategy,
            },
            results={
                "stocks_analyzed": len(selected_stocks),
                "signals_generated": len(all_stock_signals),
                "orders_executed": len(final_orders),
                "portfolio_return": summary["return_pct"],
                "drawdown": summary["drawdown_pct"],
                "spy_price": stock_prices.get("SPY", intel.get("indices", {}).spy_price if intel.get("indices") else 0),
            },
            feedback=ceo_feedback,
        )

        # Timing
        elapsed_total = time.monotonic() - cycle_start
        n_signals = len(all_stock_signals)
        n_stocks = len(selected_stocks)
        # CEO pre + CEO post + COO + CRO + (16 sub-agents + 6 managers) per stock
        n_llm_calls = 4 + (22 * n_stocks)
        print(f"\n  {dim(f'Completed in {elapsed_total:.1f}s · {n_stocks} stocks · {n_signals} signals · {n_llm_calls} LLM calls')}")

        # Trade Ledger
        section("Trade Ledger — Lifetime Performance")
        ledger_summary = trade_ledger.format_summary()
        for line in ledger_summary.split("\n"):
            print(f"    {dim(line)}")

    except Exception as e:
        logger.error("stock_pipeline_failed", error=str(e))
        import traceback
        traceback.print_exc()

    footer()


def main() -> None:
    """Entry point."""
    try:
        syndicate_settings.get_active_llm_key()
    except ValueError as e:
        print(f"\n  {c('Error:', C.B_RED)} {e}")
        print(f"  Copy .env.example to .env and add your API key.\n")
        sys.exit(1)

    run_pipeline()


if __name__ == "__main__":
    main()
