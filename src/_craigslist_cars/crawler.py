"""Craigslist cars crawler."""
from __future__ import annotations

from typing import List, Any
import time
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

from hyperSel import instance, parser

try:
    from utils.geo import get_all_cities_with_location
    from _craigslist_cars.jsonify import CraigslistCarsJsonify
    from _craigslist_cars.schema import SCHEMA
except ModuleNotFoundError:
    import sys
    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "src"))
    from utils.geo import get_all_cities_with_location
    from _craigslist_cars.jsonify import CraigslistCarsJsonify
    from _craigslist_cars.schema import SCHEMA

# ── ANSI colours ──────────────────────────────────────────────────────────────
R  = '\033[0m'
BD = '\033[1m'
GR = '\033[92m'
YL = '\033[93m'
BL = '\033[94m'
MG = '\033[95m'
CY = '\033[96m'
RD = '\033[91m'
WH = '\033[97m'

PUSH_INTERVAL = 600  # seconds between github pushes


def _banner(lines: list[str], color: str = CY) -> None:
    width = max(len(l) for l in lines) + 6
    border = color + BD + "█" * width + R
    print(f"\n{border}")
    for line in lines:
        pad = width - len(line) - 4
        print(f"{color}{BD}██  {WH}{line}{' ' * pad}{color}██{R}")
    print(f"{border}\n")


class CraigslistCarsCrawler:
    def __init__(self, name: str = "_craigslist_cars"):
        self.name        = name
        self._last_push  = time.time()
        self._total_rows = 0
        self._cities_done = 0

    # ── Git push ───────────────────────────────────────────────────────────────

    def _push_to_github(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            subprocess.run(["git", "add", "src/_craigslist_cars/database.sqlite"],
                           cwd=repo_root, check=True)
            subprocess.run(["git", "commit", "-m",
                            f"data: craigslist_cars auto-push {now} | rows={self._total_rows}"],
                           cwd=repo_root, check=True)
            subprocess.run(["git", "push"], cwd=repo_root, check=True)

        except subprocess.CalledProcessError as e:
            pass

        self._last_push = time.time()

    def _maybe_push(self) -> None:
        if time.time() - self._last_push >= PUSH_INTERVAL:
            self._push_to_github()

    # ── Main run ───────────────────────────────────────────────────────────────

    def run(self) -> None:
        browser = instance.Browser(
            driver_choice='selenium',
            headless=True,
            zoom_level=100
        )
        browser.init_browser()
        browser.go_to_site("https://foreandr.github.io/")

        cities = list(get_all_cities_with_location())
        total_cities = len(cities)

        for i, location in enumerate(cities, 1):
            city = location["city"]
            try:
                total_data = self._process_city(browser, city)
                jsonifier  = CraigslistCarsJsonify(self.name)
                clean_data = jsonifier.run_analysis(total_data, location=location, print_samples=False)
                inserted   = self._store_clean_data(clean_data)
                self._total_rows  += inserted
                self._cities_done += 1
            except Exception as e:
                pass

            pct = f"{i}/{total_cities}"
            db_total = self._db_total_rows()
            print(f"[{pct}] {self.name} | {city}, {location['state']}, {location['country']} | rows={db_total}")

            self._maybe_push()

        browser.close_browser()
        self._push_to_github()   # final push when done

        # done

    # ── Scraping ───────────────────────────────────────────────────────────────

    def _process_city(self, browser: Any, city: str) -> List[List[Any]]:
        city_without_spaces = city.replace(" ", "").lower()
        url = f"https://{city_without_spaces}.craigslist.org/search/cta#search=2~list~0"
        browser.go_to_site(url)
        return self._scroll_and_scrape(browser)

    def _scroll_and_scrape(self, browser: Any) -> List[List[Any]]:
        scroll_increment     = 2000
        time_between_scrolls = 0.1
        scroll_count         = 0
        last_y               = -1
        total_data           = []

        while True:
            scroll_count += 1
            current_y = browser.WEBDRIVER.execute_script("return window.pageYOffset;")

            if current_y == last_y:
                break

            last_y   = current_y
            target_y = current_y + scroll_increment
            browser.WEBDRIVER.execute_script(f"window.scrollTo(0, {target_y});")
            time.sleep(time_between_scrolls)

            soup       = browser.return_current_soup()
            all_data   = parser.main(soup)
            total_data.extend(all_data)
            total_data = [list(x) for x in set(tuple(x) for x in total_data)]

        return total_data

    # ── Storage ────────────────────────────────────────────────────────────────

    def _store_clean_data(self, clean_data: Any) -> int:
        db_path = self._db_path()
        conn    = sqlite3.connect(str(db_path))
        conn.execute(SCHEMA.create_table_sql())
        for stmt in SCHEMA.create_indexes_sql():
            conn.execute(stmt)

        cols = [r[1] for r in conn.execute("PRAGMA table_info(items);").fetchall()]
        if "crawled_at" not in cols:
            conn.execute("ALTER TABLE items ADD COLUMN crawled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP;")
        conn.execute(
            "UPDATE items SET crawled_at = CURRENT_TIMESTAMP "
            "WHERE crawled_at IS NULL OR crawled_at = '' OR LOWER(TRIM(crawled_at)) IN ('null', 'none');"
        )
        for col in ("city", "state", "country"):
            if col not in cols:
                conn.execute(f"ALTER TABLE items ADD COLUMN {col} TEXT;")

        rows = []
        if isinstance(clean_data, list):
            for item in clean_data:
                if not isinstance(item, dict):
                    continue
                crawled_at = item.get("crawled_at")
                if crawled_at is None or str(crawled_at).strip().lower() in {"", "null", "none"}:
                    item["crawled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                rows.append([item.get(k) for k in SCHEMA.field_names()])

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
        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute("SELECT COUNT(*) FROM items;").fetchone()
            return int(row[0]) if row else 0
        finally:
            conn.close()


def dedup_database(db_path: Path | None = None) -> int:
    """Delete duplicate rows that share the same URL, keeping the oldest (lowest rowid).

    Returns the number of rows deleted.
    """
    if db_path is None:
        db_path = Path(__file__).resolve().parents[2] / "src" / "_craigslist_cars" / "database.sqlite"

    if not db_path.exists():
        print(f"  {RD}DB not found:{R} {db_path}")
        return 0

    conn = sqlite3.connect(str(db_path))

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
        "🧹  DEDUP COMPLETE",
        f"  Before : {before:,}",
        f"  After  : {after:,}",
        f"  Deleted: {deleted:,} duplicate rows",
    ], color=GR)
    return deleted


if __name__ == "__main__":
    CraigslistCarsCrawler().run()
