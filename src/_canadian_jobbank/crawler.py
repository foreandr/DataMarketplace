"""Crawler for _canadian_jobbank."""
from __future__ import annotations


class CanadianJobbankCrawler:
    def __init__(self, name: str = "_canadian_jobbank"):
        self.name = name

    def run(self) -> None:
        # TODO: implement
        print(f"[{self.name}] stub_run")


if __name__ == "__main__":
    CanadianJobbankCrawler().run()
