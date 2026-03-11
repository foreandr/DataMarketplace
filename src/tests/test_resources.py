from __future__ import annotations

import json
from pathlib import Path


def test_resources_loads() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / "config" / "resources.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    collections = data.get("collections", {})
    assert collections, "No collections defined in resources.json"
