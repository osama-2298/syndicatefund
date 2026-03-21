"""Syndicate FastAPI application."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import FastAPI

from syndicate.api.routes import agents, backtest, ceo_posts, comms, contributors, cycles, events, intelligence, leaderboard, moltbook, portfolio, research, signals, teams
from syndicate.polymarket.routes import router as polymarket_router
from syndicate.config import settings

logger = structlog.get_logger()

CYCLE_INTERVAL_HOURS = 4


async def _load_registry():
    """Load the agent registry from the database."""
    from syndicate.core.agent_registry import AgentRegistry
    from syndicate.db.session import async_session_factory

    async with async_session_factory() as session:
        registry = AgentRegistry(session)
        await registry.load_all()
        return registry


async def _background_cycle_loop(shutdown_event: asyncio.Event):
    """Background task that runs the analysis pipeline every 4 hours."""
    import sys
    print("[CYCLE] Background cycle loop starting...", flush=True)

    try:
        from syndicate.data.binance_client import BinanceClient
        binance = BinanceClient()
        print(f"[CYCLE] BinanceClient created with {binance._base_url}", flush=True)
    except Exception as e:
        print(f"[CYCLE] FATAL: Failed to create BinanceClient: {e}", flush=True)
        return

    try:
        while not shutdown_event.is_set():
            # Load fresh registry each cycle (picks up new agents/teams)
            try:
                registry = await _load_registry()
            except Exception as e:
                logger.error("registry_load_failed", error=str(e))
                registry = None  # Fall back to hardcoded agents

            # Run pipeline in a thread (it's synchronous)
            try:
                print(f"[CYCLE] Starting pipeline run (registry={'loaded' if registry else 'none'})...", flush=True)
                from syndicate.main import run_pipeline
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, lambda: run_pipeline(binance=binance, registry=registry)
                )
                print("[CYCLE] Pipeline completed successfully", flush=True)
            except Exception as e:
                import traceback
                logger.error("cycle_failed", error=str(e), traceback=traceback.format_exc())

            # Sleep until next 4H boundary
            now = datetime.now(timezone.utc)
            current_slot = (now.hour // CYCLE_INTERVAL_HOURS) * CYCLE_INTERVAL_HOURS
            next_slot = current_slot + CYCLE_INTERVAL_HOURS
            boundary = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=next_slot)
            wait_secs = max(30, (boundary - datetime.now(timezone.utc)).total_seconds())

            logger.info("cycle_sleeping", next_run=boundary.isoformat(), wait_secs=round(wait_secs))

            # Sleep in chunks so we can respond to shutdown
            sleep_end = time.monotonic() + wait_secs
            while time.monotonic() < sleep_end and not shutdown_event.is_set():
                remaining = sleep_end - time.monotonic()
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=min(remaining, 30))
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    pass  # Continue sleeping
    finally:
        binance.close()
        logger.info("cycle_loop_stopped")


async def _price_monitor(shutdown_event: asyncio.Event):
    """Background task that checks live prices against SL/TP every 2 seconds."""
    import httpx

    print("[MONITOR] Price monitor starting...", flush=True)

    async with httpx.AsyncClient(timeout=10.0) as http:
        while not shutdown_event.is_set():
            try:
                from syndicate.config import settings
                from syndicate.execution.trade_monitor import TradeMonitor
                from syndicate.execution.paper_trader import PaperTrader
                from syndicate.execution.trade_ledger import TradeLedger
                from syndicate.data.models import OrderSide

                monitor = TradeMonitor(storage_path=settings.open_trades_path)
                if not monitor.open_trades:
                    await asyncio.sleep(5)
                    continue

                # Fetch current prices for all open positions
                symbols = list(monitor.open_trades.keys())
                params = ",".join(f'"{s}"' for s in symbols)
                resp = await http.get(
                    f"https://data-api.binance.vision/api/v3/ticker/price?symbols=[{params}]"
                )
                prices = {item["symbol"]: float(item["price"]) for item in resp.json()}

                triggered = []
                for symbol, trade in list(monitor.open_trades.items()):
                    price = prices.get(symbol)
                    if price is None:
                        continue

                    params_t = trade.params
                    is_long = trade.side == OrderSide.BUY

                    # Check stop loss
                    if params_t.stop_loss_price > 0:
                        if (is_long and price <= params_t.stop_loss_price) or \
                           (not is_long and price >= params_t.stop_loss_price):
                            triggered.append((symbol, price, "STOP_LOSS", trade.quantity))
                            continue

                    # Check take profit 1
                    if params_t.take_profit_1 > 0 and not trade.tp1_hit:
                        if (is_long and price >= params_t.take_profit_1) or \
                           (not is_long and price <= params_t.take_profit_1):
                            exit_qty = trade.quantity * 0.33
                            triggered.append((symbol, price, "TAKE_PROFIT_1", exit_qty))
                            continue

                    # Check take profit 2
                    if params_t.take_profit_2 > 0 and trade.tp1_hit and not trade.tp2_hit:
                        if (is_long and price >= params_t.take_profit_2) or \
                           (not is_long and price <= params_t.take_profit_2):
                            exit_qty = trade.quantity * 0.5
                            triggered.append((symbol, price, "TAKE_PROFIT_2", exit_qty))
                            continue

                # Execute triggered exits under lock to avoid race with pipeline
                if triggered:
                    from syndicate.execution.state_lock import execution_lock

                    with execution_lock:
                        # Re-load inside lock to get latest state
                        paper_trader = PaperTrader.load(settings.portfolio_state_path)
                        ledger = TradeLedger(storage_path=settings.trade_ledger_path)

                        for symbol, price, reason, qty in triggered:
                            try:
                                paper_trader.partial_close(symbol=symbol, quantity=qty, price=price)
                                print(f"[MONITOR] {reason} triggered: {symbol} @ ${price:,.2f} (qty={qty:.6f})", flush=True)

                                # Record in ledger
                                trade = monitor.open_trades.get(symbol)
                                if trade:
                                    pnl_pct = ((price - trade.entry_price) / trade.entry_price) * \
                                              (1 if trade.side == OrderSide.BUY else -1)
                                    pnl_usd = (price - trade.entry_price) * qty * \
                                               (1 if trade.side == OrderSide.BUY else -1)
                                    entry_time = trade.entry_time if hasattr(trade, 'entry_time') else None
                                    holding_hours = 0.0
                                    if entry_time:
                                        try:
                                            from datetime import datetime as dt
                                            if isinstance(entry_time, str):
                                                entry_dt = dt.fromisoformat(entry_time.replace('Z', '+00:00'))
                                            else:
                                                entry_dt = entry_time
                                            holding_hours = (dt.now(timezone.utc) - entry_dt).total_seconds() / 3600
                                        except Exception:
                                            pass
                                    ledger.record_exit(
                                        symbol=symbol,
                                        exit_price=price,
                                        exit_reason=reason,
                                        pnl_pct=pnl_pct,
                                        pnl_usd=pnl_usd,
                                        holding_hours=holding_hours,
                                        quantity=qty,
                                    )

                                    # Update or remove from monitor
                                    trade.quantity -= qty
                                    if reason == "TAKE_PROFIT_1":
                                        trade.tp1_hit = True
                                    elif reason == "TAKE_PROFIT_2":
                                        trade.tp2_hit = True
                                    if trade.quantity <= 0.000001 or reason == "STOP_LOSS":
                                        del monitor.open_trades[symbol]
                            except Exception as e:
                                logger.error("monitor_exit_failed", symbol=symbol, error=str(e))

                        paper_trader.save(settings.portfolio_state_path)
                        monitor._save()

            except Exception as e:
                logger.error("price_monitor_error", error=str(e))

            # Check every 2 seconds
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=2)
                break
            except asyncio.TimeoutError:
                pass

    print("[MONITOR] Price monitor stopped.", flush=True)


async def _daily_briefing_task(shutdown_event: asyncio.Event):
    """Runs daily at 08:00 UTC — CEO reads the market and writes a briefing."""
    print("[CEO] Daily briefing task starting...", flush=True)

    while not shutdown_event.is_set():
        try:
            # Wait until 08:00 UTC
            now = datetime.now(timezone.utc)
            next_run = now.replace(hour=8, minute=0, second=0, microsecond=0)
            if now.hour >= 8:
                next_run += timedelta(days=1)
            wait_secs = (next_run - now).total_seconds()

            print(f"[CEO] Next briefing at {next_run.isoformat()} ({int(wait_secs)}s)", flush=True)

            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=wait_secs)
                break
            except asyncio.TimeoutError:
                pass

            # Gather market data
            import httpx
            ctx = {}
            async with httpx.AsyncClient(timeout=15) as http:
                try:
                    r = await http.get("https://data-api.binance.vision/api/v3/ticker/24hr?symbol=BTCUSDT")
                    d = r.json()
                    ctx["btc_price"] = float(d.get("lastPrice", 0))
                    ctx["btc_24h_change"] = float(d.get("priceChangePercent", 0))
                except Exception:
                    pass
                try:
                    r = await http.get("https://api.alternative.me/fng/?limit=1")
                    fg = r.json().get("data", [{}])[0]
                    ctx["fear_greed"] = f"{fg.get('value', '?')}/100 ({fg.get('value_classification', '?')})"
                except Exception:
                    pass

            # Get portfolio state
            from pathlib import Path
            import json
            portfolio_path = Path(settings.portfolio_state_path)
            if portfolio_path.exists():
                pf = json.loads(portfolio_path.read_text())
                positions = pf.get("positions", [])
                ctx["open_positions"] = ", ".join(
                    f"{p['symbol'].replace('USDT','')} ({p['side']})" for p in positions
                ) or "None"

            # Write briefing
            from syndicate.executive.ceo_writer import CEOWriter
            writer = CEOWriter(
                api_key=settings.get_active_llm_key(),
                provider=settings.default_llm_provider,
                model=settings.default_llm_model,
            )
            result = writer.write_briefing(ctx)

            # Save to DB
            from syndicate.db.session import async_session_factory
            from syndicate.db.models import CeoPostRow
            async with async_session_factory() as session:
                post = CeoPostRow(
                    post_type="briefing",
                    title=result.get("title", "Daily Brief"),
                    content=result.get("content", ""),
                    summary=result.get("summary", ""),
                    market_context=ctx,
                )
                session.add(post)
                await session.commit()

            print(f"[CEO] Daily briefing written: {result.get('title', '?')}", flush=True)

        except Exception as e:
            logger.error("daily_briefing_failed", error=str(e))

        # Small delay before next loop iteration
        await asyncio.sleep(60)

    print("[CEO] Daily briefing task stopped.", flush=True)


async def _weekly_blog_task(shutdown_event: asyncio.Event):
    """Runs weekly on Sunday at 10:00 UTC — CEO writes a blog post."""
    print("[CEO] Weekly blog task starting...", flush=True)

    while not shutdown_event.is_set():
        try:
            # Wait until Sunday 10:00 UTC
            now = datetime.now(timezone.utc)
            days_until_sunday = (6 - now.weekday()) % 7
            if days_until_sunday == 0 and now.hour >= 10:
                days_until_sunday = 7
            next_run = (now + timedelta(days=days_until_sunday)).replace(
                hour=10, minute=0, second=0, microsecond=0
            )
            wait_secs = (next_run - now).total_seconds()

            print(f"[CEO] Next blog at {next_run.isoformat()} ({int(wait_secs)}s)", flush=True)

            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=wait_secs)
                break
            except asyncio.TimeoutError:
                pass

            # Gather weekly context
            from pathlib import Path
            import json

            ctx = {}

            # BTC price
            import httpx
            async with httpx.AsyncClient(timeout=15) as http:
                try:
                    r = await http.get("https://data-api.binance.vision/api/v3/ticker/24hr?symbol=BTCUSDT")
                    d = r.json()
                    ctx["btc_price"] = float(d.get("lastPrice", 0))
                except Exception:
                    pass
                try:
                    r = await http.get("https://api.alternative.me/fng/?limit=1")
                    fg = r.json().get("data", [{}])[0]
                    ctx["fear_greed"] = f"{fg.get('value', '?')}/100"
                except Exception:
                    pass

            # Portfolio
            portfolio_path = Path(settings.portfolio_state_path)
            if portfolio_path.exists():
                pf = json.loads(portfolio_path.read_text())
                positions = pf.get("positions", [])
                cash = pf.get("cash", 100000)
                invested = sum(p["quantity"] * p.get("current_price", p["entry_price"]) for p in positions)
                ctx["portfolio_value"] = cash + invested
                ctx["return_pct"] = ((cash + invested - 100000) / 100000) * 100

            # Cycle stats from DB
            try:
                from syndicate.db.session import async_session_factory
                from syndicate.db.models import CycleRow
                from sqlalchemy import select, func
                async with async_session_factory() as session:
                    week_ago = now - timedelta(days=7)
                    result = await session.execute(
                        select(
                            func.count(CycleRow.id),
                            func.sum(CycleRow.signals_produced),
                            func.sum(CycleRow.orders_executed),
                        ).where(CycleRow.started_at >= week_ago)
                    )
                    row = result.one_or_none()
                    if row:
                        ctx["cycles_this_week"] = row[0] or 0
                        ctx["signals_this_week"] = row[1] or 0
                        ctx["trades_this_week"] = row[2] or 0
            except Exception:
                pass

            # Agent count
            try:
                from syndicate.db.models import AgentRow, AgentStatusDB
                async with async_session_factory() as session:
                    result = await session.execute(
                        select(func.count(AgentRow.id)).where(
                            AgentRow.status.in_([AgentStatusDB.FOUNDING, AgentStatusDB.ACTIVE, AgentStatusDB.ASSIGNED])
                        )
                    )
                    ctx["active_agents"] = result.scalar() or 0
            except Exception:
                pass

            # Write blog
            from syndicate.executive.ceo_writer import CEOWriter
            writer = CEOWriter(
                api_key=settings.get_active_llm_key(),
                provider=settings.default_llm_provider,
                model=settings.default_llm_model,
            )
            result = writer.write_blog(ctx)

            # Also write a memo after the blog
            memo_result = writer.write_memo(ctx)

            # Save both to DB
            from syndicate.db.models import CeoPostRow
            async with async_session_factory() as session:
                blog_post = CeoPostRow(
                    post_type="blog",
                    title=result.get("title", "Weekly Update"),
                    content=result.get("content", ""),
                    summary=result.get("summary", ""),
                    market_context=ctx,
                )
                memo_post = CeoPostRow(
                    post_type="memo",
                    title=memo_result.get("title", "Strategy Update"),
                    content=memo_result.get("content", ""),
                    market_context=ctx,
                )
                session.add(blog_post)
                session.add(memo_post)
                await session.commit()

            print(f"[CEO] Weekly blog written: {result.get('title', '?')}", flush=True)
            print(f"[CEO] Memo written: {memo_result.get('title', '?')}", flush=True)

        except Exception as e:
            logger.error("weekly_blog_failed", error=str(e))

        await asyncio.sleep(60)

    print("[CEO] Weekly blog task stopped.", flush=True)


async def _daily_research_task(shutdown_event: asyncio.Event):
    """Runs daily at 06:00 UTC — research team analyzes signal health and trade attribution."""
    print("[RESEARCH] Daily research task starting...", flush=True)

    while not shutdown_event.is_set():
        try:
            # Wait until 06:00 UTC
            now = datetime.now(timezone.utc)
            next_run = now.replace(hour=6, minute=0, second=0, microsecond=0)
            if now.hour >= 6:
                next_run += timedelta(days=1)
            wait_secs = (next_run - now).total_seconds()

            print(f"[RESEARCH] Next daily research at {next_run.isoformat()}", flush=True)

            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=wait_secs)
                break
            except asyncio.TimeoutError:
                pass

            print("[RESEARCH] Running daily analysis...", flush=True)

            # 1. Run statistical engines
            from syndicate.research.stats.agent_stats import full_report as agent_full_report
            from syndicate.research.stats.trade_attribution import full_report as trade_full_report

            loop = asyncio.get_event_loop()
            agent_stats = await loop.run_in_executor(None, agent_full_report)
            trade_attribution = await loop.run_in_executor(None, trade_full_report)

            # 2. Feed to Quant Researcher
            from syndicate.research.agents.quant_researcher import QuantResearcher

            quant = QuantResearcher(
                api_key=settings.get_active_llm_key(),
                provider=settings.default_llm_provider,
                model=settings.default_llm_model,
            )
            signal_health = await loop.run_in_executor(None, quant.analyze_signal_health, agent_stats)

            # 3. Feed to Strategy Researcher
            from syndicate.research.agents.strategy_researcher import StrategyResearcher

            strategist = StrategyResearcher(
                api_key=settings.get_active_llm_key(),
                provider=settings.default_llm_provider,
                model=settings.default_llm_model,
            )
            attribution_report = await loop.run_in_executor(None, strategist.analyze_attribution, trade_attribution)

            # 4. Save both reports to DB
            from syndicate.db.session import async_session_factory
            from syndicate.db.models import ResearchReportRow

            async with async_session_factory() as session:
                session.add(ResearchReportRow(
                    researcher="quant_researcher",
                    report_type="signal_decay",
                    title=signal_health.get("title", "Signal Health Report"),
                    summary=signal_health.get("decay_summary", ""),
                    findings=signal_health,
                    recommendations=[a.get("recommendation", "") for a in signal_health.get("agents_flagged", [])],
                    data_context={"source": "daily_automated", "agents_analyzed": len(agent_stats.get("agent_stats", {}))},
                ))
                session.add(ResearchReportRow(
                    researcher="strategy_researcher",
                    report_type="performance_attribution",
                    title=attribution_report.get("title", "Attribution Report"),
                    summary=attribution_report.get("overall_assessment", ""),
                    findings=attribution_report,
                    recommendations=[p for p in attribution_report.get("worst_patterns", [])],
                    data_context={"source": "daily_automated"},
                ))
                await session.commit()

            print(f"[RESEARCH] Daily reports saved: {signal_health.get('title', '?')}, {attribution_report.get('title', '?')}", flush=True)

        except Exception as e:
            import traceback
            logger.error("daily_research_failed", error=str(e), traceback=traceback.format_exc())

        await asyncio.sleep(60)

    print("[RESEARCH] Daily research task stopped.", flush=True)


async def _weekly_research_task(shutdown_event: asyncio.Event):
    """Runs weekly on Saturday at 04:00 UTC — deep research including data source evaluation and Head of Research digest."""
    print("[RESEARCH] Weekly research task starting...", flush=True)

    while not shutdown_event.is_set():
        try:
            # Wait until Saturday 04:00 UTC
            now = datetime.now(timezone.utc)
            days_until_saturday = (5 - now.weekday()) % 7
            if days_until_saturday == 0 and now.hour >= 4:
                days_until_saturday = 7
            next_run = (now + timedelta(days=days_until_saturday)).replace(
                hour=4, minute=0, second=0, microsecond=0
            )
            wait_secs = (next_run - now).total_seconds()

            print(f"[RESEARCH] Next weekly research at {next_run.isoformat()}", flush=True)

            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=wait_secs)
                break
            except asyncio.TimeoutError:
                pass

            print("[RESEARCH] Running weekly deep analysis...", flush=True)

            loop = asyncio.get_event_loop()

            # 1. Run all statistical engines
            from syndicate.research.stats.agent_stats import full_report as agent_full_report
            from syndicate.research.stats.trade_attribution import full_report as trade_full_report
            from syndicate.research.stats.data_source_eval import full_report as data_source_full_report

            agent_stats = await loop.run_in_executor(None, agent_full_report)
            trade_attribution = await loop.run_in_executor(None, trade_full_report)
            data_eval = await loop.run_in_executor(None, data_source_full_report)

            # 2. Quant Researcher: signal health + data source eval
            from syndicate.research.agents.quant_researcher import QuantResearcher
            quant = QuantResearcher(api_key=settings.get_active_llm_key(), provider=settings.default_llm_provider, model=settings.default_llm_model)
            signal_health = await loop.run_in_executor(None, quant.analyze_signal_health, agent_stats)
            data_source_report = await loop.run_in_executor(None, quant.evaluate_data_sources, data_eval)

            # 3. Strategy Researcher: attribution
            from syndicate.research.agents.strategy_researcher import StrategyResearcher
            strategist = StrategyResearcher(api_key=settings.get_active_llm_key(), provider=settings.default_llm_provider, model=settings.default_llm_model)
            attribution_report = await loop.run_in_executor(None, strategist.analyze_attribution, trade_attribution)

            # 4. Head of Research: weekly digest
            from syndicate.research.agents.head_of_research import HeadOfResearch
            head = HeadOfResearch(api_key=settings.get_active_llm_key(), provider=settings.default_llm_provider, model=settings.default_llm_model)
            digest = await loop.run_in_executor(None, head.produce_digest, {
                "quant_findings": signal_health,
                "strategy_findings": attribution_report,
                "agent_accuracy": {k: v.get("accuracy", 0) for k, v in agent_stats.get("agent_stats", {}).items()},
                "signal_decay_alerts": agent_stats.get("decay_alerts", []),
                "trade_attribution": trade_attribution.get("optimal_parameters", {}),
                "data_source_evaluation": data_source_report,
                "correlation_matrix": agent_stats.get("correlation", {}),
            })

            # 5. Save all reports to DB
            from syndicate.db.session import async_session_factory
            from syndicate.db.models import ResearchReportRow

            async with async_session_factory() as session:
                for report_data, researcher, rtype in [
                    (signal_health, "quant_researcher", "signal_decay"),
                    (data_source_report, "quant_researcher", "data_source_eval"),
                    (attribution_report, "strategy_researcher", "performance_attribution"),
                    (digest, "head_of_research", "weekly_digest"),
                ]:
                    session.add(ResearchReportRow(
                        researcher=researcher,
                        report_type=rtype,
                        title=report_data.get("title", f"{rtype} report"),
                        summary=report_data.get("executive_summary", report_data.get("overall_assessment", report_data.get("summary", ""))),
                        findings=report_data,
                        recommendations=report_data.get("recommendations_for_board", report_data.get("recommendations", [])),
                        data_context={"source": "weekly_automated", "week_of": now.isoformat()},
                    ))
                await session.commit()

            print(f"[RESEARCH] Weekly digest saved: {digest.get('title', '?')}", flush=True)

        except Exception as e:
            import traceback
            logger.error("weekly_research_failed", error=str(e), traceback=traceback.format_exc())

        await asyncio.sleep(60)

    print("[RESEARCH] Weekly research task stopped.", flush=True)


async def _fast_intelligence_loop(shutdown_event: asyncio.Event):
    """Fast loop — runs every 15 minutes. Monitors news, prices, portfolio risk."""
    from syndicate.intelligence.fast_loop import FastLoopOrchestrator

    orchestrator = FastLoopOrchestrator()
    interval = getattr(settings, "fast_loop_interval_minutes", 15) * 60

    # Wait 2 minutes before first run (let the system stabilize)
    await asyncio.sleep(120)

    while not shutdown_event.is_set():
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, orchestrator.run_once
            )
            if result.events:
                logger.info(
                    "fast_loop_iteration",
                    events=len(result.events),
                    actions=result.risk_actions_taken,
                    duration_ms=result.duration_ms,
                )
        except Exception as e:
            logger.error("fast_loop_error", error=str(e))

        # Sleep until next interval
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=interval)
            break
        except asyncio.TimeoutError:
            continue


async def _weather_oracle_loop(shutdown_event: asyncio.Event):
    """Background task that runs the Weather Oracle for Polymarket weather markets."""
    from syndicate.config import settings
    if not settings.polymarket_enabled:
        print("[ORACLE] Polymarket disabled (POLYMARKET_ENABLED=false)", flush=True)
        return

    print("[ORACLE] Weather Oracle starting...", flush=True)
    from syndicate.polymarket.oracle import oracle_loop
    await oracle_loop(shutdown_event)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    # Ensure all DB tables exist (handles new tables added after initial seed)
    from syndicate.db.session import engine as _db_engine
    from syndicate.db.models import Base as _Base
    async with _db_engine.begin() as conn:
        await conn.run_sync(_Base.metadata.create_all)

    # Seed comms if DB is empty (so transparency feed is never blank)
    try:
        from syndicate.comms.seed import ensure_comms_seeded
        seeded = await ensure_comms_seeded()
        if seeded:
            print("[SEED] Comms seeded successfully", flush=True)
    except Exception as e:
        logger.warning("comms_seed_failed", error=str(e))

    shutdown_event = asyncio.Event()

    # Start background tasks
    cycle_task = asyncio.create_task(_background_cycle_loop(shutdown_event))
    monitor_task = asyncio.create_task(_price_monitor(shutdown_event))
    briefing_task = asyncio.create_task(_daily_briefing_task(shutdown_event))
    blog_task = asyncio.create_task(_weekly_blog_task(shutdown_event))
    daily_research_task = asyncio.create_task(_daily_research_task(shutdown_event))
    weekly_research_task = asyncio.create_task(_weekly_research_task(shutdown_event))
    oracle_task = asyncio.create_task(_weather_oracle_loop(shutdown_event))
    fast_loop_task = asyncio.create_task(_fast_intelligence_loop(shutdown_event))

    yield

    # Shutdown
    shutdown_event.set()
    all_tasks = [
        cycle_task, monitor_task, briefing_task, blog_task,
        daily_research_task, weekly_research_task, oracle_task, fast_loop_task,
    ]
    for task in all_tasks:
        task.cancel()
    for task in all_tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass

    from syndicate.db.session import engine
    await engine.dispose()


app = FastAPI(
    title="Syndicate",
    description="Scalable Multi-Agent Crypto Analysis Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiting — simple in-memory token bucket per IP
import collections
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple per-IP rate limiter. 60 req/min reads, 10 req/min writes."""

    def __init__(self, app, read_limit: int = 60, write_limit: int = 10, window: int = 60):
        super().__init__(app)
        self._read_limit = read_limit
        self._write_limit = write_limit
        self._window = window
        self._hits: dict[str, list[float]] = collections.defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        key = f"{ip}:{'w' if request.method in ('POST', 'PUT', 'DELETE', 'PATCH') else 'r'}"
        limit = self._write_limit if "w" in key.split(":")[-1] else self._read_limit

        # Trim old entries
        self._hits[key] = [t for t in self._hits[key] if now - t < self._window]
        if len(self._hits[key]) >= limit:
            return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
        self._hits[key].append(now)
        return await call_next(request)


# CORS — allow frontend to call the API
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://syndicatefund.ai",
        "https://www.syndicatefund.ai",
        "https://api.hivemindfund.com",
        "https://hivemindfund.com",
        "https://www.hivemindfund.com",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware, read_limit=60, write_limit=10)

# Mount route modules
app.include_router(contributors.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(teams.router, prefix="/api/v1")
app.include_router(cycles.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(backtest.router, prefix="/api/v1")
app.include_router(signals.router, prefix="/api/v1")
app.include_router(ceo_posts.router, prefix="/api/v1")
app.include_router(research.router, prefix="/api/v1")
app.include_router(moltbook.router, prefix="/api/v1")
app.include_router(comms.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(leaderboard.router, prefix="/api/v1")
app.include_router(intelligence.router, prefix="/api/v1")
app.include_router(polymarket_router, prefix="/api/v1")


@app.get("/health")
async def health():
    """Health check endpoint — verifies DB and Redis connectivity."""
    status = "ok"
    checks = {}

    # Check DB
    try:
        from syndicate.db.session import async_session_factory
        async with async_session_factory() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {str(e)[:80]}"
        status = "degraded"

    # Check Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)[:80]}"
        status = "degraded"

    return {"status": status, "service": "syndicate", "checks": checks}
