"""Crawler stub."""
from __future__ import annotations

from typing import Iterable
import time
from hyperSel import instance, parser, log

try:
    from crawlers.base import BaseCrawler, CrawlItem
    from utils.geo import get_all_cities
    from jsonify_logic.craigslist_cars import CraigslistCarsJsonify
except ModuleNotFoundError:  # allow running directly from this folder
    import sys
    from pathlib import Path

    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "src"))
    from crawlers.base import BaseCrawler, CrawlItem
    from utils.geo import get_all_cities
    from jsonify_logic.craigslist_cars import CraigslistCarsJsonify


class CraigslistCarsCrawler(BaseCrawler):
    def run(self) -> Iterable[CrawlItem]:
        browser = instance.Browser(
            driver_choice='selenium',
            headless=False,
            zoom_level=100
        )
        browser.init_browser()
        browser.go_to_site("https://foreandr.github.io/")
        
        for idx, city in enumerate(get_all_cities()):
            print(f"[{self.name}] city: {city}")
            city_without_spaces = city.replace(" ","").lower()
            url = f"https://{city_without_spaces}.craigslist.org/search/cta#search=2~list~0"
            print("url:", url)
            browser.go_to_site(url)

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
                print(f"Scroll {scroll_count}: Moved from {current_y}px to {target_y}px")
                
                time.sleep(time_between_scrolls)

                soup = browser.return_current_soup()
                all_data = parser.main(soup)
                
                # Extend and remove duplicates from list of lists
                total_data.extend(all_data)
                total_data = [list(x) for x in set(tuple(x) for x in total_data)]
                
                print(f"Current unique items in total_data: {len(total_data)}")
                
                if scroll_count % 10 == 0:
                    print(f"Periodic Check: Found {len(all_data)} items on last pass.")

            if idx == 0:
                input("holding here")
            input("hit end of cities")

            jsonifier = CraigslistCarsJsonify(self.name)
            json_data = jsonifier.to_json(total_data)
            print(f"[{self.name}] jsonified items: {len(json_data)}")
            
        return self.stub_run()


if __name__ == "__main__":
    CraigslistCarsCrawler(name="craigslist_cars").run()
