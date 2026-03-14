"""
Hivemind configuration — loads from environment variables with validation.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


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
    default_llm_provider: LLMProvider = LLMProvider.ANTHROPIC
    default_llm_model: str = "claude-opus-4-6"

    # ── Binance ──
    binance_api_key: str = ""
    binance_secret_key: str = ""
    binance_base_url: str = "https://api.binance.com"

    # ── Database ──
    database_url: str = "postgresql+asyncpg://hivemind:hivemind@localhost:5432/hivemind"

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"

    # ── WhatsApp ──
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""

    # ── Platform ──
    paper_trading: bool = True
    log_level: str = "INFO"
    max_coins_per_cycle: int = 10
    min_volume_24h: float = 1_000_000
    performance_history_path: str = "data/performance_history.json"

    # ── Paths ──
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent)

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
        raise ValueError(f"Unknown LLM provider: {self.default_llm_provider}")

    def has_binance_credentials(self) -> bool:
        """Check if Binance API credentials are configured (needed for execution)."""
        return bool(self.binance_api_key and self.binance_secret_key)


# Singleton — import this everywhere
settings = Settings()
