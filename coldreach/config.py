"""
ColdReach configuration via pydantic-settings.

All settings are read from environment variables prefixed with ``COLDREACH_``
or from a ``.env`` file in the current working directory.

Example .env
------------
    COLDREACH_DATABASE_URL=sqlite+aiosqlite:///./coldreach.db
    COLDREACH_GROQ_API_KEY=gsk_xxx
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration for ColdReach.

    Every field can be overridden by an environment variable of the form
    ``COLDREACH_<FIELD_NAME_UPPER>``, or by a ``.env`` file entry.
    """

    model_config = SettingsConfigDict(
        env_prefix="COLDREACH_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./coldreach.db"
    """SQLAlchemy async database URL.

    Default is a local SQLite file — no Docker needed.
    Switch to PostgreSQL by setting:
        COLDREACH_DATABASE_URL=postgresql+asyncpg://coldreach:coldreach_dev@localhost:5432/coldreach
    """

    # ── Cache (Redis) ─────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    """Redis URL for result caching. Requires: docker compose up redis."""

    cache_ttl_days: int = 7
    """How many days to keep cached domain results before re-scanning."""

    # ── Docker service URLs ───────────────────────────────────────────────────
    searxng_url: str = "http://localhost:8080"
    """Self-hosted SearXNG metasearch instance. docker compose up searxng"""

    firecrawl_url: str = "http://localhost:3002"
    """Self-hosted Firecrawl JS-site crawler. docker compose up firecrawl"""

    spiderfoot_url: str = "http://localhost:5001"
    """Self-hosted SpiderFoot OSINT engine. docker compose up spiderfoot"""

    reacher_url: str = "http://localhost:8083"
    """Self-hosted Reacher SMTP verifier. docker compose up reacher"""

    # ── Optional API keys (never required for core functionality) ─────────────
    groq_api_key: str | None = None
    """Groq API key — unlocks LLM email personalization.
    Free tier: https://console.groq.com/  (14,400 tokens/min)
    """

    # ── Verification behaviour ────────────────────────────────────────────────
    smtp_timeout: int = 10
    """Seconds to wait for SMTP RCPT TO response."""

    dns_timeout: float = 5.0
    """Seconds to wait for DNS resolution."""

    # ── Concurrency ───────────────────────────────────────────────────────────
    max_concurrent_sources: int = 5
    """Maximum number of data sources to query in parallel per domain scan."""

    request_delay_seconds: float = 1.0
    """Minimum delay between outgoing HTTP requests to the same host."""

    # ── Scoring ───────────────────────────────────────────────────────────────
    min_confidence_to_display: int = 20
    """Emails below this confidence score are hidden from default output."""

    # ── Validators ────────────────────────────────────────────────────────────
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not (v.startswith("sqlite") or v.startswith("postgresql")):
            raise ValueError(
                "database_url must start with 'sqlite' or 'postgresql'. "
                f"Got: {v!r}"
            )
        return v

    @field_validator("cache_ttl_days")
    @classmethod
    def validate_cache_ttl(cls, v: int) -> int:
        if v < 1:
            raise ValueError("cache_ttl_days must be at least 1")
        return v

    @field_validator("max_concurrent_sources")
    @classmethod
    def validate_concurrency(cls, v: int) -> int:
        if v < 1 or v > 20:
            raise ValueError("max_concurrent_sources must be between 1 and 20")
        return v

    @property
    def has_groq(self) -> bool:
        """True if a Groq API key is configured."""
        return bool(self.groq_api_key)

    @property
    def using_sqlite(self) -> bool:
        """True if the database backend is SQLite (no Docker needed)."""
        return self.database_url.startswith("sqlite")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance.

    Results are cached after the first call. To force a reload (e.g. in
    tests), call ``get_settings.cache_clear()`` first.

    Returns
    -------
    Settings
        The application settings loaded from env / .env file.
    """
    return Settings()
