"""Crawler for _craigslist_cars2."""
from __future__ import annotations


class CraigslistCars2Crawler:
    def __init__(self, name: str = "_craigslist_cars2"):
        self.name = name

    def run(self) -> None:
        # TODO: implement
        print(f"[{self.name}] stub_run")


if __name__ == "__main__":
    CraigslistCars2Crawler().run()
