"""Craigslist real estate crawler."""
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
    from _craigslist_realestate.schema import SCHEMA
    from _craigslist_realestate.jsonify import CraigslistRealestateJsonify
except ModuleNotFoundError:
    import sys
    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "src"))
    from utils.geo import get_all_cities_with_location
    from _craigslist_realestate.schema import SCHEMA
    from _craigslist_realestate.jsonify import CraigslistRealestateJsonify

# ── ANSI colours ──────────────────────────────────────────────────────────────
R  = "\033[0m"
BD = "\033[1m"
GR = "\033[92m"
YL = "\033[93m"
BL = "\033[94m"
MG = "\033[95m"
CY = "\033[96m"
RD = "\033[91m"
WH = "\033[97m"

PUSH_INTERVAL = 600  # seconds between github pushes


def _banner(lines: list[str], color: str = CY) -> None:
    width = max(len(l) for l in lines) + 6
    border = color + BD + "=" * width + R
    print(f"\n{border}")
    for line in lines:
        pad = width - len(line) - 4
        print(f"{color}{BD}||  {WH}{line}{' ' * pad}{color}||{R}")
    print(f"{border}\n")


class CraigslistRealestateCrawler:
    def __init__(self, name: str = "_craigslist_realestate"):
        self.name         = name
        self._last_push   = time.time()
        self._total_rows  = 0
        self._cities_done = 0

    # ── Git push ──────────────────────────────────────────────────────────────

    def _push_to_github(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        _banner([
            "PUSHING TO GITHUB",
            f"  Time : {now}",
            f"  Rows : {self._total_rows:,}",
            f"  Cities done : {self._cities_done}",
        ], color=MG)

        db_rel = f"src/{self.name}/database.sqlite"
        try:
            subprocess.run(["git", "add", db_rel], cwd=repo_root, check=True)
            subprocess.run(
                ["git", "commit", "-m",
                 f"data: craigslist_realestate auto-push {now} | rows={self._total_rows}"],
                cwd=repo_root,
                check=True,
            )
            subprocess.run(["git", "push"], cwd=repo_root, check=True)

            _banner([
                "PUSH SUCCESSFUL",
                f"  {now}",
            ], color=GR)

        except subprocess.CalledProcessError as e:
            _banner([
                "PUSH FAILED",
                f"  {e}",
            ], color=RD)

        self._last_push = time.time()

    def _maybe_push(self) -> None:
        if time.time() - self._last_push >= PUSH_INTERVAL:
            self._push_to_github()

    # ── Main run ──────────────────────────────────────────────────────────────

    def run(self) -> None:
        _banner([
            "CRAIGSLIST REALESTATE CRAWLER STARTING",
            f"  Push interval : every {PUSH_INTERVAL // 60} minutes",
        ], color=CY)

        browser = instance.Browser(
            driver_choice="selenium",
            headless=True,
            zoom_level=100,
        )
        browser.init_browser()
        browser.go_to_site("https://foreandr.github.io/")

        cities = list(get_all_cities_with_location())
        total_cities = len(cities)

        for i, location in enumerate(cities, 1):
            city = location["city"]
            pct  = f"{i}/{total_cities}"
            print(f"{BL}{BD}[{pct}]{R} {YL}{city}{R} | {location['state']}, {location['country']}")

            try:
                total_data = self._process_city(browser, city)
                jsonifier  = CraigslistRealestateJsonify(self.name)
                clean_data = jsonifier.run_analysis(total_data, location=location, print_samples=False)
                n = len(clean_data or [])
                m = len(total_data or [])
                pct = (n / m * 100) if m else 0.0
                _banner([
                    "PARSE RATE",
                    f"  Kept  : {n}",
                    f"  Total : {m}",
                    f"  Rate  : {pct:.1f}%",
                ], color=CY)
                inserted   = self._store_clean_data(clean_data)
                self._total_rows  += inserted
                self._cities_done += 1
                print(f"  {GR}+{inserted} rows{R}  |  total {WH}{self._total_rows:,}{R}")
            except Exception as e:
                print(f"  {RD}CITY FAILED:{R} {city}")
                continue

            self._maybe_push()

        browser.close_browser()
        self._push_to_github()   # final push when done

        _banner([
            "CRAWL COMPLETE",
            f"  Total rows : {self._total_rows:,}",
            f"  Cities     : {self._cities_done}/{total_cities}",
        ], color=GR)

    # ── Scraping ──────────────────────────────────────────────────────────────

    def _process_city(self, browser: Any, city: str) -> List[List[Any]]:
        city_without_spaces = city.replace(" ", "").lower()
        searches = [
            ("apa", "list"),  # apartments / housing for rent
            ("rea", "list"),     # real estate for sale
            ("sha", "list"),     # shared housing
            ("roo", "list"),     # rooms / shared
        ]

        total_data: List[List[Any]] = []
        for code, mode in searches:
            url = f"https://{city_without_spaces}.craigslist.org/search/{code}#search=2~{mode}~0"
            browser.go_to_site(url)
            data = self._scroll_and_scrape(browser)
            total_data.extend(data)
            total_data = [list(x) for x in set(tuple(x) for x in total_data)]
        return total_data

    def _scroll_and_scrape(self, browser: Any) -> List[List[Any]]:
        scroll_increment     = 2000
        time_between_scrolls = 0.1
        scroll_count         = 0
        last_y               = -1
        total_data: List[List[Any]] = []

        while True:
            scroll_count += 1
            current_y = browser.WEBDRIVER.execute_script("return window.pageYOffset;")

            if current_y == last_y:
                print(f"  {CY}Bottom reached{R} at {current_y}px after {scroll_count} scrolls.")
                break

            last_y   = current_y
            target_y = current_y + scroll_increment
            browser.WEBDRIVER.execute_script(f"window.scrollTo(0, {target_y});")
            time.sleep(time_between_scrolls)

            soup       = browser.return_current_soup()
            all_data   = parser.main(soup)
            total_data.extend(all_data)
            total_data = [list(x) for x in set(tuple(x) for x in total_data)]

            if scroll_count % 10 == 0:
                print(f"  {YL}scroll {scroll_count}{R} | items so far: {len(total_data)}")
        return total_data

    # ── Storage ──────────────────────────────────────────────────────────────

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
        if "location" not in cols:
            conn.execute("ALTER TABLE items ADD COLUMN location TEXT;")
            if "neighborhood" in cols:
                conn.execute(
                    "UPDATE items SET location = neighborhood "
                    "WHERE location IS NULL OR TRIM(location) = '';"
                )

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


def dedup_database(db_path: Path | None = None) -> int:
    """Delete duplicate rows that share the same URL, keeping the oldest (lowest rowid).

    Returns the number of rows deleted.
    """
    if db_path is None:
        db_path = Path(__file__).resolve().parents[2] / "src" / "_craigslist_realestate" / "database.sqlite"

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
        "DEDUP COMPLETE",
        f"  Before : {before:,}",
        f"  After  : {after:,}",
        f"  Deleted: {deleted:,} duplicate rows",
    ], color=GR)
    return deleted


if __name__ == "__main__":
    CraigslistRealestateCrawler().run()
