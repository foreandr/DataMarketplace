"""Crawler stub."""
from __future__ import annotations

from typing import Iterable, List, Any
import time
import json
import sqlite3
from datetime import datetime, timezone
from hyperSel import instance, parser, log

try:
    from crawlers.base import BaseCrawler, CrawlItem
    from utils.geo import get_all_cities
    from jsonify_logic.craigslist_cars import CraigslistCarsJsonify
    from schemas.craigslist_cars import SCHEMA
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "src"))
    from crawlers.base import BaseCrawler, CrawlItem
    from utils.geo import get_all_cities
    from jsonify_logic.craigslist_cars import CraigslistCarsJsonify
    from schemas.craigslist_cars import SCHEMA


class CraigslistCarsCrawler(BaseCrawler):
    def run(self) -> Iterable[CrawlItem]:
        browser = instance.Browser(
            driver_choice='selenium',
            headless=True,
            zoom_level=100
        )
        browser.init_browser()
        browser.go_to_site("https://foreandr.github.io/")
        
        for idx, city in enumerate(get_all_cities()):
            try:
                print(f"[{self.name}] city: {city}")
                total_data = self._process_city(browser, city)
                jsonifier = CraigslistCarsJsonify(self.name)
                clean_data = jsonifier.run_analysis(total_data, print_samples=True)
                self._store_clean_data(clean_data)
            except Exception as e:
                print("CITY FAILED FOR SOME REASON:", city)
                continue
            
        browser.close_browser()
        return self.stub_run()

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
            # print(f"Scroll {scroll_count}: Moved from {current_y}px to {target_y}px")
            
            time.sleep(time_between_scrolls)

            soup = browser.return_current_soup()
            all_data = parser.main(soup)
            
            total_data.extend(all_data)
            total_data = [list(x) for x in set(tuple(x) for x in total_data)]
            
            # print(f"Current unique items in total_data: {len(total_data)}")
            
            if scroll_count % 10 == 0:
                print(f"Periodic Check: Found {len(all_data)} items on last pass.")
            
        return total_data

    def _store_clean_data(self, clean_data: Any) -> None:
        # Store cleaned data in a crawler-specific SQLite DB.
        db_path = self._crawler_db_path()
        print(f"[{self.name}] DB path: {db_path}")
        conn = sqlite3.connect(str(db_path))
        conn.execute(SCHEMA.create_table_sql())
        print(f"[{self.name}] Ensured table: {SCHEMA.table}")
        for stmt in SCHEMA.create_indexes_sql():
            conn.execute(stmt)
        if SCHEMA.create_indexes_sql():
            print(f"[{self.name}] Ensured indexes: {len(SCHEMA.create_indexes_sql())}")

        rows = []
        if isinstance(clean_data, list):
            for item in clean_data:
                if not isinstance(item, dict):
                    continue
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

    def _crawler_db_path(self) -> "Path":
        from pathlib import Path

        root_dir = Path(__file__).resolve().parents[2]
        return root_dir / "data" / f"{self.name}.sqlite"

    def _utc_now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    CraigslistCarsCrawler(name="craigslist_cars").run()
