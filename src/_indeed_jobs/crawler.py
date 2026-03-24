"""Crawler for _indeed_jobs."""
from __future__ import annotations

import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, List

from hyperSel import instance, parser

try:
    from _indeed_jobs.jsonify import IndeedJobsJsonify
    from _indeed_jobs.schema import SCHEMA
except ModuleNotFoundError:
    import sys
    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "src"))
    from _indeed_jobs.jsonify import IndeedJobsJsonify
    from _indeed_jobs.schema import SCHEMA

# ── ANSI colours ──────────────────────────────────────────────────────────────
R  = '\033[0m'
BD = '\033[1m'
GR = '\033[92m'
YL = '\033[93m'
CY = '\033[96m'
RD = '\033[91m'
WH = '\033[97m'

PUSH_INTERVAL = 600  # seconds between GitHub pushes


def _banner(lines: list[str], color: str = CY) -> None:
    width  = max(len(l) for l in lines) + 6
    border = color + BD + "█" * width + R
    print(f"\n{border}")
    for line in lines:
        pad = width - len(line) - 4
        print(f"{color}{BD}██  {WH}{line}{' ' * pad}{color}██{R}")
    print(f"{border}\n")


class IndeedJobsCrawler:
    def __init__(self, name: str = "_indeed_jobs"):
        self.name        = name
        self._last_push  = time.time()
        self._total_rows = 0
        self._items_done = 0

    # ── Git push ───────────────────────────────────────────────────────────────
    def _push_to_github(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            subprocess.run(
                ["git", "add", f"src/{self.name}/database.sqlite"],
                cwd=repo_root, check=True,
            )
            subprocess.run(
                ["git", "commit", "-m",
                 f"data: {self.name} auto-push {now} | rows={self._total_rows}"],
                cwd=repo_root, check=True,
            )
            subprocess.run(["git", "push"], cwd=repo_root, check=True)
        except subprocess.CalledProcessError:
            pass
        self._last_push = time.time()

    def _maybe_push(self) -> None:
        if time.time() - self._last_push >= PUSH_INTERVAL:
            self._push_to_github()

    # ── Main run ───────────────────────────────────────────────────────────────
    def run(self) -> None:
        browser = instance.Browser(
            driver_choice="selenium",
            headless=True,
            zoom_level=100,
        )
        browser.init_browser()
        browser.go_to_site("https://foreandr.github.io/")

        # TODO: replace `items` with your actual iteration list
        #       e.g. cities, keywords, category URLs, page numbers, etc.
        items = []  # TODO
        total = len(items)

        input("TODO: populate `items` above — press ENTER when ready (Ctrl+C to abort) ")
        input("TODO: implement `_process_item()` and `jsonify.run_analysis()` — press ENTER when ready (Ctrl+C to abort) ")

        for i, item in enumerate(items, 1):
            try:
                raw_data = self._process_item(browser, item)
                for row in raw_data[:10]:
                    print(row)
                input("raw data printed above — press ENTER to jsonify (Ctrl+C to abort) ")

                jsonifier  = IndeedJobsJsonify(self.name)
                clean_data = jsonifier.run_analysis(raw_data, print_samples=False)
                for rec in clean_data[:10]:
                    print(rec)
                input("clean data printed above — press ENTER to continue (Ctrl+C to abort) ")

                continue  # TODO: remove this line when ready to store

                inserted = self._store_clean_data(clean_data)
                self._total_rows  += inserted
                self._items_done  += 1
            except Exception as e:
                print(f"{RD}[ERROR] item={item}: {e}{R}")

            db_total = self._db_total_rows()
            print(f"[{i}/{total}] {self.name} | item={item} | rows={db_total}")
            self._maybe_push()

        browser.close_browser()
        self._push_to_github()

    # ── Scraping — implement this ──────────────────────────────────────────────
    def _process_item(self, browser: Any, item: Any) -> List[List[Any]]:
        # TODO: navigate to the target URL and return raw scraped rows
        # Example:
        #   browser.go_to_site(f"https://example.com/search?q={item}")
        #   soup = browser.return_current_soup()
        #   return parser.main(soup)
        raise NotImplementedError("_process_item not implemented")

    # ── Storage ────────────────────────────────────────────────────────────────
    def _store_clean_data(self, clean_data: Any) -> int:
        db_path = self._db_path()
        conn    = sqlite3.connect(str(db_path), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(SCHEMA.create_table_sql())
        for stmt in SCHEMA.create_indexes_sql():
            conn.execute(stmt)
        existing_cols = [r[1] for r in conn.execute("PRAGMA table_info(items);").fetchall()]
        for field in SCHEMA.fields:
            if field.name not in existing_cols:
                default = f" DEFAULT {field.default_sql}" if field.default_sql else ""
                conn.execute(f"ALTER TABLE items ADD COLUMN {field.name} {field.type}{default};")
        rows = []
        if isinstance(clean_data, list):
            for record in clean_data:
                if not isinstance(record, dict):
                    continue
                if not record.get("crawled_at"):
                    record["crawled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                rows.append([record.get(k) for k in SCHEMA.field_names()])
        if rows:
            placeholders = ", ".join(["?"] * len(SCHEMA.field_names()))
            columns      = ", ".join(SCHEMA.field_names())
            conn.executemany(
                f"INSERT OR IGNORE INTO items ({columns}) VALUES ({placeholders});",
                rows,
            )
        conn.commit()
        conn.close()
        return len(rows)

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


# ── Dedup helper ───────────────────────────────────────────────────────────────
def dedup_database(db_path: Path | None = None) -> int:
    """Delete duplicate rows sharing the same URL, keeping the oldest (lowest rowid)."""
    if db_path is None:
        db_path = Path(__file__).resolve().parents[2] / "src" / "_indeed_jobs" / "database.sqlite"
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
    after   = conn.execute("SELECT COUNT(*) FROM items;").fetchone()[0]
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
    IndeedJobsCrawler().run()
