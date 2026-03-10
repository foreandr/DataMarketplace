"""CSV registry for published APIs."""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Set, Tuple


def published_key(api_spec: Dict[str, Any], marketplace: str) -> Tuple[str, str, str]:
    name = str(api_spec.get("name", "")).strip()
    version = str(api_spec.get("version", "")).strip()
    return (marketplace, name, version)


def load_published_registry(path: Path) -> Set[Tuple[str, str, str]]:
    if not path.exists():
        return set()
    rows: Set[Tuple[str, str, str]] = set()
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.add((row.get("marketplace", ""), row.get("api_name", ""), row.get("api_version", "")))
    return rows


def record_published(
    path: Path,
    api_spec: Dict[str, Any],
    marketplace: str,
    metadata: Dict[str, Any] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()

    with path.open("a", encoding="utf-8", newline="") as f:
        fieldnames = ["marketplace", "api_name", "api_version", "published_at", "metadata_json"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "marketplace": marketplace,
                "api_name": str(api_spec.get("name", "")).strip(),
                "api_version": str(api_spec.get("version", "")).strip(),
                "published_at": _utc_now_iso(),
                "metadata_json": json.dumps(metadata or {}, ensure_ascii=False),
            }
        )


def _utc_now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
