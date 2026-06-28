"""SQLite persistence layer (repository pattern).

A repository hides the storage engine behind plain Python methods so the rest of
the service never sees SQL. SQLite is used for a zero-config, durable default;
because access is funnelled through this one class, swapping in PostgreSQL later
is a localized change.

Concurrency: FastAPI may serve requests from multiple threads. File-backed
databases open a short-lived connection per call; the special ``:memory:`` mode
(used by tests) keeps one shared, lock-guarded connection so the schema persists
across calls.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator

from . import shortener


class AliasTakenError(Exception):
    """Raised when a requested custom alias already exists."""


@dataclass(frozen=True)
class UrlRecord:
    id: int
    short_code: str
    long_url: str
    created_at: str


@dataclass(frozen=True)
class ClickRecord:
    short_code: str
    clicked_at: str
    referrer: str | None
    user_agent: str | None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Repository:
    def __init__(self, db_path: str = ":memory:") -> None:
        self._path = db_path
        self._lock = threading.Lock()
        self._shared: sqlite3.Connection | None = None
        if db_path == ":memory:":
            self._shared = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared.row_factory = sqlite3.Row
        self._init_db()

    def close(self) -> None:
        """Close the shared in-memory connection, if any.

        File-backed mode opens a connection per call and closes it immediately,
        so only the long-lived ``:memory:`` connection needs explicit cleanup.
        Idempotent: safe to call more than once.
        """

        if self._shared is not None:
            with self._lock:
                self._shared.close()
                self._shared = None

    def __enter__(self) -> "Repository":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        if self._shared is not None:
            with self._lock:
                try:
                    yield self._shared
                    self._shared.commit()
                except Exception:
                    self._shared.rollback()
                    raise
        else:
            conn = sqlite3.connect(self._path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    short_code TEXT UNIQUE,
                    long_url TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS clicks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    short_code TEXT NOT NULL,
                    clicked_at TEXT NOT NULL,
                    referrer TEXT,
                    user_agent TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_clicks_code ON clicks(short_code);
                """
            )

    # --- writes ---------------------------------------------------------

    def create_url(self, long_url: str, custom_code: str | None = None) -> UrlRecord:
        """Persist a new mapping and return the stored record.

        With ``custom_code`` the alias is used verbatim (and must be unique).
        Otherwise a Base62 code is derived from the row's primary key, which is
        unique by construction and needs no collision check.
        """

        created_at = _utc_now_iso()
        with self._connect() as conn:
            if custom_code is not None:
                try:
                    cur = conn.execute(
                        "INSERT INTO urls (short_code, long_url, created_at) "
                        "VALUES (?, ?, ?)",
                        (custom_code, long_url, created_at),
                    )
                except sqlite3.IntegrityError as exc:
                    raise AliasTakenError(custom_code) from exc
                return UrlRecord(cur.lastrowid, custom_code, long_url, created_at)

            cur = conn.execute(
                "INSERT INTO urls (long_url, created_at) VALUES (?, ?)",
                (long_url, created_at),
            )
            new_id = cur.lastrowid
            code = shortener.encode(new_id)
            conn.execute(
                "UPDATE urls SET short_code = ? WHERE id = ?", (code, new_id)
            )
            return UrlRecord(new_id, code, long_url, created_at)

    def record_click(
        self,
        short_code: str,
        referrer: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO clicks (short_code, clicked_at, referrer, user_agent) "
                "VALUES (?, ?, ?, ?)",
                (short_code, _utc_now_iso(), referrer, user_agent),
            )

    # --- reads ----------------------------------------------------------

    def get_by_code(self, short_code: str) -> UrlRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, short_code, long_url, created_at FROM urls "
                "WHERE short_code = ?",
                (short_code,),
            ).fetchone()
        return self._to_url_record(row) if row else None

    def list_urls(self, limit: int = 50, offset: int = 0) -> list[UrlRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, short_code, long_url, created_at FROM urls "
                "ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [self._to_url_record(row) for row in rows]

    def get_clicks(self, short_code: str) -> list[ClickRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT short_code, clicked_at, referrer, user_agent FROM clicks "
                "WHERE short_code = ? ORDER BY clicked_at",
                (short_code,),
            ).fetchall()
        return [
            ClickRecord(
                row["short_code"],
                row["clicked_at"],
                row["referrer"],
                row["user_agent"],
            )
            for row in rows
        ]

    def count_clicks(self, short_code: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM clicks WHERE short_code = ?",
                (short_code,),
            ).fetchone()
        return int(row["n"])

    @staticmethod
    def _to_url_record(row: sqlite3.Row) -> UrlRecord:
        return UrlRecord(
            id=row["id"],
            short_code=row["short_code"],
            long_url=row["long_url"],
            created_at=row["created_at"],
        )
