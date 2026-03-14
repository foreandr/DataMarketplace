"""Crawler stub for _craigslist_realestate."""
from __future__ import annotations

from typing import Iterable

try:
    from crawlers.base import BaseCrawler, CrawlItem
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "src"))
    from crawlers.base import BaseCrawler, CrawlItem


class CraigslistRealestateCrawler(BaseCrawler):
    def run(self) -> Iterable[CrawlItem]:
        return self.stub_run()


if __name__ == "__main__":
    CraigslistRealestateCrawler(name="_craigslist_realestate").run()
