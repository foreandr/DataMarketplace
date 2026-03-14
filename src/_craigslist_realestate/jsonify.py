"""Jsonify stub for _craigslist_realestate."""
from __future__ import annotations

from typing import Any, List

try:
    from jsonify_logic.base import Jsonify
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "src"))
    from jsonify_logic.base import Jsonify


class CraigslistRealestateJsonify(Jsonify):
    def to_json(self, data: Any) -> List[dict]:
        # TODO: implement
        return data if isinstance(data, list) else []
