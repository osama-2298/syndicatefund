"""Syndicate FastAPI application."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import FastAPI

from hivemind.api.routes import agents, backtest, contributors, cycles, portfolio, signals, teams
from hivemind.config import settings

logger = structlog.get_logger()

CYCLE_INTERVAL_HOURS = 4


async def _load_registry():
    """Load the agent registry from the database."""
    from hivemind.core.agent_registry import AgentRegistry
    from hivemind.db.session import async_session_factory

    async with async_session_factory() as session:
        registry = AgentRegistry(session)
        await registry.load_all()
        return registry


async def _background_cycle_loop(shutdown_event: asyncio.Event):
    """Background task that runs the analysis pipeline every 4 hours."""
    import sys
    print("[CYCLE] Background cycle loop starting...", flush=True)

    try:
        from hivemind.data.binance_client import BinanceClient
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
                from hivemind.main import run_pipeline
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
                from hivemind.config import settings
                from hivemind.execution.trade_monitor import TradeMonitor
                from hivemind.execution.paper_trader import PaperTrader
                from hivemind.execution.trade_ledger import TradeLedger
                from hivemind.data.models import OrderSide

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

                # Execute triggered exits
                if triggered:
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    shutdown_event = asyncio.Event()

    # Start background tasks
    cycle_task = asyncio.create_task(_background_cycle_loop(shutdown_event))
    monitor_task = asyncio.create_task(_price_monitor(shutdown_event))

    yield

    # Shutdown
    shutdown_event.set()
    cycle_task.cancel()
    monitor_task.cancel()
    try:
        await cycle_task
    except asyncio.CancelledError:
        pass
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass

    from hivemind.db.session import engine
    await engine.dispose()


app = FastAPI(
    title="Syndicate",
    description="Scalable Multi-Agent Crypto Analysis Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend to call the API
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://syndicatefund.ai",
        "https://www.syndicatefund.ai",
        "http://localhost:3000",  # Local dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount route modules
app.include_router(contributors.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(teams.router, prefix="/api/v1")
app.include_router(cycles.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(backtest.router, prefix="/api/v1")
app.include_router(signals.router, prefix="/api/v1")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "hivemind"}
