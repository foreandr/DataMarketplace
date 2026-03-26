"""
eBay Cars discovery script.
Runs live Selenium, explores the page, and reports:
  - Does the page have a "next" button or scroll trigger?
  - What does the paginated URL look like?
  - How many total results does eBay report?
  - What sub-categories / filter dimensions are visible?
"""
from __future__ import annotations
import sys, time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "src"))

from hyperSel import instance
from bs4 import BeautifulSoup

def report_section(title: str, items: list) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    for item in items:
        print(f"  {item}")


def discover(url: str, label: str, browser) -> None:
    print(f"\n>>> Loading: {url}")
    browser.go_to_site(url)
    time.sleep(3)

    soup = browser.return_current_soup()

    # ── 1. Total results count ────────────────────────────────────────────────
    total_hints = []
    for el in soup.find_all(string=True):
        t = el.strip()
        if any(k in t.lower() for k in ["results", "items found", "listings"]) and any(c.isdigit() for c in t):
            if len(t) < 120:
                total_hints.append(t)
    report_section(f"[{label}] Total result hints", total_hints[:10])

    # ── 2. Pagination buttons / links ─────────────────────────────────────────
    pagination_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if any(k in href.lower() for k in ["_pgn=", "page=", "pgn", "&pg=", "offset"]):
            pagination_links.append(f"TEXT={text!r:20s}  HREF={href[:120]}")
        elif any(k in text.lower() for k in ["next", "previous", "page 2", "›", "»"]):
            pagination_links.append(f"TEXT={text!r:20s}  HREF={href[:120]}")
    report_section(f"[{label}] Pagination links found", pagination_links[:15])

    # ── 3. Current URL (may have changed after JS redirect) ──────────────────
    current_url = browser.WEBDRIVER.current_url
    print(f"\n  Current URL after load: {current_url}")

    # ── 4. Scroll-trigger indicators ─────────────────────────────────────────
    scroll_hints = []
    for el in soup.find_all(attrs={"data-infinite": True}):
        scroll_hints.append(f"data-infinite: {el.get('data-infinite')}")
    for el in soup.find_all(class_=lambda c: c and any(k in c for k in ["infinite", "lazy", "load-more"])):
        scroll_hints.append(f"class={el.get('class')}")
    report_section(f"[{label}] Infinite-scroll/lazy-load indicators", scroll_hints[:10])

    # ── 5. Listing count on this page ─────────────────────────────────────────
    # Try common eBay listing containers
    listing_candidates = [
        ("li[data-viewport]",        soup.find_all("li",  attrs={"data-viewport": True})),
        (".s-item",                   soup.select(".s-item")),
        ("[class*='s-item']",         [t for t in soup.find_all(True) if "s-item" in " ".join(t.get("class", []))]),
        ("ul.srp-results li",         soup.select("ul.srp-results li")),
    ]
    report_section(f"[{label}] Listing containers found",
                   [f"{sel}: {len(els)} elements" for sel, els in listing_candidates if els])

    # ── 6. Filter / sub-category links ───────────────────────────────────────
    filter_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if any(k in href for k in ["LH_", "_sacat=", "Makes", "Model", "Year"]) and text:
            filter_links.append(f"{text[:40]:40s}  {href[:100]}")
    report_section(f"[{label}] Filter/subcategory links", filter_links[:20])

    # ── 7. Try scrolling once and check if new items appear ──────────────────
    before_scroll = len(soup.select(".s-item") or soup.find_all("li", attrs={"data-viewport": True}))
    browser.WEBDRIVER.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    soup2 = browser.return_current_soup()
    after_scroll = len(soup2.select(".s-item") or soup2.find_all("li", attrs={"data-viewport": True}))
    print(f"\n  Scroll test — items before: {before_scroll}, after: {after_scroll}")
    if after_scroll > before_scroll:
        print("  >>> INFINITE SCROLL DETECTED")
    else:
        print("  >>> No new items after scroll — likely paginator, not infinite scroll")


def dump_html_sample(soup, label: str, chars: int = 3000) -> None:
    """Print a slice of the raw HTML to see what eBay actually rendered."""
    html = str(soup)
    print(f"\n--- RAW HTML SAMPLE [{label}] (first {chars} chars) ---")
    print(html[:chars])
    print(f"--- END SAMPLE (total html len={len(html)}) ---")


def main():
    browser = instance.Browser(driver_choice="selenium", headless=False, zoom_level=100)
    browser.init_browser()
    browser.go_to_site("https://foreandr.github.io/")

    # --- Round 2: try URLs that should return actual listings ---

    # A: used-car search with keyword to force results page
    discover("https://www.ebay.com/sch/i.html?_nkw=car&_sacat=6001&LH_ItemCondition=3", "used-cars-kw", browser)

    # B: decade filter URL we saw on the landing page
    discover(
        "https://www.ebay.com/b/Cars-Trucks/6001/bn_1865117"
        "?_fsrp=0&_sacat=6001&LH_ItemCondition=3000%7C1000&_pgn=1",
        "decade-filter", browser
    )

    # C: dump raw HTML of the current page so we can see what eBay rendered
    browser.go_to_site("https://www.ebay.com/sch/i.html?_nkw=car&_sacat=6001&LH_ItemCondition=3")
    time.sleep(5)
    soup = browser.return_current_soup()
    dump_html_sample(soup, "used-cars-raw", chars=5000)

    # D: check what the URL became after redirect
    print(f"\nFinal current URL: {browser.WEBDRIVER.current_url}")

    # E: count ALL anchor tags and list unique href patterns
    all_hrefs = [a["href"] for a in soup.find_all("a", href=True)]
    ebay_hrefs = [h for h in all_hrefs if "ebay.com" in h]
    print(f"\nTotal <a> tags: {len(all_hrefs)} | eBay hrefs: {len(ebay_hrefs)}")
    # Show unique path patterns
    from urllib.parse import urlparse
    paths = {}
    for h in ebay_hrefs:
        p = urlparse(h).path.split("/")[1:3]
        key = "/".join(p)
        paths[key] = paths.get(key, 0) + 1
    print("URL path patterns (top 20):")
    for k, v in sorted(paths.items(), key=lambda x: -x[1])[:20]:
        print(f"  /{k}  x{v}")

    browser.close_browser()


if __name__ == "__main__":
    main()
