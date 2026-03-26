"""
eBay Cars discovery - Round 2.
Tests:
  1. Does _pgn=N paginate correctly on the working search URL?
  2. How many total results does eBay report?
  3. Does make-based search (_nkw=toyota) work and give different listings?
  4. Is there a way to get ALL listings without a keyword?
"""
from __future__ import annotations
import sys, time, re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "src"))

from hyperSel import instance, parser


MAKES = [
    "toyota", "ford", "honda", "chevrolet", "nissan",
    "bmw", "mercedes", "dodge", "jeep", "volkswagen",
]

BASE = "https://www.ebay.com/sch/i.html?_sacat=6001&LH_ItemCondition=3"


def get_page(browser, url: str, wait: float = 3.0):
    browser.go_to_site(url)
    time.sleep(wait)
    soup = browser.return_current_soup()
    items = soup.find_all("li", attrs={"data-viewport": True})
    return soup, items


def extract_total_results(soup) -> str:
    """Try to find eBay's 'X results' count in the page."""
    for el in soup.find_all(True):
        text = el.get_text(strip=True)
        m = re.search(r'([\d,]+)\s+results?\s+for', text, re.IGNORECASE)
        if m:
            return m.group(0)
        m2 = re.search(r'([\d,]+)\s+listings?', text, re.IGNORECASE)
        if m2 and len(text) < 100:
            return text
    return "not found"


def extract_pagination_links(soup) -> list:
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if "_pgn=" in href and text:
            links.append(f"  [{text}] -> {href[:120]}")
    return links


def main():
    browser = instance.Browser(driver_choice="selenium", headless=False, zoom_level=100)
    browser.init_browser()
    browser.go_to_site("https://foreandr.github.io/")

    # ── Test 1: pagination on _nkw=car ────────────────────────────────────────
    print("\n" + "="*60)
    print("TEST 1: Does _pgn work on the keyword search?")
    print("="*60)
    for page in [1, 2, 3]:
        url = f"{BASE}&_nkw=car&_pgn={page}"
        soup, items = get_page(browser, url)
        total = extract_total_results(soup)
        pg_links = extract_pagination_links(soup)
        print(f"\n  Page {page}: {len(items)} items | total hint: {total}")
        print(f"  URL stayed: {browser.WEBDRIVER.current_url[:80]}")
        if pg_links:
            print(f"  Pagination links found:")
            for l in pg_links[:5]:
                print(l)
        else:
            print("  No _pgn= links found in page")

    # ── Test 2: make-based search ─────────────────────────────────────────────
    print("\n" + "="*60)
    print("TEST 2: Make-based searches — coverage overlap check")
    print("="*60)
    all_ids = set()
    for make in MAKES:
        url = f"{BASE}&_nkw={make}&_pgn=1"
        soup, items = get_page(browser, url)
        total = extract_total_results(soup)
        # Extract item IDs from /itm/ hrefs
        ids = set()
        for a in soup.find_all("a", href=True):
            m = re.search(r'/itm/(\d+)', a["href"])
            if m:
                ids.add(m.group(1))
        new_ids = ids - all_ids
        all_ids |= ids
        print(f"  {make:15s}: {len(items):3d} list items | {len(ids):3d} /itm/ IDs | "
              f"{len(new_ids):3d} new | total unique so far: {len(all_ids)} | result hint: {total}")

    # ── Test 3: no-keyword URL with _from=R40 ─────────────────────────────────
    print("\n" + "="*60)
    print("TEST 3: No keyword with _from=R40 — does it show listings?")
    print("="*60)
    url = f"{BASE}&_from=R40&_pgn=1"
    soup, items = get_page(browser, url, wait=5)
    total = extract_total_results(soup)
    print(f"  Items: {len(items)} | URL: {browser.WEBDRIVER.current_url[:100]}")
    print(f"  Total hint: {total}")

    # ── Test 4: run parser.main on working page and show raw rows ─────────────
    print("\n" + "="*60)
    print("TEST 4: What does parser.main() return on this page?")
    print("="*60)
    url = f"{BASE}&_nkw=car&_pgn=1"
    soup, items = get_page(browser, url)
    rows = parser.main(soup)
    print(f"  parser.main() returned {len(rows)} rows")
    for i, row in enumerate(rows[:5]):
        print(f"  row[{i}]: {row}")

    browser.close_browser()


if __name__ == "__main__":
    main()
