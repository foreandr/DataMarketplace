"""
actions/apply_to_jobs/main.py

Query all job databases for one or more keywords and return raw results,
skipping jobs already applied to or marked unapplicable.

Duplicate detection: (normalized title, normalized company) pair.
Reapply cooldown: REAPPLY_AFTER_DAYS — fair game again after this many days.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from keywords import SOFTWARE_KEYWORDS

ROOT = Path(__file__).resolve().parents[2]
DB   = Path(__file__).resolve().parent / "database.sqlite"

REAPPLY_AFTER_DAYS = 365

SOURCES = {
    "canadian_jobbank": ROOT / "src/_canadian_jobbank/database.sqlite",
    "charityvillage":   ROOT / "src/_charityvillage_jobs/database.sqlite",
    "craigslist":       ROOT / "src/_craigslist_jobs/database.sqlite",
    "goodwork":         ROOT / "src/_goodwork_jobs/database.sqlite",
    "indeed":           ROOT / "src/_indeed_jobs/database.sqlite",
    "saskjobs":         ROOT / "src/_saskjobs/database.sqlite",
    "workbc":           ROOT / "src/_workbc_jobs/database.sqlite",
}

# Always-on constraints per source (applied regardless of other filters).
SOURCE_CONSTRAINTS = {
    "charityvillage": "AND is_quick_apply = 1",
}

# Remote work_mode constraints per source, applied when remote_only=True.
# Values taken from the actual data in each DB.
REMOTE_CONSTRAINTS = {
    "canadian_jobbank": "AND LOWER(work_mode) LIKE '%remote%'",
    "charityvillage":   "AND LOWER(work_mode) LIKE '%remote%'",
    "goodwork":         "AND LOWER(work_mode) LIKE '%remote%'",
    "workbc":           "AND LOWER(work_mode) LIKE '%remote%'",
    # craigslist, saskjobs, indeed have no work_mode column — no constraint added
}


# ── tracker DB ────────────────────────────────────────────────────────────────

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
    # Tracks URLs that couldn't be applied to (bad link, no email, etc.)
    # Keyed by URL so the same company can repost a working link later.
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
    """
    Call this when an application attempt fails (bad link, no contact info, etc.).
    That URL will be permanently skipped in future get_jobs() calls.
    """
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
    """
    Call this after successfully applying to a job. Logs the application so
    the same (title, company) is skipped for the next REAPPLY_AFTER_DAYS days.
    """
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


# ── job fetcher ───────────────────────────────────────────────────────────────

def get_jobs(
    keywords: str | list[str],
    remote_only: bool = True,
) -> list[dict[str, Any]]:
    """
    Query all job databases for one or more keywords (OR logic, case-insensitive
    substring match against title and company).

    Parameters
    ----------
    keywords    : a single keyword string or a list of keywords.
    remote_only : when True, sources that have a work_mode column are filtered
                  to remote roles only. Sources without work_mode are unaffected.

    Jobs already applied to (within cooldown) or marked unapplicable are skipped.
    Each returned dict contains all original columns from its source table plus a
    ``source`` key — fields are NOT normalized so source-specific filters remain.
    """
    if isinstance(keywords, str):
        keywords = [keywords]

    results: list[dict[str, Any]] = []
    tracker = sqlite3.connect(DB)
    _init_db(tracker)

    try:
        for source_name, db_path in SOURCES.items():
            if not db_path.exists():
                print(f"[{source_name}] database not found, skipping.")
                continue

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                # Build keyword OR clause dynamically — title only, LOWER on both sides.
                # Searching company name causes false positives (e.g. "Engineering Corp"
                # pulls in all their unrelated jobs).
                kw_clauses = " OR ".join(
                    ["LOWER(title) LIKE ?"] * len(keywords)
                )
                params: list[Any] = []
                for kw in keywords:
                    params.append(f"%{kw.lower()}%")

                always_on  = SOURCE_CONSTRAINTS.get(source_name, "")
                remote_sql = REMOTE_CONSTRAINTS.get(source_name, "") if remote_only else ""

                sql = f"SELECT * FROM items WHERE ({kw_clauses}) {always_on} {remote_sql}"
                rows = conn.execute(sql, params).fetchall()

                new, skip_applied, skip_failed = 0, 0, 0
                for row in rows:
                    record = dict(row)
                    record["source"] = source_name
                    if is_failed(tracker, record.get("url")):
                        skip_failed += 1
                    elif already_applied(tracker, record.get("title", ""), record.get("company", "")):
                        skip_applied += 1
                    else:
                        results.append(record)
                        new += 1

                label = f"{new} new"
                if skip_applied:
                    label += f", {skip_applied} already applied (skipped)"
                if skip_failed:
                    label += f", {skip_failed} unapplicable (skipped)"
                print(f"[{source_name}] {label}")
            except sqlite3.Error as e:
                print(f"[{source_name}] query error: {e}")
            finally:
                conn.close()
    finally:
        tracker.close()

    return results


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    keywords = SOFTWARE_KEYWORDS
    print(f"\nSearching all databases for {len(keywords)} keywords (remote only)\n{'='*50}")
    jobs = get_jobs(keywords, remote_only=True)
    print(f"\nTotal results: {len(jobs)}")
    print(f"Showing first 20:\n{'='*50}")
    for job in jobs[:20]:
        print(json.dumps(job, indent=2, default=str))
