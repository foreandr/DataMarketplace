"""
actions/apply_to_jobs/main.py

Query all job databases for one or more keywords and return raw results,
skipping jobs already applied to or marked unapplicable.

Duplicate detection: (normalized title, normalized company) pair.
Reapply cooldown: REAPPLY_AFTER_DAYS — fair game again after this many days.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from hyperSel import log
from keywords import SOFTWARE_KEYWORDS, PLACEMENT_KEYWORDS

ROOT = Path(__file__).resolve().parents[2]
DB   = Path(__file__).resolve().parent / "database.sqlite"

REAPPLY_AFTER_DAYS = 365

_STATS = {"success": 0, "failed": 0, "total": 0}

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
    "charityvillage":   "AND LOWER(work_mode) LIKE '%remote%'",
    "goodwork":         "AND LOWER(work_mode) LIKE '%remote%'",
    # "workbc":           "AND LOWER(work_mode) LIKE '%remote%'",
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


# Keywords that are short enough to be substrings of unrelated words and need
# a proper word-boundary check rather than a bare LIKE match.
# e.g. "intern" → "internal auditor" is a false positive.
_WORD_BOUNDARY_KEYWORDS: dict[str, re.Pattern[str]] = {
    kw: re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
    for kw in ("intern",)
}


def _placement_word_boundary_ok(title: str, keywords: list[str]) -> bool:
    """
    For any keyword that requires a word-boundary check, confirm the title
    actually contains that keyword as a standalone word (not as a substring
    of a longer word like "internal" or "international").

    Returns True if:
      - none of the matched keywords are in _WORD_BOUNDARY_KEYWORDS, OR
      - at least one of them genuinely matches as a whole word.
    """
    title_lower = title.lower()
    sensitive = [kw for kw in keywords if kw.lower() in _WORD_BOUNDARY_KEYWORDS]
    if not sensitive:
        return True  # nothing to double-check

    # Check whether a sensitive keyword is the ONLY reason this row matched.
    non_sensitive = [kw for kw in keywords if kw.lower() not in _WORD_BOUNDARY_KEYWORDS]
    non_sensitive_hit = any(kw.lower() in title_lower for kw in non_sensitive)
    if non_sensitive_hit:
        return True  # a safe keyword already matches — row is legitimate

    # Only sensitive keywords matched — verify each has a true word boundary.
    return any(
        _WORD_BOUNDARY_KEYWORDS[kw.lower()].search(title)
        for kw in sensitive
        if kw.lower() in _WORD_BOUNDARY_KEYWORDS
    )


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
    # These parameters can remain in the signature to avoid breaking other code,
    # but we will ignore them to ensure the search is "General".
    remote_only: bool = False, 
    cities: list[str] | None = None,
    province: str | None = None,
) -> list[dict[str, Any]]:
    if isinstance(keywords, str):
        keywords = [keywords]

    results: list[dict[str, Any]] = []
    tracker = sqlite3.connect(DB)
    _init_db(tracker)

    try:
        for source_name, db_path in SOURCES.items():
            if not db_path.exists():
                continue

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                # ── Simplified Keyword Clause ─────────────────────────────────
                # This matches your keywords against the title.
                kw_clauses = " OR ".join(["LOWER(title) LIKE ?"] * len(keywords))
                params: list[Any] = [f"%{kw.lower()}%" for kw in keywords]

                # ── Remove all Location/Remote logic ──────────────────────────
                # We ignore 'cities', 'province', and 'remote_only' here
                # to make the search as broad as possible.
                sql = f"SELECT * FROM items WHERE ({kw_clauses})"
                
                rows = conn.execute(sql, params).fetchall()
                print(f"   [{source_name}] Found {len(rows)} raw matches for keywords.")

                new = 0
                for row in rows:
                    record = dict(row)
                    record["source"] = source_name
                    
                    # We still check the tracker so you don't double-apply
                    if not is_failed(tracker, record.get("url")) and \
                       not already_applied(tracker, record.get("title", ""), record.get("company", "")):
                        results.append(record)
                        new += 1
                
                print(f"   [{source_name}] {new} are new/not yet applied.")

            except sqlite3.Error as e:
                print(f"   [{source_name}] query error: {e}")
            finally:
                conn.close()
    finally:
        tracker.close()

    return results


# ── applier dispatch ──────────────────────────────────────────────────────────

import apply_to_canadian_jobbank
import apply_to_charityvillage
import apply_to_craigslist
import apply_to_goodwork
import apply_to_saskjobs
import apply_to_workbc

_APPLIERS = {
    "canadian_jobbank": apply_to_canadian_jobbank.apply,
    "charityvillage":   apply_to_charityvillage.apply,
    "craigslist":       apply_to_craigslist.apply,
    "goodwork":         apply_to_goodwork.apply,
    "saskjobs":         apply_to_saskjobs.apply,
    "workbc":           apply_to_workbc.apply,
}

def _apply_job(job: dict[str, Any]) -> None:
    """Apply to a single job with error handling; failures are recorded and skipped."""
    source = job.get("source")
    applier = _APPLIERS.get(source)
    if applier is None:
        print(f"  [skip] no applier for source: {source}")
        return

    url = job.get("url", "<no url>")
    title = job.get("title", "<no title>")
    _STATS["total"] += 1
    print(f"  [{source}] applying → {title}  ({url})")
    

    if "numerical" in title or "automobile" in title:
        record_application(job)
        return
        
    
    try:
        # Re-check tracker right before applying to avoid duplicates in the same run.
        tracker = sqlite3.connect(DB)
        _init_db(tracker)
        try:
            if is_failed(tracker, url):
                print(f"  [{source}] skip (marked failed): {title}")
                return
            if already_applied(tracker, title, job.get("company", "")):
                print(f"  [{source}] skip (already applied): {title}")
                return
        finally:
            tracker.close()

        applier(job)
        # input("Application sent. Press Enter to continue...")
        record_application(job)
        _STATS["success"] += 1
        print(f"  [{source}] recorded application for: {title}")
        print(f"  [stats] success={_STATS['success']} failed={_STATS['failed']} total={_STATS['total']}")
    except Exception as e:
        print(f"  [{source}] failed: {e}")
        record_failure(job, reason=str(e))
        _STATS["failed"] += 1
        print(f"  [stats] success={_STATS['success']} failed={_STATS['failed']} total={_STATS['total']}")


def run_applications(jobs: list[dict]) -> None:
    """Loop through jobs, apply to each via the matching source applier, and record the result."""
    for job in jobs:
        log.checkpoint()
        print("DOING JOB:", job)
        _apply_job(job)
        log.checkpoint()
        # input("-")


# ── main ──────────────────────────────────────────────────────────────────────

# Cities in the Toronto / Durham / Kawarthas corridor (ON).
GTA_CITIES = [
    "toronto",
    "peterborough",
    "oshawa",
    "durham",
    "whitby",
    "ajax",
    "pickering",
    "scarborough",
    "north york",
]

if __name__ == "__main__":
    import json

    # Combine both lists into one big search
    all_keywords = SOFTWARE_KEYWORDS + PLACEMENT_KEYWORDS

    # This will now search the entire WorkBC (and other) DBs for any of these titles
    all_jobs = get_jobs(all_keywords) 
    
    print(f"Total jobs found across all databases: {len(all_jobs)}")

    for job in all_jobs:
        # Proceed with applications
        run_applications([job])