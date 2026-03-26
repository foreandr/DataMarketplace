"""Jsonify for _workbc_jobs."""
from __future__ import annotations

from typing import Any, List


class WorkbcJobsJsonify:
    def __init__(self, source_name: str = "_workbc_jobs"):
        self.source_name = source_name

    def to_json(self, data: Any, location: dict | None = None) -> List[dict]:
        # TODO: convert scraped rows into dicts.
        # Stamp each record with location data if provided:
        loc_city    = (location or {}).get('city', '')
        loc_country = (location or {}).get('country', '')
        return data if isinstance(data, list) else []

    def run_analysis(
        self,
        data: Any,
        location: dict | None = None,
        print_samples: bool = False,
    ) -> List[dict]:
        # Placeholder to match crawler API.
        # When you implement parsing, return cleaned records here.
        _ = print_samples  # unused for now
        return self.to_json(data, location=location)
