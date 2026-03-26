"""
eBay Cars discovery - Round 3.
Tests:
  1. Does Make=Toyota without _nkw avoid the browse-page redirect?
  2. How many pages per make?
  3. What do the actual li[data-viewport] items look like?
  4. Do we need _nkw at all if we pass Make= directly?
"""
from __future__ import annotations
import sys, time, re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "src"))

from hyperSel import instance, parser

BASE_SACAT = "https://www.ebay.com/sch/i.html?_sacat=6001&LH_ItemCondition=3"

MAKES_SAMPLE = [
    "Toyota", "Ford", "Honda", "Chevrolet", "Nissan",
    "BMW", "Mercedes-Benz", "Dodge", "Jeep", "Hyundai",
    "Kia", "Subaru", "Audi", "Lexus", "Ram",
]


def get_items(browser, url: str, wait: float = 3.0):
    browser.go_to_site(url)
    time.sleep(wait)
    soup = browser.return_current_soup()
    items = soup.find_all("li", attrs={"data-viewport": True})
    current_url = browser.WEBDRIVER.current_url
    return soup, items, current_url


def get_total_hint(soup) -> str:
    for el in soup.find_all(True):
        text = el.get_text(strip=True)
        m = re.search(r'([\d,]+)\s+results?', text, re.IGNORECASE)
        if m and len(text) < 80:
            return text
    return "?"


def main():
    browser = instance.Browser(driver_choice="selenium", headless=False, zoom_level=100)
    browser.init_browser()
    browser.go_to_site("https://foreandr.github.io/")

    # ── Test 1: Make= without _nkw ────────────────────────────────────────────
    print("\n" + "="*60)
    print("TEST 1: Make=Toyota WITHOUT _nkw — does it show results?")
    print("="*60)
    url = f"{BASE_SACAT}&Make=Toyota&_dcat=6001"
    soup, items, cur_url = get_items(browser, url)
    print(f"  URL after load : {cur_url[:100]}")
    print(f"  Items found    : {len(items)}")
    print(f"  Total hint     : {get_total_hint(soup)}")

    # ── Test 2: Make= with _nkw=Toyota ───────────────────────────────────────
    print("\n" + "="*60)
    print("TEST 2: _nkw=Toyota WITH Make=Toyota — redundant but safe?")
    print("="*60)
    url = f"{BASE_SACAT}&_nkw=Toyota&Make=Toyota&_dcat=6001"
    soup, items, cur_url = get_items(browser, url)
    print(f"  URL after load : {cur_url[:100]}")
    print(f"  Items found    : {len(items)}")
    print(f"  Total hint     : {get_total_hint(soup)}")

    # ── Test 3: How many pages does Toyota have? ──────────────────────────────
    print("\n" + "="*60)
    print("TEST 3: Toyota page count (stop when items drop to 0)")
    print("="*60)
    base = f"{BASE_SACAT}&_nkw=Toyota"
    all_ids = set()
    for pg in range(1, 20):
        url = f"{base}&_pgn={pg}"
        soup, items, cur_url = get_items(browser, url, wait=2)
        ids = set(re.findall(r'/itm/(\d+)', cur_url + str(soup)[:5000]))
        new = ids - all_ids
        all_ids |= ids
        print(f"  Page {pg:2d}: {len(items):3d} items | {len(new):3d} new IDs | total unique: {len(all_ids)}")
        if len(items) == 0:
            print("  -> Empty page, stopping.")
            break

    # ── Test 4: sample the raw li[data-viewport] HTML ─────────────────────────
    print("\n" + "="*60)
    print("TEST 4: Raw HTML of first 2 li[data-viewport] items")
    print("="*60)
    url = f"{BASE_SACAT}&_nkw=Toyota&_pgn=1"
    soup, items, _ = get_items(browser, url)
    for i, li in enumerate(items[:2]):
        print(f"\n  --- Item {i} ---")
        print(li.get_text(separator=" | ", strip=True)[:400])

    # ── Test 5: full make sweep — coverage per make ────────────────────────────
    print("\n" + "="*60)
    print("TEST 5: Per-make sweep (1 page each) — unique IDs")
    print("="*60)
    seen_ids = set()
    for make in MAKES_SAMPLE:
        make_enc = make.replace(" ", "+").replace("-", "-")
        url = f"{BASE_SACAT}&_nkw={make_enc}&_pgn=1"
        soup, items, cur_url = get_items(browser, url, wait=2)
        ids = set(re.findall(r'/itm/(\d+)', str(soup)[:20000]))
        new = ids - seen_ids
        seen_ids |= ids
        total_hint = get_total_hint(soup)
        print(f"  {make:20s}: {len(items):3d} items | {len(new):3d} new IDs | "
              f"cumulative: {len(seen_ids):4d} | hint: {total_hint}")

    browser.close_browser()
    print(f"\nTotal unique /itm/ IDs across all makes (1 page each): {len(seen_ids)}")


if __name__ == "__main__":
    main()
