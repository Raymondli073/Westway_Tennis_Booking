"""
Subscriber database — SQLite-backed store for email addresses.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "subscribers.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                email      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                token      TEXT    NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def _make_token(email: str) -> str:
    secret = os.getenv("SECRET_KEY", "westway-tennis-secret")
    return hashlib.sha256(f"{email}{secret}".encode()).hexdigest()[:32]


def subscribe(email: str) -> tuple[bool, str]:
    """
    Add email to subscribers.
    Returns (success, message).
    """
    token = _make_token(email)
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO subscribers (email, token) VALUES (?, ?)",
                (email.strip().lower(), token),
            )
            conn.commit()
        return True, "subscribed"
    except sqlite3.IntegrityError:
        return False, "already_subscribed"


def unsubscribe(token: str) -> tuple[bool, str]:
    """Remove subscriber by token. Returns (success, email_or_error)."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT email FROM subscribers WHERE token = ?", (token,)
        ).fetchone()
        if not row:
            return False, "not_found"
        conn.execute("DELETE FROM subscribers WHERE token = ?", (token,))
        conn.commit()
        return True, row["email"]


def get_all_emails() -> list[str]:
    with _connect() as conn:
        rows = conn.execute("SELECT email FROM subscribers").fetchall()
        return [r["email"] for r in rows]


def get_token(email: str) -> str:
    return _make_token(email)


def count() -> int:
    with _connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]
