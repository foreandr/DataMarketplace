"""
actions/apply_to_jobs/main.py

Query all job databases for one or more keywords and return raw results,
skipping jobs already applied to or marked unapplicable.

Duplicate detection: (normalized title, normalized company) pair.
Reapply cooldown: REAPPLY_AFTER_DAYS — fair game again after this many days.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
from hyperSel import log
from keywords import SOFTWARE_KEYWORDS, PLACEMENT_KEYWORDS

from tracker_db import DB, _init_db, already_applied, is_failed, record_failure, record_application

ROOT = Path(__file__).resolve().parents[2]

_STATS = {"success": 0, "failed": 0, "total": 0}

SOURCES = {
    "canadian_jobbank": ROOT / "src/_canadian_jobbank/database.sqlite",
    # "charityvillage":   ROOT / "src/_charityvillage_jobs/database.sqlite",
    "craigslist":       ROOT / "src/_craigslist_jobs/database.sqlite",
    # "goodwork":         ROOT / "src/_goodwork_jobs/database.sqlite",
    # "indeed":           ROOT / "src/_indeed_jobs/database.sqlite",
    "jobspider":        ROOT / "src/_jobspider_jobs/database.sqlite",
    # "saskjobs":         ROOT / "src/_saskjobs/database.sqlite",
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
import apply_to_job_spider
import apply_to_saskjobs
import apply_to_workbc

_APPLIERS = {
    "canadian_jobbank": apply_to_canadian_jobbank.apply,
    "charityvillage":   apply_to_charityvillage.apply,
    "craigslist":       apply_to_craigslist.apply,
    "goodwork":         apply_to_goodwork.apply,
    "jobspider":        apply_to_job_spider.apply,
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