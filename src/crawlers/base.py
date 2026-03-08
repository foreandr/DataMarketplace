"""Crawler base classes and interfaces."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Any


@dataclass
class CrawlItem:
    source: str
    payload: Dict[str, Any]


class BaseCrawler:
    def __init__(self, name: str):
        self.name = name

    def run(self) -> Iterable[CrawlItem]:
        """Return an iterable of CrawlItem. Override in subclasses."""
        raise NotImplementedError

    def stub_run(self) -> Iterable[CrawlItem]:
        """Base loop placeholder: print source name, return no items."""
        print(f"[{self.name}] stub_run")
        return []
