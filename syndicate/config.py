"""
Syndicate configuration — loads from environment variables with validation.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables / .env file.
    Validates that required keys are present at startup, not at trade time.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    default_llm_provider: LLMProvider = LLMProvider.ANTHROPIC
    default_llm_model: str = "claude-opus-4-6"

    # ── Binance ──
    binance_api_key: str = ""
    binance_secret_key: str = ""
    binance_base_url: str = "https://api.binance.com"

    # ── Database ──
    database_url: str = "postgresql+asyncpg://syndicate:syndicate@localhost:5432/syndicate"

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        """Railway provides postgresql:// — we need postgresql+asyncpg://"""
        if v and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"

    # ── WhatsApp ──
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""

    # ── CryptoPanic ──
    cryptopanic_api_key: str = ""

    # ── Encryption ──
    syndicate_encryption_key: str = ""  # 32-byte hex for AES-256-GCM

    # ── Server ──
    serve_host: str = "0.0.0.0"
    serve_port: int = 8000
    port: int = 0  # Railway sets PORT env var — takes precedence over serve_port

    # ── Platform ──
    paper_trading: bool = True
    log_level: str = "INFO"
    max_coins_per_cycle: int = 10
    min_volume_24h: float = 1_000_000
    performance_history_path: str = ""

    # ── Decision Mode ──
    # "every_cycle": make trading decisions every 4h cycle (original behavior)
    # "daily": collect data every 4h, but only execute trades at 00:00 UTC cycle
    decision_mode: str = "daily"

    # ── Paths ──
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent)

    @property
    def data_dir(self) -> Path:
        d = self.project_root / "data"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def portfolio_state_path(self) -> str:
        return str(self.data_dir / "portfolio_state.json")

    @property
    def open_trades_path(self) -> str:
        return str(self.data_dir / "open_trades.json")

    @property
    def trade_ledger_path(self) -> str:
        return str(self.data_dir / "trade_ledger.json")

    @property
    def ceo_memory_path(self) -> str:
        return str(self.data_dir / "ceo_memory.json")

    @property
    def team_weights_path(self) -> str:
        return str(self.data_dir / "team_weights.json")

    @property
    def whale_history_path(self) -> str:
        return str(self.data_dir / "whale_history.json")

    @property
    def perf_history_path(self) -> str:
        if self.performance_history_path:
            return self.performance_history_path
        return str(self.data_dir / "performance_history.json")

    @field_validator("decision_mode")
    @classmethod
    def validate_decision_mode(cls, v: str) -> str:
        allowed = {"every_cycle", "daily"}
        if v not in allowed:
            raise ValueError(f"decision_mode must be one of {allowed}, got '{v}'")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got '{v}'")
        return upper

    def get_active_llm_key(self) -> str:
        """Return the API key for the configured default LLM provider."""
        if self.default_llm_provider == LLMProvider.ANTHROPIC:
            if not self.anthropic_api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY is required when default_llm_provider=anthropic"
                )
            return self.anthropic_api_key
        elif self.default_llm_provider == LLMProvider.OPENAI:
            if not self.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY is required when default_llm_provider=openai"
                )
            return self.openai_api_key
        elif self.default_llm_provider == LLMProvider.GOOGLE:
            if not self.google_api_key:
                raise ValueError(
                    "GOOGLE_API_KEY is required when default_llm_provider=google"
                )
            return self.google_api_key
        raise ValueError(f"Unknown LLM provider: {self.default_llm_provider}")

    def has_binance_credentials(self) -> bool:
        """Check if Binance API credentials are configured (needed for execution)."""
        return bool(self.binance_api_key and self.binance_secret_key)


# Singleton — import this everywhere
settings = Settings()
