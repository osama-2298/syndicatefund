"""
Polymarket Weather Oracle — Configuration.

Pydantic-settings model for all oracle-specific settings.
Imports project-level settings from syndicate.config for paths and shared config.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from syndicate.config import settings as _syndicate_settings


class PolymarketSettings(BaseSettings):
    """
    Settings for the Polymarket Weather Oracle.

    Loaded from environment variables prefixed with POLYMARKET_ (or from .env).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Feature Flags ──
    polymarket_enabled: bool = False
    polymarket_paper_trading: bool = True

    # ── Authentication ──
    polymarket_private_key: str = ""
    polymarket_api_key: str = ""

    # ── Bankroll & Risk ──
    polymarket_bankroll: float = 10_000.0
    polymarket_min_edge: float = 0.08
    polymarket_max_kelly_fraction: float = 0.25

    # ── Scan Interval ──
    polymarket_scan_interval_seconds: int = 300

    # ── Horizon ──
    polymarket_max_horizon_hours: int = 72

    # ── Calibration ──
    polymarket_emos_training_window: int = 90  # days of history for EMOS fit
    polymarket_min_calibration_points: int = 20  # minimum observations before using EMOS
    polymarket_laddering_scheme: str = "gradient"  # "gradient", "equal", or "kelly"
    polymarket_daily_loss_limit: float = 0.10  # halt at -10% of bankroll
    polymarket_loss_streak_limit: int = 10  # pause after N consecutive losses

    # ── Live Trading ──
    polymarket_max_bet_live: float = 20.0  # Hard cap per bet ($20 initial rollout)
    polymarket_order_timeout_seconds: int = 300  # Cancel unfilled orders after 5 min
    polymarket_max_open_orders: int = 10  # Max concurrent pending orders
    polymarket_min_usdc_reserve: float = 50.0  # Always keep $50 buffer in wallet
    polymarket_kill_switch: bool = False  # Emergency halt flag
    polymarket_shadow_mode: bool = True  # Log but don't execute (first-run safety)
    polymarket_funder_address: str = ""  # Polymarket proxy wallet address (holds USDC.e)

    @property
    def polymarket_data_dir(self) -> Path:
        """Return (and create) the data directory for polymarket state files."""
        d = _syndicate_settings.project_root / "data" / "polymarket"
        d.mkdir(parents=True, exist_ok=True)
        return d


# Singleton — import this everywhere in the polymarket package
pm_settings = PolymarketSettings()
