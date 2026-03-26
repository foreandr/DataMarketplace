"""
Reverse-engineer proof-of-concept: Kijiji Cars
Pagination strategy: single national URL + page-number in URL path

Kijiji is a single Canadian site (no city subdomains).
URL structure:
  Page 1 : https://www.kijiji.ca/b-cars-trucks/canada/c174l0
  Page N : https://www.kijiji.ca/b-cars-trucks/canada/page-{n}/c174l0

Stop when parser returns 0 new rows (empty page / Kijiji redirected back to page 1).

No DB, no jsonify, no git push — just proves pagination + parser work.
Run: python src/reverse_engineer/kijiji_cars.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, List

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "src"))

from hyperSel import instance, parser

BASE_URL  = "https://www.kijiji.ca/b-cars-trucks/canada/c174l0"
PAGE_URL  = "https://www.kijiji.ca/b-cars-trucks/canada/page-{n}/c174l0"
MAX_PAGES = 100
PAGE_WAIT = 1.5  # seconds between page loads


def page_url(n: int) -> str:
    return BASE_URL if n == 1 else PAGE_URL.format(n=n)


def run() -> None:
    browser = instance.Browser(driver_choice="selenium", headless=True, zoom_level=100)
    browser.init_browser()
    browser.go_to_site("https://foreandr.github.io/")

    grand_total: List[List[Any]] = []

    for page_num in range(1, MAX_PAGES + 1):
        url = page_url(page_num)

        try:
            browser.go_to_site(url)
            time.sleep(PAGE_WAIT)

            soup      = browser.return_current_soup()
            page_data = parser.main(soup)

            if not page_data:
                print(f"[page {page_num}] No data returned — end of results.")
                break

            before = len(grand_total)
            grand_total.extend(page_data)
            grand_total = [list(x) for x in set(tuple(x) for x in grand_total)]
            new_rows = len(grand_total) - before

            print(
                f"[page {page_num}/{MAX_PAGES}] this_page={len(page_data)}"
                f" | new_unique={new_rows} | total={len(grand_total)}"
            )

            if new_rows == 0:
                # All rows already seen → Kijiji looped back to page 1
                print(f"[page {page_num}] No new unique rows — stopping.")
                break

        except Exception as exc:
            print(f"[page {page_num}] ERROR — {exc}")
            break

    browser.close_browser()
    print(f"\nDone. Grand total raw rows: {len(grand_total)}")


if __name__ == "__main__":
    run()
