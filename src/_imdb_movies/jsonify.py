"""Jsonify for _imdb_movies."""
from __future__ import annotations

from typing import Any, List


class ImdbMoviesJsonify:
    def __init__(self, source_name: str = "_imdb_movies"):
        self.source_name = source_name

    def to_json(self, data: Any) -> List[dict]:
        # TODO: implement
        return data if isinstance(data, list) else []
