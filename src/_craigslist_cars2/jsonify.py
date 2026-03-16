"""Jsonify for _craigslist_cars2."""
from __future__ import annotations

from typing import Any, List


class CraigslistCars2Jsonify:
    def __init__(self, source_name: str = "_craigslist_cars2"):
        self.source_name = source_name

    def to_json(self, data: Any, location: dict | None = None) -> List[dict]:
        # TODO: convert scraped rows into dicts.
        # Stamp each record with location data if provided:
        loc_city    = (location or {}).get('city', '')
        loc_state   = (location or {}).get('state', '')
        loc_country = (location or {}).get('country', '')
        return data if isinstance(data, list) else []
