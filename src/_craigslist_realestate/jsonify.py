"""Jsonify for _craigslist_realestate."""
from __future__ import annotations

from typing import Any, List


class CraigslistRealestateJsonify:
    def __init__(self, source_name: str = "_craigslist_realestate"):
        self.source_name = source_name

    def to_json(self, data: Any) -> List[dict]:
        # TODO: implement
        return data if isinstance(data, list) else []
