"""Craigslist cars crawler."""
from __future__ import annotations

from typing import List, Any
import time
import sqlite3
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


class CraigslistCarsCrawler:
    def __init__(self, name: str = "_craigslist_cars"):
        self.name = name

    def run(self) -> None:
        browser = instance.Browser(
            driver_choice='selenium',
            headless=True,
            zoom_level=100
        )
        browser.init_browser()
        browser.go_to_site("https://foreandr.github.io/")

        for location in get_all_cities_with_location():
            city = location["city"]
            try:
                print(f"[{self.name}] city: {city} | {location['state']}, {location['country']}")
                total_data = self._process_city(browser, city)
                jsonifier = CraigslistCarsJsonify(self.name)
                clean_data = jsonifier.run_analysis(total_data, location=location, print_samples=False)
                self._store_clean_data(clean_data)
            except Exception as e:
                print("CITY FAILED FOR SOME REASON:", city)
                continue

        browser.close_browser()

    def _process_city(self, browser: Any, city: str) -> List[List[Any]]:
        city_without_spaces = city.replace(" ", "").lower()
        url = f"https://{city_without_spaces}.craigslist.org/search/cta#search=2~list~0"
        print("url:", url)
        browser.go_to_site(url)
        return self._scroll_and_scrape(browser)

    def _scroll_and_scrape(self, browser: Any) -> List[List[Any]]:
        scroll_increment = 2000
        time_between_scrolls = 0.1
        scroll_count = 0
        last_y = -1
        total_data = []

        while True:
            scroll_count += 1
            current_y = browser.WEBDRIVER.execute_script("return window.pageYOffset;")

            if current_y == last_y:
                print(f"Finished. Bottom reached at {current_y}px after {scroll_count} increments.")
                break

            last_y = current_y
            target_y = current_y + scroll_increment
            browser.WEBDRIVER.execute_script(f"window.scrollTo(0, {target_y});")
            time.sleep(time_between_scrolls)

            soup = browser.return_current_soup()
            all_data = parser.main(soup)
            total_data.extend(all_data)
            total_data = [list(x) for x in set(tuple(x) for x in total_data)]

            if scroll_count % 10 == 0:
                print(f"Periodic Check: Found {len(all_data)} items on last pass.")

        return total_data

    def _store_clean_data(self, clean_data: Any) -> None:
        db_path = self._db_path()
        print(f"[{self.name}] DB path: {db_path}")
        conn = sqlite3.connect(str(db_path))
        conn.execute(SCHEMA.create_table_sql())
        for stmt in SCHEMA.create_indexes_sql():
            conn.execute(stmt)

        cols = [r[1] for r in conn.execute("PRAGMA table_info(items);").fetchall()]
        if "crawled_at" not in cols:
            conn.execute("ALTER TABLE items ADD COLUMN crawled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP;")
        # ensure all existing/legacy rows have a valid crawled_at value
        conn.execute(
            "UPDATE items SET crawled_at = CURRENT_TIMESTAMP "
            "WHERE crawled_at IS NULL OR crawled_at = '' OR LOWER(TRIM(crawled_at)) IN ('null', 'none');"
        )
        if "city" not in cols:
            conn.execute("ALTER TABLE items ADD COLUMN city TEXT;")
        if "state" not in cols:
            conn.execute("ALTER TABLE items ADD COLUMN state TEXT;")
        if "country" not in cols:
            conn.execute("ALTER TABLE items ADD COLUMN country TEXT;")

        rows = []
        if isinstance(clean_data, list):
            for item in clean_data:
                if not isinstance(item, dict):
                    continue
                crawled_at = item.get("crawled_at")
                if crawled_at is None or str(crawled_at).strip().lower() in {"", "null", "none"}:
                    item["crawled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                row = [item.get(k) for k in SCHEMA.field_names()]
                rows.append(row)
        if rows:
            placeholders = ", ".join(["?"] * len(SCHEMA.field_names()))
            columns = ", ".join(SCHEMA.field_names())
            conn.executemany(
                f"INSERT OR REPLACE INTO items ({columns}) VALUES ({placeholders});",
                rows,
            )
            print(f"[{self.name}] Inserted rows: {len(rows)}")
        else:
            print(f"[{self.name}] Inserted rows: 0")
        conn.commit()
        conn.close()

    def _db_path(self) -> Path:
        return Path(__file__).resolve().parents[2] / "src" / self.name / "database.sqlite"


if __name__ == "__main__":
    CraigslistCarsCrawler().run()
