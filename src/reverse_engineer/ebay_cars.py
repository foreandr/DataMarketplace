"""
eBay Cars & Trucks crawler — city-based coverage (US).

Pagination strategy (confirmed):
  - Type       : paginator (NOT infinite scroll)
  - URL        : https://www.ebay.com/sch/i.html?_sacat=6001&LH_ItemCondition=3
                 &_dcat=6001&_stpos={zip}&_sadis=50&_ipg=240&_pgn={n}
  - Items/page : up to 240 (with _ipg=240)
  - Stop       : empty page_data

Coverage strategy:
  - Iterate US cities from cities_us.py, take first zip of each city
  - 25-mile radius per city captures local listings
  - City + state appended to every row so location is known

Run: python src/reverse_engineer/ebay_cars.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "src"))

from db.cities_us import cities_us
from hyperSel import instance, parser

BASE = (
    "https://www.ebay.com/sch/i.html"
    "?_sacat=6001&LH_ItemCondition=3&_dcat=6001&_ipg=240"
)
MAX_PAGES_PER_CITY = 20
PAGE_WAIT          = 2.5


def page_url(zip_code: str, page: int) -> str:
    return f"{BASE}&_stpos={zip_code}&_sadis=50&_pgn={page}"


def run() -> None:
    browser = instance.Browser(driver_choice="selenium", headless=False, zoom_level=100)
    browser.init_browser()
    browser.go_to_site("https://foreandr.github.io/")

    all_raw_data: list[list[Any]] = []

    for city_entry in cities_us:
        city      = city_entry["city_ascii"]
        state     = city_entry["state_id"]
        first_zip = city_entry["zips"].split()[0]

        for page in range(1, MAX_PAGES_PER_CITY + 1):
            try:
                url = page_url(first_zip, page)
                print(f"\033[92m{url}\033[0m")
                browser.go_to_site(url)
                time.sleep(PAGE_WAIT)

                soup      = browser.return_current_soup()
                page_data = parser.main(soup)
                for i in page_data:
                    print(i)
                continue
                if not page_data:
                    break

                # append city + state to every row so location is known
                page_data = [row + [city, state, "US"] for row in page_data]

                all_raw_data.extend(page_data)

                print(f"[{city}, {state} p{page}] {len(page_data)} rows | total={len(all_raw_data)}")
                for row in page_data[:3]:
                    print(f"  {row}")

            except Exception as exc:
                print(f"[{city}, {state} p{page}] ERROR: {exc}")
                break

    browser.close_browser()
    print(f"\nDone. Total rows: {len(all_raw_data)}")


if __name__ == "__main__":
    run()
