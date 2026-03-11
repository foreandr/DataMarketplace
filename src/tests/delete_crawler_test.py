from __future__ import annotations

import json
import time
from pathlib import Path

from tools import add_crawler as add_mod
from tools import delete_crawler as del_mod


def _module_name(source_name: str) -> str:
    return source_name.replace("-", "_").lower()


def _source_entry_exists(source_name: str) -> bool:
    root = Path(__file__).resolve().parents[2]
    sources_path = root / "config" / "sources.json"
    data = json.loads(sources_path.read_text(encoding="utf-8"))
    return any(s.get("name") == source_name for s in data.get("sources", []))


def test_delete_crawler_removes_artifacts() -> None:
    root = Path(__file__).resolve().parents[2]
    source_name = f"test_temp_source_{int(time.time())}"
    module_name = _module_name(source_name)

    paths = [
        root / "src" / "crawlers" / f"{module_name}.py",
        root / "src" / "jsonify_logic" / f"{module_name}.py",
        root / "src" / "demo_data" / f"{module_name}.py",
        root / "src" / "schemas" / f"{module_name}.py",
        root / "data" / f"{source_name}.sqlite",
    ]

    add_mod.main(source_name, enabled=False)
    del_mod.main(source_name)

    remaining = [p for p in paths if p.exists()]
    assert not remaining, f"Expected files to be removed: {remaining}"

    assert not _source_entry_exists(source_name), "Source entry still present in config/sources.json"
