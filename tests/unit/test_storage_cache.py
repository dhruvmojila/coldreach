"""
Unit tests for coldreach.storage.cache.CacheStore

Uses in-memory SQLite (:memory: via db_path=None fallback won't work since
:memory: isn't exposed directly; instead we use a tmp_path fixture).
No Redis — all Redis-dependent paths are exercised with a dummy URL that
fails gracefully.
"""

from __future__ import annotations

import time

import pytest

from coldreach.core.models import DomainResult, EmailRecord, VerificationStatus
from coldreach.storage.cache import CacheStore


def _make_result(domain: str, emails: list[str] | None = None) -> DomainResult:
    result = DomainResult(domain=domain)
    for addr in emails or [f"ceo@{domain}", f"cto@{domain}"]:
        result.add_email(
            EmailRecord(
                email=addr,
                confidence=75,
                status=VerificationStatus.UNKNOWN,
            )
        )
    return result


@pytest.fixture
def store(tmp_path) -> CacheStore:
    db = str(tmp_path / "test_cache.db")
    return CacheStore(db_path=db, ttl_days=7)


class TestCacheStoreMiss:
    def test_get_returns_none_for_unknown_domain(self, store: CacheStore) -> None:
        assert store.get("notcached.com") is None

    def test_list_empty_when_no_entries(self, store: CacheStore) -> None:
        assert store.list_domains() == []

    def test_stats_zero_when_empty(self, store: CacheStore) -> None:
        s = store.stats()
        assert s["total"] == 0
        assert s["valid"] == 0
        assert s["expired"] == 0


class TestCacheStoreSetGet:
    def test_get_returns_stored_result(self, store: CacheStore) -> None:
        result = _make_result("stripe.com")
        store.set("stripe.com", result)
        cached = store.get("stripe.com")
        assert cached is not None
        assert cached.domain == "stripe.com"

    def test_emails_round_trip(self, store: CacheStore) -> None:
        result = _make_result("acme.com", ["ceo@acme.com", "hr@acme.com"])
        store.set("acme.com", result)
        cached = store.get("acme.com")
        assert cached is not None
        emails = [r.email for r in cached.emails]
        assert "ceo@acme.com" in emails
        assert "hr@acme.com" in emails

    def test_set_overwrites_existing_entry(self, store: CacheStore) -> None:
        store.set("acme.com", _make_result("acme.com", ["old@acme.com"]))
        store.set("acme.com", _make_result("acme.com", ["new@acme.com"]))
        cached = store.get("acme.com")
        assert cached is not None
        emails = [r.email for r in cached.emails]
        assert "new@acme.com" in emails
        assert "old@acme.com" not in emails

    def test_domain_normalised_to_lowercase(self, store: CacheStore) -> None:
        store.set("Stripe.COM", _make_result("stripe.com"))
        cached = store.get("stripe.com")
        assert cached is not None

    def test_multiple_domains_independent(self, store: CacheStore) -> None:
        store.set("a.com", _make_result("a.com", ["x@a.com"]))
        store.set("b.com", _make_result("b.com", ["x@b.com"]))
        a = store.get("a.com")
        b = store.get("b.com")
        assert a is not None
        assert a.domain == "a.com"
        assert b is not None
        assert b.domain == "b.com"


class TestCacheStoreExpiry:
    def test_expired_entry_returns_none(self, tmp_path) -> None:
        store = CacheStore(db_path=str(tmp_path / "exp.db"), ttl_days=0)
        # TTL = 0 days = 0 seconds → already expired on write
        store.set("expired.com", _make_result("expired.com"))
        # Force expires_at to be in the past
        import sqlite3

        db_path = str(tmp_path / "exp.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE domain_cache SET expires_at = ? WHERE domain = ?",
                (time.time() - 1, "expired.com"),
            )
        assert store.get("expired.com") is None

    def test_valid_entry_not_expired(self, store: CacheStore) -> None:
        store.set("fresh.com", _make_result("fresh.com"))
        assert store.get("fresh.com") is not None


class TestCacheStoreClear:
    def test_clear_specific_domain(self, store: CacheStore) -> None:
        store.set("a.com", _make_result("a.com"))
        store.set("b.com", _make_result("b.com"))
        deleted = store.clear(domain="a.com")
        assert deleted == 1
        assert store.get("a.com") is None
        assert store.get("b.com") is not None

    def test_clear_all(self, store: CacheStore) -> None:
        store.set("a.com", _make_result("a.com"))
        store.set("b.com", _make_result("b.com"))
        deleted = store.clear()
        assert deleted == 2
        assert store.get("a.com") is None
        assert store.get("b.com") is None

    def test_clear_nonexistent_domain_returns_zero(self, store: CacheStore) -> None:
        assert store.clear(domain="nobody.com") == 0


class TestCacheStoreList:
    def test_list_returns_cached_domains(self, store: CacheStore) -> None:
        store.set("x.com", _make_result("x.com"))
        store.set("y.com", _make_result("y.com"))
        domains = [d for d, _, _ in store.list_domains()]
        assert "x.com" in domains
        assert "y.com" in domains

    def test_list_returns_expired_flag(self, tmp_path) -> None:
        store = CacheStore(db_path=str(tmp_path / "lst.db"), ttl_days=7)
        store.set("ok.com", _make_result("ok.com"))
        import sqlite3

        with sqlite3.connect(str(tmp_path / "lst.db")) as conn:
            conn.execute(
                "UPDATE domain_cache SET expires_at = ? WHERE domain = ?",
                (time.time() - 1, "ok.com"),
            )
        entries = store.list_domains()
        assert len(entries) == 1
        _, _, is_expired = entries[0]
        assert is_expired is True


class TestCacheStoreStats:
    def test_stats_counts_valid_and_expired(self, tmp_path) -> None:
        store = CacheStore(db_path=str(tmp_path / "stats.db"), ttl_days=7)
        store.set("valid.com", _make_result("valid.com"))
        store.set("old.com", _make_result("old.com"))
        import sqlite3

        with sqlite3.connect(str(tmp_path / "stats.db")) as conn:
            conn.execute(
                "UPDATE domain_cache SET expires_at = ? WHERE domain = ?",
                (time.time() - 1, "old.com"),
            )
        s = store.stats()
        assert s["total"] == 2
        assert s["valid"] == 1
        assert s["expired"] == 1


class TestCacheStoreRedisFailsGracefully:
    def test_invalid_redis_url_does_not_raise(self, tmp_path) -> None:
        store = CacheStore(
            db_path=str(tmp_path / "r.db"),
            redis_url="redis://localhost:19999/0",  # nothing listening there
        )
        assert store._redis is None  # Redis disabled after failed ping

    def test_sqlite_still_works_when_redis_unavailable(self, tmp_path) -> None:
        store = CacheStore(
            db_path=str(tmp_path / "r2.db"),
            redis_url="redis://localhost:19999/0",
        )
        store.set("fallback.com", _make_result("fallback.com"))
        assert store.get("fallback.com") is not None
