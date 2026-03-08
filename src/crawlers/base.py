"""Crawler base classes and interfaces."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Any


@dataclass
class CrawlItem:
    source: str
    item_type: str
    payload: Dict[str, Any]


class BaseCrawler:
    def __init__(self, name: str, item_type: str, seed_urls: Iterable[str] | None = None):
        self.name = name
        self.item_type = item_type
        self.seed_urls = list(seed_urls or [])

    def run(self) -> Iterable[CrawlItem]:
        """Return an iterable of CrawlItem. Override in subclasses."""
        raise NotImplementedError

    def stub_run(self) -> Iterable[CrawlItem]:
        """Base loop placeholder: print seed URLs, return no items."""
        for url in self.seed_urls:
            print(f"[{self.name}] seed_url: {url}")
        return []
