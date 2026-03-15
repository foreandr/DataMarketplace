from __future__ import annotations

import json
import time
from pathlib import Path

from tools import add_crawler as add_mod
from tools import delete_crawler as del_mod


def _module_name(source_name: str) -> str:
    name = source_name.replace("-", "_").lower()
    return name if name.startswith("_") else f"_{name}"


def _collection_entry_exists(module_name: str) -> bool:
    root = Path(__file__).resolve().parents[2]
    resources_path = root / "config" / "resources.json"
    data = json.loads(resources_path.read_text(encoding="utf-8"))
    return module_name in data.get("collections", {})


def test_delete_crawler_removes_artifacts() -> None:
    root = Path(__file__).resolve().parents[2]
    source_name = f"test_temp_source_{int(time.time())}"
    module_name = _module_name(source_name)

    paths = [
        root / "src" / module_name / "crawler.py",
        root / "src" / module_name / "schema.py",
        root / "src" / module_name / "jsonify.py",
        root / "src" / module_name / "demo_data.py",
        root / "src" / module_name / "database.sqlite",
    ]

    add_mod.main(source_name)
    del_mod.main(source_name)

    remaining = [p for p in paths if p.exists()]
    assert not remaining, f"Expected files to be removed: {remaining}"

    assert not _collection_entry_exists(module_name), f"Collection entry still present in config/resources.json for {module_name}"
