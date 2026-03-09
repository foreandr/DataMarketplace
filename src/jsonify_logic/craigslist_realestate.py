"""Jsonify stub for craigslist_realestate."""
from __future__ import annotations

from typing import Any, List

try:
    from jsonify_logic.base import Jsonify
except ModuleNotFoundError:  # allow running directly from this folder
    import sys
    from pathlib import Path

    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "src"))
    from jsonify_logic.base import Jsonify


class CraigslistRealestateJsonify(Jsonify):
    def to_json(self, data: Any) -> List[dict]:
        # TODO: convert list-of-lists into list of dicts.
        return data if isinstance(data, list) else []

    def demo_data(self) -> Any:
        from demo_data.craigslist_realestate import DEMO_DATA

        return DEMO_DATA


if __name__ == "__main__":
    jsonifier = CraigslistRealestateJsonify("craigslist_realestate")
    sample = jsonifier.demo_data()
    result = jsonifier.to_json(sample)
    print("Input:", sample)
    print("Output:", result)
