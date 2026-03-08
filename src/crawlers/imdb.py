"""IMDb crawler stub."""
from __future__ import annotations

from typing import Iterable

from crawlers.base import BaseCrawler, CrawlItem


class ImdbCrawler(BaseCrawler):
    def run(self) -> Iterable[CrawlItem]:
        raise NotImplementedError("Implement IMDb crawling logic.")
