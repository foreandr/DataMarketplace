"""Crawler for _craigslist_realestate."""
from __future__ import annotations


class CraigslistRealestateCrawler:
    def __init__(self, name: str = "_craigslist_realestate"):
        self.name = name

    def run(self) -> None:
        # TODO: implement
        print(f"[{self.name}] stub_run")


if __name__ == "__main__":
    CraigslistRealestateCrawler().run()
