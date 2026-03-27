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

from keywords import SOFTWARE_KEYWORDS, PLACEMENT_KEYWORDS

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
    remote_only: bool = True,
    cities: list[str] | None = None,
    province: str | None = None,
) -> list[dict[str, Any]]:
    """
    Query all job databases for one or more keywords (OR logic, case-insensitive
    substring match against title only).

    Parameters
    ----------
    keywords    : a single keyword string or a list of keywords.
    remote_only : when True, sources that have a work_mode column are filtered
                  to remote roles only. Sources without work_mode are unaffected.
                  Ignored when ``cities`` is provided.
    cities      : optional list of city names to filter by (OR logic, substring
                  match against the ``city`` column). When set, ``remote_only``
                  is ignored and results are restricted to these cities.
    province    : optional two-letter province code (e.g. "ON") applied alongside
                  ``cities`` to avoid cross-province false positives.

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
                # ── keyword clause ────────────────────────────────────────────
                # Title only — searching company causes false positives
                # (e.g. "Engineering Corp" pulls all their unrelated jobs).
                kw_clauses = " OR ".join(["LOWER(title) LIKE ?"] * len(keywords))
                params: list[Any] = [f"%{kw.lower()}%" for kw in keywords]

                # ── source-level always-on constraints ────────────────────────
                always_on = SOURCE_CONSTRAINTS.get(source_name, "")

                # ── introspect available columns ──────────────────────────────
                col_names = {
                    r[1] for r in conn.execute("PRAGMA table_info(items)").fetchall()
                }

                # ── location filter ───────────────────────────────────────────
                if cities:
                    # City-based search — remote_only does not apply.
                    if "city" not in col_names:
                        # Source has no city column — skip it entirely.
                        print(f"  [{source_name}] no city column, skipping for local search.")
                        continue
                    city_clauses = " OR ".join(["LOWER(city) LIKE ?"] * len(cities))
                    params += [f"%{c.lower()}%" for c in cities]
                    if province and "province" in col_names:
                        location_sql = f"AND ({city_clauses}) AND UPPER(province) = ?"
                        params.append(province.upper())
                    else:
                        location_sql = f"AND ({city_clauses})"
                else:
                    # Remote filter — only applied to sources that have work_mode.
                    location_sql = REMOTE_CONSTRAINTS.get(source_name, "") if remote_only else ""

                sql = (
                    f"SELECT * FROM items "
                    f"WHERE ({kw_clauses}) {always_on} {location_sql}"
                )
                rows = conn.execute(sql, params).fetchall()

                new, skip_applied, skip_failed, skip_boundary = 0, 0, 0, 0
                for row in rows:
                    record = dict(row)
                    record["source"] = source_name

                    # Word-boundary guard for placement searches (e.g. "intern"
                    # must not match "internal auditor").
                    if cities and not _placement_word_boundary_ok(
                        record.get("title", ""), keywords
                    ):
                        skip_boundary += 1
                        continue

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
                if skip_boundary:
                    label += f", {skip_boundary} false-positive (skipped)"
                print(f"  [{source_name}] {label}")
            except sqlite3.Error as e:
                print(f"  [{source_name}] query error: {e}")
            finally:
                conn.close()
    finally:
        tracker.close()

    return results


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

    # ── Search 1: remote software jobs ────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"SEARCH 1 — Remote software jobs ({len(SOFTWARE_KEYWORDS)} keywords)")
    print(f"{'='*60}")
    remote_jobs = get_jobs(SOFTWARE_KEYWORDS, remote_only=True)
    print(f"\nTotal: {len(remote_jobs)}  |  Showing first 20")
    print(f"{'-'*60}")
    for job in remote_jobs[:20]:
        print(json.dumps(job, indent=2, default=str))

    # ── Search 2: local internships / co-ops / summer roles in ON ─────────────
    print(f"\n{'='*60}")
    print(f"SEARCH 2 — ON internships / co-ops / summer roles ({len(PLACEMENT_KEYWORDS)} keywords)")
    print(f"Cities: {', '.join(GTA_CITIES)}")
    print(f"{'='*60}")
    local_jobs = get_jobs(
        PLACEMENT_KEYWORDS,
        remote_only=False,
        cities=GTA_CITIES,
        province="ON",
    )
    print(f"\nTotal: {len(local_jobs)}  |  Showing first 20")
    print(f"{'-'*60}")
    for job in local_jobs[:20]:
        print(json.dumps(job, indent=2, default=str))
