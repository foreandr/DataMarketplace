"""
actions/apply_to_jobs/apply_to_job_spider.py

Load JobSpider jobs from the DB matching SOFTWARE_KEYWORDS,
open each one in a visible browser, and wait for user input before moving on.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from hyperSel import instance

from some_keywords import SOFTWARE_KEYWORDS
from main import already_applied, is_failed, _init_db, DB

ROOT    = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "src" / "_jobspider_jobs" / "database.sqlite"


# ── DB loader ─────────────────────────────────────────────────────────────────

def _load_jobs(keywords: list[str]) -> list[dict[str, Any]]:
    """Query the jobspider DB for rows whose title matches any keyword."""
    if not DB_PATH.exists():
        print(f"[ERROR] DB not found: {DB_PATH}")
        return []

    tracker = sqlite3.connect(DB)
    _init_db(tracker)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        kw_clauses = " OR ".join(["LOWER(title) LIKE ?"] * len(keywords))
        params     = [f"%{kw.lower()}%" for kw in keywords]
        sql        = f"SELECT * FROM items WHERE ({kw_clauses})"
        rows       = conn.execute(sql, params).fetchall()
        print(f"[jobspider] {len(rows)} raw matches for {len(keywords)} keywords")

        jobs = []
        for row in rows:
            record = dict(row)
            record["source"] = "jobspider"
            if is_failed(tracker, record.get("url")):
                continue
            if already_applied(tracker, record.get("title", ""), record.get("company", "")):
                continue
            jobs.append(record)

        print(f"[jobspider] {len(jobs)} jobs after skipping applied/failed")
        return jobs

    except sqlite3.Error as exc:
        print(f"[jobspider] DB error: {exc}")
        return []
    finally:
        conn.close()
        tracker.close()


# ── Browser opener ────────────────────────────────────────────────────────────

def apply(job: dict[str, Any]) -> None:
    """Open a single JobSpider listing in a visible browser."""
    url = job.get("url")
    if not url:
        raise ValueError(f"jobspider job missing url: {job}")

    browser = instance.Browser(
        driver_choice="selenium",
        headless=False,
        zoom_level=100,
    )
    browser.init_browser()
    browser.go_to_site(url)

    try:
        print(f"\n  Title   : {job.get('title')}")
        print(f"  Company : {job.get('company')}")
        print(f"  Location: {job.get('location_raw')}")
        print(f"  Category: {job.get('category')}")
        print(f"  Posted  : {job.get('posted_date')}")
        print(f"  URL     : {url}")
        input("\n  Press ENTER for next job  (Ctrl+C to stop) ")
    finally:
        browser.close_browser()


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    jobs = _load_jobs(SOFTWARE_KEYWORDS)

    if not jobs:
        print("No jobs to show.")
    else:
        print(f"\nOpening {len(jobs)} jobs one at a time...\n")
        for i, job in enumerate(jobs, 1):
            print(f"─── [{i}/{len(jobs)}] ───────────────────────────────────────────")
            try:
                apply(job)
            except KeyboardInterrupt:
                print("\nStopped.")
                break
            except Exception as exc:
                print(f"  [skip] {exc}")
