"""Crawler stub."""
from __future__ import annotations

from typing import Iterable

try:
    from crawlers.base import BaseCrawler, CrawlItem
except ModuleNotFoundError:  # allow running directly from this folder
    import sys
    from pathlib import Path

    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "src"))
    from crawlers.base import BaseCrawler, CrawlItem


class ImdbMoviesCrawler(BaseCrawler):
    def run(self) -> Iterable[CrawlItem]:
        # Base template: each source owns its crawler file.
        return self.stub_run()


if __name__ == "__main__":
    ImdbMoviesCrawler(name="imdb_movies").run()
