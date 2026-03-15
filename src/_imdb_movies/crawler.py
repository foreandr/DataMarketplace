"""Crawler for _imdb_movies."""
from __future__ import annotations


class ImdbMoviesCrawler:
    def __init__(self, name: str = "_imdb_movies"):
        self.name = name

    def run(self) -> None:
        # TODO: implement
        print(f"[{self.name}] stub_run")


if __name__ == "__main__":
    ImdbMoviesCrawler().run()
