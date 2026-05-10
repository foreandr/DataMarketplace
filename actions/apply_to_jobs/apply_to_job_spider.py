"""
actions/apply_to_jobs/apply_to_job_spider.py

Load JobSpider jobs from the DB matching SOFTWARE_KEYWORDS,
open each one in a visible browser, and wait for user input before moving on.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from selenium.webdriver.common.by import By
from hyperSel import instance

from keywords import SOFTWARE_KEYWORDS
from tracker_db import already_applied, is_failed, _init_db, DB, record_failure, record_application
import time

ROOT        = Path(__file__).resolve().parents[2]
DB_PATH     = ROOT / "src" / "_jobspider_jobs" / "database.sqlite"
RESUME_FILE = ROOT / "files" / "resume.txt"

RESUME_TEXT = RESUME_FILE.read_text(encoding="utf-8")

NAME_XPATH    = '/html/body/div[1]/div[4]/div[2]/form/table/tbody/tr[1]/td/input'
EMAIL_XPATH   = '/html/body/div[1]/div[4]/div[2]/form/table/tbody/tr[2]/td/input'
COVER_XPATH   = '/html/body/div[1]/div[4]/div[2]/form/table/tbody/tr[4]/td/textarea'
RESUME_XPATH  = '/html/body/div[1]/div[4]/div[2]/form/table/tbody/tr[5]/td'
PREVIEW_XPATH = '/html/body/div[1]/div[4]/div[2]/form/table/tbody/tr[6]/td/input'
CONFIRM_XPATH = '/html/body/div[1]/div[4]/div[2]/form/table/tbody/tr[3]/td/div/input[2]'


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
            if "juju" in (record.get("url") or "").lower():
                record_failure(record, reason="juju in url")
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

COVER_LETTER = (
    "I am a software engineer completing a B.Sc in Mathematics at Trent University, "
    "with an Advanced Diploma in Computer Programming and Analysis from Fanshawe College. "
    "I have production experience building backend infrastructure, internal tooling, "
    "automation systems, and data pipelines.\n\n"
    "Before working in software I represented Canada on the national volleyball team, competing "
    "internationally and earning multiple national championships. That period taught me how to "
    "perform under pressure, work within high-functioning teams, and maintain a standard of "
    "effort that most environments do not demand. I carry that into the way I approach "
    "technical work.\n\n"
    "Having reviewed your requirements, I am confident I have the skills you are looking for. "
    "My experience spans Python and JavaScript across the full stack, relational and "
    "non-relational databases, REST API development, frontend frameworks, interactive "
    "dashboards, and internal tooling. I have built and deployed production systems end to end. "
    "A portfolio of work that gives a good capture of my skillset across a range of domains is "
    "available at https://foreandr.github.io/index.html.\n\n"
    "I am motivated, I work hard, and I take quality seriously. I would be glad to contribute "
    "to your team and welcome the opportunity to speak further.\n\n"
    "Sincerely,\nAndre Foreman"
)


def apply(browser: Any, job: dict[str, Any]) -> None:
    url = job.get("url")
    if not url:
        raise ValueError("missing url")

    job_id_match = re.search(r'(\d+)(?:\.\w+)?$', url.rstrip('/'))
    if not job_id_match:
        raise ValueError("could not extract job ID from URL")

    job_id    = job_id_match.group(1)
    apply_url = f"https://www.jobspider.com/job/apply-for-job-2.asp?JobID={job_id}"

    browser.go_to_site(apply_url)

    browser.WEBDRIVER.find_element(By.XPATH, NAME_XPATH).send_keys("Andre Foreman")
    browser.WEBDRIVER.find_element(By.XPATH, EMAIL_XPATH).send_keys("foreandr@gmail.com")
    browser.WEBDRIVER.find_element(By.XPATH, COVER_XPATH).send_keys(COVER_LETTER)

    resume_td = browser.WEBDRIVER.find_element(By.XPATH, RESUME_XPATH)
    resume_td.find_element(By.TAG_NAME, "textarea").send_keys(RESUME_TEXT)

    # Step 1 — Preview
    try:
        browser.click_element(by_type="xpath", value=PREVIEW_XPATH)
    except Exception:
        browser.WEBDRIVER.find_element(By.XPATH, '//input[@value="Preview Application"]').click()

    # Step 2 — Confirm / Submit
    browser.click_element(by_type="xpath", value=CONFIRM_XPATH)
    time.sleep(5)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    jobs = _load_jobs(SOFTWARE_KEYWORDS)
    total = len(jobs)

    if not total:
        print("No jobs to apply to.")
    else:
        done = skipped = 0
        print(f"\n{'='*55}")
        print(f"  JobSpider — {total} jobs queued")
        print(f"{'='*55}\n")

        browser = instance.Browser(driver_choice="selenium", headless=False, zoom_level=100)
        browser.init_browser()

        try:
            for i, job in enumerate(jobs, 1):
                title   = job.get("title", "?")
                company = job.get("company", "?")
                print(f"  [{i}/{total}]  {title} @ {company}")

                try:
                    apply(browser, job)
                    record_application(job)
                    done += 1
                    print(f"  ✓ Applied       | done={done}  skipped={skipped}  remaining={total-i}\n")
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    record_failure(job, reason=str(exc))
                    skipped += 1
                    print(f"  ✗ Failed: {exc} | done={done}  skipped={skipped}  remaining={total-i}\n")
        except KeyboardInterrupt:
            print("\nStopped by user.")
        finally:
            browser.close_browser()

        print(f"{'='*55}")
        print(f"  Finished — applied={done}  failed={skipped}  total={total}")
        print(f"{'='*55}")
