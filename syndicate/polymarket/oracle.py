"""Weather Oracle — main orchestrator loop."""

from __future__ import annotations

import asyncio
import time

import structlog
from datetime import datetime, timezone

from syndicate.polymarket.config import PolymarketSettings
from syndicate.polymarket.data.gamma_client import discover_weather_markets
from syndicate.polymarket.data.open_meteo import fetch_ensemble_forecast
from syndicate.polymarket.forecast.ensemble import blend_ensembles
from syndicate.polymarket.forecast.probability import compute_bin_probabilities
from syndicate.polymarket.forecast.emos import EMOSCalibrator
from syndicate.polymarket.forecast.bias_correction import BiasTracker
from syndicate.polymarket.forecast.model_weighting import ModelWeightTracker
from syndicate.polymarket.forecast.probability import compute_bin_probabilities_calibrated
from syndicate.polymarket.resolution.calibration import CalibrationTracker
from syndicate.polymarket.markets.edge import compute_horizon_hours, detect_edges
from syndicate.polymarket.markets.sizing import size_position
from syndicate.polymarket.execution.paper_trader import WeatherPaperTrader
from syndicate.polymarket.resolution.tracker import check_resolutions
from syndicate.polymarket.models import MarketAnalysis, OracleStatus
from syndicate.polymarket.constants import CITY_STATIONS
from syndicate.polymarket.markets.timing import optimal_scan_interval, is_fresh_data_window, next_model_release
from syndicate.polymarket.markets.laddering import ladder_allocation

logger = structlog.get_logger()


class WeatherOracle:
    """Main orchestrator for the weather trading pipeline."""

    def __init__(self) -> None:
        self.settings = PolymarketSettings()
        self.trader = WeatherPaperTrader.load()
        self.status = OracleStatus()
        self._start_time = time.monotonic()
        self._last_markets: list = []
        self._calibration_ready = False

        # Persistent calibration components — loaded once, updated continuously
        self._emos = EMOSCalibrator()
        self._bias_tracker = BiasTracker()
        self._model_weights = ModelWeightTracker()
        self._calibration_tracker = CalibrationTracker()
        self._load_calibration()

    def _load_calibration(self) -> None:
        """Load all persisted calibration state from disk."""
        data_dir = self.settings.polymarket_data_dir
        emos_path = data_dir / "emos_params.json"
        bias_path = data_dir / "bias_history.json"
        weights_path = data_dir / "model_weights.json"

        if emos_path.exists():
            self._emos.load(emos_path)
            self._calibration_ready = True
        self._bias_tracker.load(bias_path)
        self._model_weights.load(weights_path)
        self._calibration_tracker.load()

    def _save_calibration(self) -> None:
        """Persist all calibration state to disk."""
        data_dir = self.settings.polymarket_data_dir
        self._emos.save(data_dir / "emos_params.json")
        self._bias_tracker.save(data_dir / "bias_history.json")
        self._model_weights.save(data_dir / "model_weights.json")
        self._calibration_tracker.save()

    async def run_cycle(self) -> dict:
        """Run one full cycle: discover -> forecast -> analyze -> trade -> resolve.

        Returns summary dict of what happened.
        """
        summary: dict = {
            "markets_found": 0,
            "forecasts_fetched": 0,
            "edges_detected": 0,
            "bets_placed": 0,
            "positions_resolved": 0,
            "errors": [],
        }

        try:
            # 1. Discover markets
            markets = await discover_weather_markets()
            summary["markets_found"] = len(markets)
            self._last_markets = markets

            # 2. For each market, fetch forecast + analyze
            for market in markets:
                try:
                    city_key = market.city
                    config = CITY_STATIONS.get(city_key)
                    if not config:
                        # Try fuzzy match
                        for key, cfg in CITY_STATIONS.items():
                            if key.lower() in city_key.lower() or city_key.lower() in key.lower():
                                config = cfg
                                break
                    if not config:
                        continue

                    # Check horizon
                    horizon = compute_horizon_hours(market.date)
                    if horizon > self.settings.polymarket_max_horizon_hours:
                        continue
                    if horizon < 0:
                        continue  # Already past

                    # Fetch ensemble forecast
                    forecast = await fetch_ensemble_forecast(
                        city=market.city,
                        lat=config.latitude,
                        lon=config.longitude,
                        unit=config.unit,
                        target_date=market.date,
                    )
                    if not forecast.members:
                        continue
                    summary["forecasts_fetched"] += 1

                    # Compute bin probabilities
                    blend = blend_ensembles(forecast)
                    bin_probs = compute_bin_probabilities(forecast, market.bins)

                    # Try calibrated probabilities if EMOS is trained
                    try:
                        if self._calibration_ready:
                            corrected_mean = self._bias_tracker.correct(
                                market.city, blend["mean"],
                            )
                            cal_mean, cal_std = self._emos.calibrate(
                                market.city, corrected_mean, blend["std"],
                            )
                            bin_probs = compute_bin_probabilities_calibrated(
                                forecast, market.bins, cal_mean, cal_std,
                            )
                    except Exception as cal_err:
                        logger.debug(
                            "calibration_fallback",
                            city=market.city,
                            error=str(cal_err),
                        )
                        # Fall back to raw member counting (bin_probs unchanged)

                    # Build analysis
                    analysis = MarketAnalysis(
                        condition_id=market.condition_id,
                        city=market.city,
                        date=market.date,
                        horizon_hours=horizon,
                        forecast_mean=blend["mean"],
                        forecast_std=blend["std"],
                        bin_probabilities=bin_probs,
                        best_edge=max((bp.edge for bp in bin_probs), default=0),
                        best_edge_bin=(
                            max(bin_probs, key=lambda bp: bp.edge).bin_index
                            if bin_probs
                            else 0
                        ),
                        analyzed_at=datetime.now(timezone.utc),
                    )

                    # Detect edges
                    opportunities = detect_edges(analysis)
                    summary["edges_detected"] += len(opportunities)

                    # Size and place bets — use laddering to spread across adjacent bins
                    portfolio = self.trader.get_portfolio()
                    if opportunities:
                        # Use total Kelly amount for the best opportunity
                        best_opp = opportunities[0]
                        total_amount = size_position(
                            prob=best_opp,
                            portfolio=portfolio,
                            city=market.city,
                            date=market.date,
                        )
                        if total_amount > 0:
                            legs = ladder_allocation(
                                opportunities=opportunities,
                                all_bin_probs=bin_probs,
                                total_amount=total_amount,
                            )
                            for opp, amount in legs:
                                if amount <= 0:
                                    continue
                                token_id = ""
                                for b in market.bins:
                                    if b.index == opp.bin_index:
                                        token_id = b.token_id
                                        break
                                result = self.trader.place_bet(
                                    condition_id=market.condition_id,
                                    token_id=token_id,
                                    city=market.city,
                                    date=market.date,
                                    bin_label=opp.label,
                                    entry_price=opp.market_price,
                                    quantity=amount,
                                    model_prob=opp.model_prob,
                                    edge=opp.edge,
                                    forecast_mean=blend["mean"],
                                    forecast_std=blend["std"],
                                    total_market_volume=market.total_volume,
                                    n_bins=len(market.bins),
                                )
                                if result is not None:
                                    summary["bets_placed"] += 1

                except Exception as e:
                    summary["errors"].append(f"{market.city}/{market.date}: {str(e)}")
                    logger.error(
                        "market_analysis_failed",
                        city=market.city,
                        date=market.date,
                        error=str(e),
                    )

            # 3. Check resolutions — pass calibration components for feedback
            results = await check_resolutions(
                self.trader, markets,
                calibration_tracker=self._calibration_tracker,
                bias_tracker=self._bias_tracker,
                emos=self._emos,
                model_weights=self._model_weights,
            )
            summary["positions_resolved"] = len(results)

            # 4. Save state + calibration
            self.trader.save()
            self._save_calibration()

            # 5. Update status
            portfolio = self.trader.get_portfolio()
            self.status = OracleStatus(
                running=True,
                last_scan=datetime.now(timezone.utc),
                markets_tracked=len(markets),
                open_positions=len([p for p in portfolio.positions if not p.resolved]),
                portfolio_value=portfolio.total_value,
                total_pnl=portfolio.total_pnl,
                uptime_seconds=time.monotonic() - self._start_time,
            )

        except Exception as e:
            summary["errors"].append(f"cycle_error: {str(e)}")
            logger.error("oracle_cycle_failed", error=str(e))

        logger.info(
            "oracle_cycle_complete",
            **{k: v for k, v in summary.items() if k != "errors"},
        )
        return summary


# ── Global Instance ───────────────────────────────────────────────────────

_oracle: WeatherOracle | None = None


def get_oracle() -> WeatherOracle:
    """Return the global WeatherOracle singleton (lazy-initialized)."""
    global _oracle
    if _oracle is None:
        _oracle = WeatherOracle()
    return _oracle


async def _auto_bootstrap_calibration() -> None:
    """Bootstrap EMOS calibration on first run if no data exists."""
    settings = PolymarketSettings()
    emos_path = settings.polymarket_data_dir / "emos_params.json"

    if emos_path.exists():
        print("[ORACLE] EMOS calibration loaded.", flush=True)
        return

    print("[ORACLE] No calibration data — bootstrapping from 14 days of history...", flush=True)
    try:
        from syndicate.polymarket.data.historical_fetcher import backfill_all_cities, save_historical
        from syndicate.polymarket.forecast.emos import EMOSCalibrator
        from syndicate.polymarket.forecast.bias_correction import BiasTracker
        from syndicate.polymarket.forecast.model_weighting import ModelWeightTracker

        data = await backfill_all_cities(days_back=14)
        total = sum(len(v) for v in data.values())
        print(f"[ORACLE] Fetched {total} historical data points.", flush=True)

        emos = EMOSCalibrator()
        bias = BiasTracker()
        mw = ModelWeightTracker()

        for city, points in data.items():
            for p in points:
                em = p.get("ensemble_mean")
                es = p.get("ensemble_std")
                actual = p.get("actual")
                if em is None or actual is None:
                    continue
                # Skip points where ensemble_std is missing — don't use default 2.0
                # which contaminates EMOS training with fake spread values
                if es is None or es <= 0:
                    bias.update(city, em, actual)
                    continue
                emos.add_training_point(city, em, es, actual)
                bias.update(city, em, actual)
                for model, mean in p.get("model_means", {}).items():
                    model_std = p.get("model_stds", {}).get(model, es)
                    if mean is not None:
                        mw.update(model, mean, model_std or es, actual)
            emos.fit_city(city)

        emos.save(emos_path)
        bias.save()
        mw.save()
        save_historical(data, settings.polymarket_data_dir / "historical_data.json")

        print(f"[ORACLE] Calibration bootstrapped ({total} points, {len(data)} cities).", flush=True)
    except Exception as e:
        print(f"[ORACLE] Bootstrap failed (will use raw counting): {e}", flush=True)


async def oracle_loop(shutdown_event: asyncio.Event) -> None:
    """Background loop — runs oracle cycle with dynamic scan intervals."""
    oracle = get_oracle()
    settings = PolymarketSettings()

    print(
        f"[ORACLE] Weather Oracle starting "
        f"(paper={settings.polymarket_paper_trading})...",
        flush=True,
    )

    # Auto-bootstrap calibration on first deploy
    await _auto_bootstrap_calibration()

    while not shutdown_event.is_set():
        try:
            print("[ORACLE] Starting cycle...", flush=True)
            summary = await oracle.run_cycle()
            print(
                f"[ORACLE] Cycle: {summary['markets_found']} markets, "
                f"{summary['edges_detected']} edges, "
                f"{summary['bets_placed']} bets, "
                f"{summary['positions_resolved']} resolved",
                flush=True,
            )
            if summary.get("errors"):
                for err in summary["errors"][:5]:
                    print(f"[ORACLE] Error: {err}", flush=True)
        except Exception as e:
            import traceback
            print(f"[ORACLE] Cycle CRASHED: {e}", flush=True)
            traceback.print_exc()

        # Use dynamic scan interval based on model release timing
        interval = optimal_scan_interval()
        fresh = is_fresh_data_window()
        if fresh:
            logger.info("oracle.fresh_data_window", interval=interval)

        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=interval)
            break
        except asyncio.TimeoutError:
            pass

    print("[ORACLE] Weather Oracle stopped.", flush=True)
