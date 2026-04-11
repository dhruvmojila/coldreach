"""
Unit tests for coldreach.config.Settings

Uses environment variable injection — no .env file required.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from coldreach.config import Settings, get_settings


class TestSettings:
    """Tests for the Settings Pydantic-settings model."""

    def test_default_database_url_is_sqlite(self) -> None:
        s = Settings()
        assert s.database_url.startswith("sqlite")

    def test_using_sqlite_property_true_for_default(self) -> None:
        s = Settings()
        assert s.using_sqlite is True

    def test_using_sqlite_property_false_for_postgresql(self) -> None:
        s = Settings(database_url="postgresql+asyncpg://user:pw@localhost:5432/db")
        assert s.using_sqlite is False

    def test_has_groq_false_when_no_key(self) -> None:
        s = Settings(groq_api_key=None)
        assert s.has_groq is False

    def test_has_groq_true_when_key_provided(self) -> None:
        s = Settings(groq_api_key="gsk_testkey")
        assert s.has_groq is True

    def test_invalid_database_url_raises(self) -> None:
        with pytest.raises(ValidationError):
            Settings(database_url="mysql://localhost/db")

    def test_cache_ttl_below_1_raises(self) -> None:
        with pytest.raises(ValidationError):
            Settings(cache_ttl_days=0)

    def test_max_concurrent_sources_above_20_raises(self) -> None:
        with pytest.raises(ValidationError):
            Settings(max_concurrent_sources=21)

    def test_max_concurrent_sources_below_1_raises(self) -> None:
        with pytest.raises(ValidationError):
            Settings(max_concurrent_sources=0)

    def test_env_prefix_is_coldreach(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("COLDREACH_CACHE_TTL_DAYS", "14")
        s = Settings()
        assert s.cache_ttl_days == 14

    def test_case_insensitive_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("coldreach_cache_ttl_days", "3")
        s = Settings()
        assert s.cache_ttl_days == 3

    def test_default_redis_url(self) -> None:
        s = Settings()
        assert "localhost" in s.redis_url or "redis" in s.redis_url

    def test_default_smtp_timeout(self) -> None:
        s = Settings()
        assert s.smtp_timeout > 0

    def test_default_request_delay(self) -> None:
        s = Settings()
        assert s.request_delay_seconds >= 0


class TestGetSettings:
    """Tests for the get_settings() cached factory."""

    def test_returns_settings_instance(self) -> None:
        s = get_settings()
        assert isinstance(s, Settings)

    def test_returns_same_instance_on_repeated_calls(self) -> None:
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_cache_clear_returns_fresh_instance(self) -> None:
        s1 = get_settings()
        get_settings.cache_clear()
        s2 = get_settings()
        # Different object but same config
        assert s1 is not s2
        assert s1.database_url == s2.database_url
