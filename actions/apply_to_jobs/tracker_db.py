"""
actions/apply_to_jobs/tracker_db.py

Shared tracker-DB utilities used by main.py and the individual apply_to_*
modules.  Extracted here to break the circular import that arises when
apply_to_job_spider.py (and others) do `from main import ...` while main.py
is still being imported.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

DB = Path(__file__).resolve().parent / "database.sqlite"

REAPPLY_AFTER_DAYS = 365


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applied_jobs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            title      TEXT NOT NULL,
            company    TEXT NOT NULL,
            source     TEXT,
            url        TEXT,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_applied_title_company
        ON applied_jobs (title, company)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS failed_jobs (
            url       TEXT PRIMARY KEY,
            title     TEXT,
            company   TEXT,
            source    TEXT,
            reason    TEXT,
            failed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def _normalize(s: str | None) -> str:
    return (s or "").strip().lower()


def already_applied(conn: sqlite3.Connection, title: str, company: str) -> bool:
    """Return True if we applied to this (title, company) within the cooldown window."""
    cutoff = (datetime.now() - timedelta(days=REAPPLY_AFTER_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    row = conn.execute(
        """
        SELECT MAX(applied_at) FROM applied_jobs
        WHERE title = ? AND company = ? AND applied_at >= ?
        """,
        (_normalize(title), _normalize(company), cutoff),
    ).fetchone()
    return row[0] is not None


def is_failed(conn: sqlite3.Connection, url: str | None) -> bool:
    """Return True if this URL has been marked as unapplicable."""
    if not url:
        return False
    row = conn.execute(
        "SELECT 1 FROM failed_jobs WHERE url = ?", (url,)
    ).fetchone()
    return row is not None


def record_failure(job: dict[str, Any], reason: str = "") -> None:
    conn = sqlite3.connect(DB)
    _init_db(conn)
    conn.execute(
        """
        INSERT OR IGNORE INTO failed_jobs (url, title, company, source, reason, failed_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            job.get("url"),
            _normalize(job.get("title")),
            _normalize(job.get("company")),
            job.get("source"),
            reason,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()


def record_application(job: dict[str, Any]) -> None:
    conn = sqlite3.connect(DB)
    _init_db(conn)
    conn.execute(
        """
        INSERT INTO applied_jobs (title, company, source, url, applied_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            _normalize(job.get("title")),
            _normalize(job.get("company")),
            job.get("source"),
            job.get("url"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()
