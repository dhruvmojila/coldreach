"""
Shared pytest fixtures for all test modules.
"""

from __future__ import annotations

import pytest

from coldreach.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:  # type: ignore[return]
    """Clear the lru_cache on get_settings before each test.

    Prevents settings from one test leaking into another.
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def settings() -> Settings:
    """Return a Settings instance wired for tests (SQLite in-memory, no keys)."""
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/15",
        groq_api_key=None,
        cache_ttl_days=1,
    )


# ── Email fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def valid_email() -> str:
    return "john.smith@example.com"


@pytest.fixture
def valid_email_mixed_case() -> str:
    return "John.Smith@Example.COM"


@pytest.fixture
def disposable_email() -> str:
    return "test@mailinator.com"


@pytest.fixture
def invalid_email_no_at() -> str:
    return "notanemail"


@pytest.fixture
def invalid_email_no_domain() -> str:
    return "user@"


@pytest.fixture
def invalid_email_no_local() -> str:
    return "@example.com"
