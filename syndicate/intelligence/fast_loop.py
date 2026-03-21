"""
Fast Loop Orchestrator — 15-minute intelligence cycle.

Monitors news, portfolio risk, and price movements between the main
4-hour analysis cycles. This is where contributor scout bots operate.

Responsibilities:
1. Check CryptoPanic for breaking news
2. Flash crash / flash pump detection
3. Portfolio risk check (drawdown, heat, correlation)
4. Record events to DB + JSON fallback
5. Take emergency risk actions if thresholds breached
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import structlog

from syndicate.config import settings
from syndicate.intelligence.models import (
    AlertSeverity,
    FastLoopResult,
    IntelEvent,
    IntelEventType,
)

logger = structlog.get_logger()


class FastLoopOrchestrator:
    """
    Runs the fast intelligence loop every 15 minutes.

    Checks news, prices, portfolio risk — and records events for
    the dashboard and API.
    """

    def __init__(self) -> None:
        self._last_prices: dict[str, float] = {}
        self._last_run: datetime | None = None
        self._events_path = Path(settings.data_dir) / "fast_loop_events.json"

    def run_once(self) -> FastLoopResult:
        """Execute one fast loop iteration."""
        start = time.monotonic()
        result = FastLoopResult()

        # 1. Check news
        news_events = self._check_news()
        result.events.extend(news_events)
        result.news_checked = len(news_events)

        # 2. Check prices for flash moves
        price_events = self._check_prices()
        result.events.extend(price_events)
        result.prices_checked = len(self._last_prices)

        # 3. Portfolio risk check
        risk_events = self._check_portfolio_risk()
        result.events.extend(risk_events)

        # 4. Count risk actions
        result.risk_actions_taken = sum(1 for e in result.events if e.acted_upon)

        # 5. Persist events
        result.duration_ms = int((time.monotonic() - start) * 1000)
        self._persist_events(result)

        self._last_run = datetime.now(timezone.utc)

        if result.events:
            logger.info(
                "fast_loop_complete",
                events=len(result.events),
                actions=result.risk_actions_taken,
                duration_ms=result.duration_ms,
            )

        return result

    def _check_news(self) -> list[IntelEvent]:
        """Check CryptoPanic for breaking news."""
        events = []
        try:
            api_key = settings.cryptopanic_api_key
            if not api_key:
                return events

            import httpx

            url = f"https://cryptopanic.com/api/v1/posts/?auth_token={api_key}&kind=news&filter=hot"
            with httpx.Client(timeout=10) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    return events

                data = resp.json()
                posts = data.get("results", [])

                for post in posts[:5]:
                    title = post.get("title", "")
                    published = post.get("published_at", "")
                    votes = post.get("votes", {})
                    positive = votes.get("positive", 0)
                    negative = votes.get("negative", 0)
                    important = votes.get("important", 0)

                    # Determine severity from community voting
                    if important >= 5 or (positive + negative) >= 20:
                        severity = AlertSeverity.HIGH
                    elif important >= 2 or (positive + negative) >= 10:
                        severity = AlertSeverity.MEDIUM
                    else:
                        severity = AlertSeverity.LOW

                    # Extract related symbols
                    currencies = post.get("currencies", [])
                    symbols = [
                        f"{c.get('code', '').upper()}USDT"
                        for c in currencies
                        if c.get("code")
                    ]

                    events.append(IntelEvent(
                        event_type=IntelEventType.NEWS_ALERT,
                        severity=severity,
                        source="cryptopanic",
                        title=title[:200],
                        detail={
                            "url": post.get("url", ""),
                            "source": post.get("source", {}).get("title", ""),
                            "votes_positive": positive,
                            "votes_negative": negative,
                            "votes_important": important,
                            "published_at": published,
                        },
                        symbols=symbols,
                    ))

        except Exception as e:
            logger.debug("fast_loop_news_error", error=str(e))

        return events

    def _check_prices(self) -> list[IntelEvent]:
        """Check for flash crashes or pumps (>5% move in <15 min)."""
        events = []
        try:
            from syndicate.data.models import PortfolioState

            # Load portfolio to know which symbols to monitor
            portfolio_path = Path(settings.portfolio_state_path)
            if not portfolio_path.exists():
                return events

            portfolio = PortfolioState.model_validate(
                json.loads(portfolio_path.read_text())
            )

            if not portfolio.positions:
                return events

            # Fetch current prices from Binance
            import httpx

            symbols = [p.symbol for p in portfolio.positions]
            formatted = json.dumps(symbols)
            url = f"https://data-api.binance.vision/api/v3/ticker/price?symbols={formatted}"

            with httpx.Client(timeout=5) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    return events

                prices = {item["symbol"]: float(item["price"]) for item in resp.json()}

            # Compare with last known prices
            for symbol, current_price in prices.items():
                last_price = self._last_prices.get(symbol)
                if last_price and last_price > 0:
                    change_pct = ((current_price - last_price) / last_price) * 100

                    if abs(change_pct) >= 5.0:
                        is_crash = change_pct < 0
                        event_type = IntelEventType.FLASH_CRASH if is_crash else IntelEventType.FLASH_PUMP
                        severity = AlertSeverity.CRITICAL if abs(change_pct) >= 10 else AlertSeverity.HIGH

                        events.append(IntelEvent(
                            event_type=event_type,
                            severity=severity,
                            source="price_monitor",
                            title=f"{symbol.replace('USDT', '')} {'crashed' if is_crash else 'pumped'} {change_pct:+.1f}% in 15min",
                            detail={
                                "symbol": symbol,
                                "previous_price": last_price,
                                "current_price": current_price,
                                "change_pct": round(change_pct, 2),
                            },
                            symbols=[symbol],
                            acted_upon=abs(change_pct) >= 10,
                            action_taken="alert_escalated" if abs(change_pct) >= 10 else None,
                        ))

            # Update last prices
            self._last_prices = prices

        except Exception as e:
            logger.debug("fast_loop_price_error", error=str(e))

        return events

    def _check_portfolio_risk(self) -> list[IntelEvent]:
        """Run portfolio-level risk check and generate events for significant changes."""
        events = []
        try:
            from syndicate.data.models import PortfolioState
            from syndicate.risk.portfolio_risk import PortfolioRiskManager

            portfolio_path = Path(settings.portfolio_state_path)
            if not portfolio_path.exists():
                return events

            portfolio = PortfolioState.model_validate(
                json.loads(portfolio_path.read_text())
            )

            risk_mgr = PortfolioRiskManager()

            # Load open trades for heat
            open_trades = None
            ot_path = Path(settings.open_trades_path)
            if ot_path.exists():
                try:
                    raw = json.loads(ot_path.read_text())
                    open_trades = list(raw.values()) if isinstance(raw, dict) else raw
                except Exception:
                    pass

            snapshot = risk_mgr.check(portfolio=portfolio, open_trades=open_trades)

            # Generate events for significant risk conditions
            if snapshot.drawdown_level.value >= 2:  # REDUCED or worse
                events.append(IntelEvent(
                    event_type=IntelEventType.RISK_ACTION,
                    severity=AlertSeverity.HIGH if snapshot.drawdown_level.value >= 3 else AlertSeverity.MEDIUM,
                    source="portfolio_risk",
                    title=f"Drawdown alert: {snapshot.drawdown_message}",
                    detail=snapshot.to_dict(),
                    acted_upon=snapshot.drawdown_level.value >= 3,
                    action_taken=f"drawdown_level_{snapshot.drawdown_level.name}" if snapshot.drawdown_level.value >= 3 else None,
                ))

            if snapshot.heat_exceeded:
                events.append(IntelEvent(
                    event_type=IntelEventType.RISK_ACTION,
                    severity=AlertSeverity.MEDIUM,
                    source="portfolio_risk",
                    title=f"Portfolio heat {snapshot.portfolio_heat*100:.1f}% exceeds {risk_mgr.max_heat*100:.0f}% limit",
                    detail={"portfolio_heat": round(snapshot.portfolio_heat, 4)},
                ))

            if snapshot.correlation_warning:
                events.append(IntelEvent(
                    event_type=IntelEventType.CORRELATION_SPIKE,
                    severity=AlertSeverity.MEDIUM,
                    source="portfolio_risk",
                    title=f"Correlation spike: avg {snapshot.avg_correlation:.2f}",
                    detail={
                        "avg_correlation": round(snapshot.avg_correlation, 4),
                        "matrix": snapshot.correlation_matrix,
                    },
                ))

            # Save latest risk snapshot
            rs_path = Path(settings.data_dir) / "latest_risk_snapshot.json"
            rs_path.parent.mkdir(parents=True, exist_ok=True)
            rs_path.write_text(json.dumps(snapshot.to_dict(), indent=2, default=str))

        except Exception as e:
            logger.debug("fast_loop_risk_error", error=str(e))

        return events

    def _persist_events(self, result: FastLoopResult) -> None:
        """Save fast loop events to JSON (DB persistence done by caller)."""
        if not result.events:
            return

        try:
            self._events_path.parent.mkdir(parents=True, exist_ok=True)

            # Load existing events
            existing = []
            if self._events_path.exists():
                try:
                    existing = json.loads(self._events_path.read_text())
                except Exception:
                    existing = []

            # Append new events
            for event in result.events:
                existing.append(event.to_dict())

            # Keep last 1000 events
            existing = existing[-1000:]

            self._events_path.write_text(json.dumps(existing, indent=2, default=str))

        except Exception as e:
            logger.warning("fast_loop_persist_error", error=str(e))

    @property
    def last_run(self) -> datetime | None:
        return self._last_run

    def get_status(self) -> dict:
        """Return current fast loop status for the API."""
        return {
            "running": True,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "monitored_symbols": len(self._last_prices),
            "events_file": str(self._events_path),
        }
