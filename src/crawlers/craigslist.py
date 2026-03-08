"""Craigslist crawler stub."""
from __future__ import annotations

from typing import Iterable

from crawlers.base import BaseCrawler, CrawlItem


class CraigslistCrawler(BaseCrawler):
    def run(self) -> Iterable[CrawlItem]:
        return self.stub_run()
