"""
Local result cache for ColdReach domain scans.

Two-layer cache:
  1. SQLite  — always available, stored at ~/.coldreach/cache.db
  2. Redis   — optional faster layer; used when redis_url is configured

Both layers use a 7-day TTL by default (configurable).

DomainResult objects are round-tripped via Pydantic JSON (model_dump_json /
model_validate_json), preserving all fields including nested EmailRecord and
SourceRecord objects.

Thread safety: SQLite connections are per-instance (not shared across
threads). For concurrent callers, instantiate one CacheStore per thread or
rely on SQLite's built-in WAL locking.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from datetime import UTC, datetime

from coldreach.core.models import DomainResult

logger = logging.getLogger(__name__)

_DEFAULT_DB = "~/.coldreach/cache.db"
_DEFAULT_TTL_DAYS = 7
_REDIS_PREFIX = "coldreach:domain:"


class CacheStore:
    """SQLite-backed domain result cache with optional Redis layer.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file. ``~`` is expanded automatically.
        Pass ``None`` to disable SQLite (Redis-only or no-op).
    redis_url:
        Redis connection URL, e.g. ``"redis://localhost:6380/0"``.
        Pass ``None`` to skip Redis.
    ttl_days:
        How long to keep cached results before they expire.
    """

    def __init__(
        self,
        db_path: str | None = _DEFAULT_DB,
        redis_url: str | None = None,
        ttl_days: int = _DEFAULT_TTL_DAYS,
    ) -> None:
        self.ttl_seconds = ttl_days * 86400
        self._db_path = os.path.expanduser(db_path) if db_path else None
        self._redis: object = None

        if self._db_path:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            self._init_db()

        if redis_url:
            try:
                import redis as redis_lib  # optional dependency

                self._redis = redis_lib.Redis.from_url(redis_url, decode_responses=True)
                self._redis.ping()
                logger.debug("Cache: Redis connected at %s", redis_url)
            except Exception as exc:
                logger.debug("Cache: Redis unavailable (%s) — using SQLite only", exc)
                self._redis = None

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS domain_cache (
                    domain      TEXT    PRIMARY KEY,
                    result_json TEXT    NOT NULL,
                    cached_at   REAL    NOT NULL,
                    expires_at  REAL    NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path or ":memory:")
        conn.row_factory = sqlite3.Row
        return conn

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self, domain: str) -> DomainResult | None:
        """Return a cached DomainResult for *domain*, or ``None`` on miss/expiry."""
        domain = domain.strip().lower()
        now = time.time()

        # 1. Try Redis first (fast path)
        if self._redis is not None:
            try:
                raw = self._redis.get(f"{_REDIS_PREFIX}{domain}")  # type: ignore[attr-defined]
                if raw:
                    result = DomainResult.model_validate_json(raw)
                    logger.debug("Cache: Redis hit for %s", domain)
                    return result
            except Exception as exc:
                logger.debug("Cache: Redis get failed (%s) — falling back to SQLite", exc)

        # 2. Try SQLite
        if self._db_path:
            try:
                with self._connect() as conn:
                    row = conn.execute(
                        "SELECT result_json, expires_at FROM domain_cache WHERE domain = ?",
                        (domain,),
                    ).fetchone()
                if row:
                    if row["expires_at"] > now:
                        result = DomainResult.model_validate_json(row["result_json"])
                        logger.debug("Cache: SQLite hit for %s", domain)
                        return result
                    # Expired — clean it up
                    self._delete_sqlite(domain)
                    logger.debug("Cache: expired entry deleted for %s", domain)
            except Exception as exc:
                logger.debug("Cache: SQLite get failed (%s)", exc)

        return None

    def set(self, domain: str, result: DomainResult) -> None:
        """Store *result* for *domain* in all available cache layers."""
        domain = domain.strip().lower()
        now = time.time()
        expires_at = now + self.ttl_seconds
        json_str = result.model_dump_json()

        # Redis
        if self._redis is not None:
            try:
                self._redis.setex(  # type: ignore[attr-defined]
                    f"{_REDIS_PREFIX}{domain}",
                    self.ttl_seconds,
                    json_str,
                )
                logger.debug("Cache: Redis stored %s (TTL %ds)", domain, self.ttl_seconds)
            except Exception as exc:
                logger.debug("Cache: Redis set failed (%s)", exc)

        # SQLite
        if self._db_path:
            try:
                with self._connect() as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO domain_cache
                            (domain, result_json, cached_at, expires_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (domain, json_str, now, expires_at),
                    )
                logger.debug("Cache: SQLite stored %s", domain)
            except Exception as exc:
                logger.debug("Cache: SQLite set failed (%s)", exc)

    def clear(self, domain: str | None = None) -> int:
        """Delete cached entries.

        Parameters
        ----------
        domain:
            If given, delete only that domain. Otherwise delete everything.

        Returns
        -------
        int
            Number of SQLite rows deleted.
        """
        deleted = 0

        # Redis
        if self._redis is not None:
            try:
                if domain:
                    self._redis.delete(f"{_REDIS_PREFIX}{domain}")  # type: ignore[attr-defined]
                else:
                    keys = self._redis.keys(f"{_REDIS_PREFIX}*")  # type: ignore[attr-defined]
                    if keys:
                        self._redis.delete(*keys)  # type: ignore[attr-defined]
            except Exception as exc:
                logger.debug("Cache: Redis clear failed (%s)", exc)

        # SQLite
        if self._db_path:
            try:
                with self._connect() as conn:
                    if domain:
                        cur = conn.execute(
                            "DELETE FROM domain_cache WHERE domain = ?",
                            (domain.strip().lower(),),
                        )
                    else:
                        cur = conn.execute("DELETE FROM domain_cache")
                    deleted = cur.rowcount
            except Exception as exc:
                logger.debug("Cache: SQLite clear failed (%s)", exc)

        return deleted

    def list_domains(self) -> list[tuple[str, datetime, bool]]:
        """Return all cached domains as (domain, cached_at, is_expired) tuples."""
        if not self._db_path:
            return []
        now = time.time()
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT domain, cached_at, expires_at FROM domain_cache ORDER BY cached_at DESC"
                ).fetchall()
            return [
                (
                    row["domain"],
                    datetime.fromtimestamp(row["cached_at"], tz=UTC),
                    row["expires_at"] <= now,
                )
                for row in rows
            ]
        except Exception as exc:
            logger.debug("Cache: SQLite list failed (%s)", exc)
            return []

    def stats(self) -> dict[str, int]:
        """Return basic cache statistics."""
        if not self._db_path:
            return {"total": 0, "valid": 0, "expired": 0}
        now = time.time()
        try:
            with self._connect() as conn:
                total = conn.execute("SELECT COUNT(*) FROM domain_cache").fetchone()[0]
                valid = conn.execute(
                    "SELECT COUNT(*) FROM domain_cache WHERE expires_at > ?", (now,)
                ).fetchone()[0]
            return {"total": total, "valid": valid, "expired": total - valid}
        except Exception:
            return {"total": 0, "valid": 0, "expired": 0}

    # ── Private helpers ───────────────────────────────────────────────────────

    def _delete_sqlite(self, domain: str) -> None:
        if not self._db_path:
            return
        with self._connect() as conn:
            conn.execute("DELETE FROM domain_cache WHERE domain = ?", (domain,))

    # ── Context manager support ───────────────────────────────────────────────

    def __enter__(self) -> CacheStore:
        return self

    def __exit__(self, *_: object) -> None:
        pass
