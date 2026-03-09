"""Base jsonify class."""
from __future__ import annotations

from typing import Any, List


class Jsonify:
    def __init__(self, source_name: str):
        self.source_name = source_name

    def to_json(self, data: Any) -> List[dict]:
        """Convert crawler output into JSON-serializable objects."""
        raise NotImplementedError

    def demo_data(self) -> Any:
        """Optional demo data for quick local testing."""
        return []
