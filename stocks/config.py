"""
Stock-specific configuration — market hours, earnings blackout, universe settings.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StockSettings(BaseSettings):
    """Stock-specific settings layered on top of hivemind base settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Market Hours (US Eastern) ──
    market_open_hour: int = 9
    market_open_minute: int = 30
    market_close_hour: int = 16
    market_close_minute: int = 0

    # ── Earnings Blackout ──
    earnings_blackout_days: int = 3  # Block new positions N days before earnings

    # ── Universe ──
    max_stocks_per_cycle: int = 10
    include_sp500: bool = True
    include_russell1000: bool = True
    hot_stock_max_additions: int = 3

    # ── News ──
    finnhub_api_key: str = ""
    newsapi_key: str = ""

    # ── SEC EDGAR ──
    sec_edgar_user_agent: str = "Hivemind/1.0 (research@hivemind.ai)"

    # ── Data Paths ──
    stock_data_dir: str = "data/stocks"
    stock_ceo_memory_path: str = "data/stocks/ceo_memory.json"
    stock_team_weights_path: str = "data/stocks/team_weights.json"
    stock_open_trades_path: str = "data/stocks/open_trades.json"
    stock_trade_ledger_path: str = "data/stocks/trade_ledger.json"
    stock_performance_path: str = "data/stocks/performance_history.json"
    stock_watchlist_path: str = "data/stocks/watchlist.json"

    # ── Paths ──
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent)


# Singleton
stock_settings = StockSettings()
