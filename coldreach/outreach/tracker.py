"""SQLite-backed outreach contact tracker.

Stores every contact the user has drafted, sent, or replied to.
Shares the same ~/.coldreach/cache.db as CacheStore (different table).
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime

_DEFAULT_DB = "~/.coldreach/cache.db"


@dataclass
class OutreachContact:
    email: str
    domain: str
    status: str  # new | draft | sent | replied | bounced
    subject: str | None
    body: str | None
    email_type: str | None
    created_at: datetime | None
    sent_at: datetime | None
    replied_at: datetime | None


class OutreachTracker:
    """CRUD layer for the outreach table in cache.db."""

    def __init__(self, db_path: str = _DEFAULT_DB) -> None:
        self._db_path = os.path.expanduser(db_path)
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._init_table()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_table(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS outreach (
                    email       TEXT PRIMARY KEY,
                    domain      TEXT NOT NULL,
                    status      TEXT NOT NULL DEFAULT 'new',
                    subject     TEXT,
                    body        TEXT,
                    email_type  TEXT,
                    created_at  TEXT,
                    sent_at     TEXT,
                    replied_at  TEXT
                )
                """
            )

    def upsert(self, email: str, domain: str, **kwargs: object) -> None:
        """Add or update a contact. Only provided kwargs are updated."""
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT email FROM outreach WHERE email = ?", (email.lower(),)
            ).fetchone()
            if existing:
                if kwargs:
                    sets = ", ".join(f"{k} = ?" for k in kwargs)
                    vals = list(kwargs.values()) + [email.lower()]
                    conn.execute(f"UPDATE outreach SET {sets} WHERE email = ?", vals)
            else:
                conn.execute(
                    """
                    INSERT INTO outreach
                        (email, domain, status, subject, body, email_type, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        email.lower(),
                        domain.lower(),
                        kwargs.get("status", "new"),
                        kwargs.get("subject"),
                        kwargs.get("body"),
                        kwargs.get("email_type"),
                        now,
                    ),
                )

    def save_draft(self, email: str, domain: str, subject: str, body: str, email_type: str) -> None:
        self.upsert(
            email,
            domain,
            status="draft",
            subject=subject,
            body=body,
            email_type=email_type,
        )

    def mark_sent(self, email: str) -> None:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE outreach SET status = 'sent', sent_at = ? WHERE email = ?",
                (now, email.lower()),
            )

    def mark_replied(self, email: str) -> None:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE outreach SET status = 'replied', replied_at = ? WHERE email = ?",
                (now, email.lower()),
            )

    def remove(self, email: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM outreach WHERE email = ?", (email.lower(),))

    def list_contacts(self) -> list[OutreachContact]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM outreach ORDER BY created_at DESC").fetchall()
        return [
            OutreachContact(
                email=r["email"],
                domain=r["domain"],
                status=r["status"],
                subject=r["subject"],
                body=r["body"],
                email_type=r["email_type"],
                created_at=_parse_dt(r["created_at"]),
                sent_at=_parse_dt(r["sent_at"]),
                replied_at=_parse_dt(r["replied_at"]),
            )
            for r in rows
        ]

    def stats(self) -> dict[str, int]:
        contacts = self.list_contacts()
        return {
            "total": len(contacts),
            "draft": sum(1 for c in contacts if c.status == "draft"),
            "sent": sum(1 for c in contacts if c.status == "sent"),
            "replied": sum(1 for c in contacts if c.status == "replied"),
        }


def _parse_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except ValueError:
        return None
