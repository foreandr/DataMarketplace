"""
eBay Cars discovery - Round 4.
Focus:
  1. What do actual listing items contain (skip ads)?
  2. How to extract item URL/ID from li[data-viewport] for dedup?
  3. Does Make= pagination actually page properly (do items change between pages)?
  4. How many real unique items per make across all pages?
"""
from __future__ import annotations
import sys, time, re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "src"))

from hyperSel import instance

BASE = "https://www.ebay.com/sch/i.html?_sacat=6001&LH_ItemCondition=3&_dcat=6001"


def get_page(browser, url, wait=3.0):
    browser.go_to_site(url)
    time.sleep(wait)
    soup = browser.return_current_soup()
    items = soup.find_all("li", attrs={"data-viewport": True})
    return soup, items


def item_urls(items) -> list[str]:
    """Extract the first /itm/ href from each li item."""
    urls = []
    for li in items:
        for a in li.find_all("a", href=True):
            href = a["href"]
            if "/itm/" in href:
                # normalize: strip query params, keep base /itm/ID
                m = re.search(r'(https://www\.ebay\.com/itm/\d+)', href)
                if m:
                    urls.append(m.group(1))
                    break
    return urls


def main():
    browser = instance.Browser(driver_choice="selenium", headless=False, zoom_level=100)
    browser.init_browser()
    browser.go_to_site("https://foreandr.github.io/")

    # ── Test 1: Inspect actual listing items (skip ads) ───────────────────────
    print("\n" + "="*60)
    print("TEST 1: Inspect li[data-viewport] items — text + first href")
    print("="*60)
    url = f"{BASE}&Make=Toyota&_pgn=1"
    soup, items = get_page(browser, url)
    print(f"  Total li[data-viewport]: {len(items)}")
    for i, li in enumerate(items[:8]):
        text = li.get_text(separator=" | ", strip=True)[:200]
        hrefs = [a["href"] for a in li.find_all("a", href=True) if "/itm/" in a["href"]][:1]
        href_short = hrefs[0][:80] if hrefs else "NO /itm/ href"
        print(f"  [{i:2d}] {text[:100]}")
        print(f"       href: {href_short}")

    # ── Test 2: item_urls() extraction ────────────────────────────────────────
    print("\n" + "="*60)
    print("TEST 2: item_urls() from page 1 Toyota")
    print("="*60)
    urls_p1 = item_urls(items)
    print(f"  Extracted {len(urls_p1)} /itm/ URLs from {len(items)} items")
    for u in urls_p1[:5]:
        print(f"  {u}")

    # ── Test 3: Does page 2 have different items? ─────────────────────────────
    print("\n" + "="*60)
    print("TEST 3: Compare page 1 vs page 2 Toyota — same items?")
    print("="*60)
    url2 = f"{BASE}&Make=Toyota&_pgn=2"
    soup2, items2 = get_page(browser, url2, wait=2)
    urls_p2 = item_urls(items2)
    overlap = set(urls_p1) & set(urls_p2)
    print(f"  Page 1: {len(urls_p1)} items | Page 2: {len(urls_p2)} items")
    print(f"  Overlap between p1 and p2: {len(overlap)}")
    if overlap:
        print(f"  -> Pages are IDENTICAL (eBay looped back)")
    else:
        print(f"  -> Pages have different items (pagination working!)")

    # ── Test 4: How many pages before overlap for Ford (bigger make)? ─────────
    print("\n" + "="*60)
    print("TEST 4: Ford — paginate until overlap detected")
    print("="*60)
    seen = set()
    for pg in range(1, 15):
        url = f"{BASE}&Make=Ford&_pgn={pg}"
        soup, items = get_page(browser, url, wait=2)
        urls = set(item_urls(items))
        non_ad_urls = {u for u in urls if u}
        overlap_with_seen = non_ad_urls & seen
        new_urls = non_ad_urls - seen
        seen |= non_ad_urls
        print(f"  Page {pg:2d}: {len(items):3d} li items | {len(non_ad_urls):3d} /itm/ URLs "
              f"| {len(new_urls):3d} new | {len(overlap_with_seen):3d} overlap | total: {len(seen)}")
        if len(new_urls) == 0 and pg > 1:
            print(f"  -> No new URLs on page {pg}, stopping")
            break

    # ── Test 5: Total count label on page ────────────────────────────────────
    print("\n" + "="*60)
    print("TEST 5: Find total count text for Ford")
    print("="*60)
    url = f"{BASE}&Make=Ford&_pgn=1"
    soup, items = get_page(browser, url)
    for el in soup.find_all(True):
        t = el.get_text(strip=True)
        if re.search(r'\d[\d,]+\s*(results?|listings?|items?)', t, re.I) and len(t) < 100:
            print(f"  Found: {t!r}")

    browser.close_browser()


if __name__ == "__main__":
    main()
