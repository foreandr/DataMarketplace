"""Crawler for _canadian_jobbank."""
from __future__ import annotations

import re
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, List
from hyperSel import instance, parser

try:
    from _canadian_jobbank.jsonify import CanadianJobbankJsonify
    from _canadian_jobbank.schema import SCHEMA
except ModuleNotFoundError:
    import sys
    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "src"))
    from _canadian_jobbank.jsonify import CanadianJobbankJsonify
    from _canadian_jobbank.schema import SCHEMA

# ── ANSI colours ──────────────────────────────────────────────────────────────
R  = '\033[0m'
BD = '\033[1m'
GR = '\033[92m'
YL = '\033[93m'
CY = '\033[96m'
RD = '\033[91m'
WH = '\033[97m'

PUSH_INTERVAL = 600
BASE_URL      = "https://www.jobbank.gc.ca"
DEFAULT_PROVINCES = [
    "ON",
    "AB",
    "BC",
    "MB",
    "NB",
    "NS",
    "NT",
    "NU",
    "PE",
    "QC",
    "SK",
    "YT",
]

def _banner(lines: list[str], color: str = CY) -> None:
    width  = max(len(l) for l in lines) + 6
    border = color + BD + "█" * width + R
    print(f"\n{border}")
    for line in lines:
        pad = width - len(line) - 4
        print(f"{color}{BD}██  {WH}{line}{' ' * pad}{color}██{R}")
    print(f"{border}\n")


class CanadianJobbankCrawler:
    def __init__(self, name: str = "_canadian_jobbank"):
        self.name          = name
        self._last_push    = time.time()
        self._total_rows   = 0
        self._provinces_done = 0

    # ── Git push ───────────────────────────────────────────────────────────────

    def _push_to_github(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            subprocess.run(["git", "add", f"src/{self.name}/database.sqlite"],
                           cwd=repo_root, check=True)
            subprocess.run(["git", "commit", "-m",
                            f"data: {self.name} auto-push {now} | rows={self._total_rows}"],
                           cwd=repo_root, check=True)
            subprocess.run(["git", "push"], cwd=repo_root, check=True)
        except subprocess.CalledProcessError:
            pass
        self._last_push = time.time()

    def _maybe_push(self) -> None:
        if time.time() - self._last_push >= PUSH_INTERVAL:
            self._push_to_github()

    # ── Main run ───────────────────────────────────────────────────────────────

    def run(
        self,
        provinces: List[str] | None = None,
        keywords: List[str] | None = None,
    ) -> None:
        provinces = provinces or keywords or DEFAULT_PROVINCES
        total_provinces = len(provinces)

        browser = instance.Browser(
            driver_choice='selenium',
            headless=True,
            zoom_level=100,
        )
        browser.init_browser()

        for i, province in enumerate(provinces, 1):
            try:
                inserted = self._process_province(browser, province)
                self._total_rows   += inserted
                self._provinces_done += 1

            except Exception as e:
                print(f"{RD}[ERROR] province={province}: {e}{R}")

            pct      = f"{i}/{total_provinces}"
            db_total = self._db_total_rows()
            print(f"[{pct}] {self.name} | province={province} | db_rows={db_total}")
            self._maybe_push()

        browser.close_browser()
        self._push_to_github()

    # ── Scraping ───────────────────────────────────────────────────────────────

    def _process_province(self, browser: Any, province: str) -> int:
        url = f"{BASE_URL}/jobsearch/jobsearch?fage=30&sort=M&fprov={province}"
        browser.go_to_site(url)
        time.sleep(1.5)
        return self._paginate_and_scrape(browser, province)

    def _paginate_and_scrape(self, browser: Any, province: str) -> int:
        seen_rows: set[tuple[Any, ...]] = set()
        total_inserted = 0
        page = 0
        max_pages = 50  # switch provinces after 50 pages to keep the crawl moving
        page_wait = 2.0
        jsonifier = CanadianJobbankJsonify(self.name)

        while page < max_pages:
            soup = browser.return_current_soup()
            raw_rows = parser.main(soup)
            raw_count = len(raw_rows)
            page_index = page + 1

            new_rows: List[List[Any]] = []
            for row in raw_rows:
                row_key = tuple(row)
                if row_key in seen_rows:
                    continue
                seen_rows.add(row_key)
                new_rows.append(row)

            session_new_count = len(new_rows)
            session_dupe_count = max(raw_count - session_new_count, 0)
            clean_data = jsonifier.run_analysis(new_rows, print_samples=True)
            db_existing_count = self._count_existing_urls(clean_data)
            inserted_count = self._store_clean_data(clean_data)
            db_new_count = max(len(clean_data) - db_existing_count, 0)
            total_inserted += inserted_count
            skipped_summary = jsonifier.skipped_reason_counts()
            skipped_text = (
                ", ".join(f"{reason}={count}" for reason, count in skipped_summary.items())
                if skipped_summary else
                "none"
            )

            print(
                f"{CY}------- province={province} page={page_index} -------{R}"
            )
            print(
                f"{CY}[PAGE {page_index}] scraped={raw_count} | "
                f"session_new={session_new_count} | session_dupes={session_dupe_count} | "
                f"seen_total={len(seen_rows)}{R}"
            )
            print(
                f"{CY}[PAGE {page_index}] clean_rows={len(clean_data)} | "
                f"already_in_db={db_existing_count} | db_new={db_new_count} | "
                f"inserted_now={inserted_count}{R}"
            )
            print(
                f"{CY}[PAGE {page_index}] skipped={jsonifier.skipped_count} | "
                f"skip_reasons={skipped_text}{R}"
            )

            if page > 0 and session_new_count == 0:
                print(
                    f"{YL}[PAGE {page_index}] stopping: no new unique jobs detected after pagination.{R}"
                )
                break

            page += 1

            button_xpath = '//*[@id="moreresultbutton"]'
            try:
                browser.scroll_to_bottom()
                time.sleep(0.5)
                browser.click_element("xpath", button_xpath, 3)
                print(
                    f"{GR}[PAGE {page}] clicked 'show more results' | waiting {page_wait:.1f}s for new jobs to load...{R}"
                )
                time.sleep(page_wait)
            except Exception as e:
                print(
                    f"{YL}[PAGE {page}] stopping: could not click 'show more results' ({e}).{R}"
                )
                break

        return total_inserted

    # ── Storage ────────────────────────────────────────────────────────────────

    def _store_clean_data(self, clean_data: Any) -> int:
        db_path = self._db_path()
        conn    = sqlite3.connect(str(db_path), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(SCHEMA.create_table_sql())
        for stmt in SCHEMA.create_indexes_sql():
            conn.execute(stmt)

        # Ensure all schema columns exist (safe for re-runs against old DB)
        existing_cols = [r[1] for r in conn.execute("PRAGMA table_info(items);").fetchall()]
        for field in SCHEMA.fields:
            if field.name not in existing_cols:
                default = f" DEFAULT {field.default_sql}" if field.default_sql else ""
                conn.execute(f"ALTER TABLE items ADD COLUMN {field.name} {field.type}{default};")

        rows = []
        if isinstance(clean_data, list):
            for item in clean_data:
                if not isinstance(item, dict):
                    continue
                if not item.get("crawled_at"):
                    item["crawled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                rows.append([item.get(k) for k in SCHEMA.field_names()])

        if rows:
            placeholders = ", ".join(["?"] * len(SCHEMA.field_names()))
            columns      = ", ".join(SCHEMA.field_names())
            before_changes = conn.total_changes
            conn.executemany(
                f"INSERT OR IGNORE INTO items ({columns}) VALUES ({placeholders});",
                rows,
            )
            inserted = conn.total_changes - before_changes
        else:
            inserted = 0
        conn.commit()
        conn.close()
        return inserted

    def _count_existing_urls(self, clean_data: Any) -> int:
        if not isinstance(clean_data, list):
            return 0

        urls = [
            item.get("url")
            for item in clean_data
            if isinstance(item, dict) and item.get("url")
        ]
        if not urls:
            return 0

        db_path = self._db_path()
        if not db_path.exists():
            return 0

        conn = sqlite3.connect(str(db_path), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")
        try:
            total_existing = 0
            chunk_size = 200
            for i in range(0, len(urls), chunk_size):
                chunk = urls[i:i + chunk_size]
                placeholders = ", ".join(["?"] * len(chunk))
                row = conn.execute(
                    f"SELECT COUNT(*) FROM items WHERE url IN ({placeholders});",
                    chunk,
                ).fetchone()
                total_existing += int(row[0]) if row else 0
            return total_existing
        finally:
            conn.close()

    def _db_path(self) -> Path:
        return Path(__file__).resolve().parents[2] / "src" / self.name / "database.sqlite"

    def _db_total_rows(self) -> int:
        db_path = self._db_path()
        if not db_path.exists():
            return 0
        conn = sqlite3.connect(str(db_path), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")
        try:
            row = conn.execute("SELECT COUNT(*) FROM items;").fetchone()
            return int(row[0]) if row else 0
        finally:
            conn.close()


# ── dedup helper ───────────────────────────────────────────────────────────────

def dedup_database(db_path: Path | None = None) -> int:
    if db_path is None:
        db_path = Path(__file__).resolve().parents[2] / "src" / "_canadian_jobbank" / "database.sqlite"
    if not db_path.exists():
        print(f"  {RD}DB not found:{R} {db_path}")
        return 0
    conn   = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    before = conn.execute("SELECT COUNT(*) FROM items;").fetchone()[0]
    conn.execute("""
        DELETE FROM items
        WHERE rowid NOT IN (
            SELECT MIN(rowid) FROM items GROUP BY url
        );
    """)
    conn.commit()
    after = conn.execute("SELECT COUNT(*) FROM items;").fetchone()[0]
    conn.close()
    deleted = before - after
    _banner([
        "DEDUP COMPLETE",
        f"  Before : {before:,}",
        f"  After  : {after:,}",
        f"  Deleted: {deleted:,} duplicate rows",
    ], color=GR)
    return deleted


if __name__ == "__main__":
    CanadianJobbankCrawler().run()
