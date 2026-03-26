"""
Reverse-engineer proof-of-concept: Craigslist Cars
Pagination strategy: city-based subdomains + infinite scroll

For each US/Canada city:
  - Navigate to https://{city}.craigslist.org/search/cta
  - Scroll the page in 2000px increments until no more movement
  - After each scroll, grab soup and call parser.main(soup)
  - Collect + dedup raw rows

No DB, no jsonify, no git push — just proves pagination + parser work.
Run: python src/reverse_engineer/craigslist_cars.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, List

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "src"))

from hyperSel import instance, parser
from utils.geo import get_all_cities_with_location


def scroll_and_scrape(browser: Any) -> List[List[Any]]:
    """Scroll the current page to bottom, calling parser after each step."""
    scroll_increment     = 2000
    time_between_scrolls = 0.1
    last_y               = -1
    total_data: List[List[Any]] = []

    while True:
        current_y = browser.WEBDRIVER.execute_script("return window.pageYOffset;")
        if current_y == last_y:
            break

        last_y   = current_y
        target_y = current_y + scroll_increment
        browser.WEBDRIVER.execute_script(f"window.scrollTo(0, {target_y});")
        time.sleep(time_between_scrolls)

        soup      = browser.return_current_soup()
        page_data = parser.main(soup)
        total_data.extend(page_data)
        total_data = [list(x) for x in set(tuple(x) for x in total_data)]

    return total_data


def run() -> None:
    browser = instance.Browser(driver_choice="selenium", headless=True, zoom_level=100)
    browser.init_browser()
    browser.go_to_site("https://foreandr.github.io/")

    cities     = list(get_all_cities_with_location())
    grand_total: List[List[Any]] = []

    for i, location in enumerate(cities, 1):
        city                = location["city"]
        city_no_spaces      = city.replace(" ", "").lower()
        url = f"https://{city_no_spaces}.craigslist.org/search/cta#search=2~list~0"

        try:
            browser.go_to_site(url)
            city_data = scroll_and_scrape(browser)

            grand_total.extend(city_data)
            grand_total = [list(x) for x in set(tuple(x) for x in grand_total)]

            print(
                f"[{i}/{len(cities)}] {city}, {location['state']}, {location['country']}"
                f" | this_city={len(city_data)} | total={len(grand_total)}"
            )
        except Exception as exc:
            print(f"[{i}/{len(cities)}] {city} SKIPPED — {exc}")

    browser.close_browser()
    print(f"\nDone. Grand total raw rows: {len(grand_total)}")


if __name__ == "__main__":
    run()
