from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable


def report_base_dir(root: Path, report_name: str) -> Path:
    return root / report_name


def dated_report_dir(root: Path, report_name: str, when: datetime | None = None) -> Path:
    when = when or datetime.now()
    return report_base_dir(root, report_name) / f"{when:%Y}" / f"{when:%m}" / f"{when:%d}"


def write_report_json(
    root: Path,
    report_name: str,
    prefix: str,
    payload: dict,
    when: datetime | None = None,
) -> Path:
    when = when or datetime.now()
    target_dir = dated_report_dir(root, report_name, when)
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = when.strftime("%Y-%m-%d_%H-%M-%S")
    out_path = target_dir / f"{prefix}_{stamp}.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def iter_report_files(root: Path, report_name: str, pattern: str) -> Iterable[Path]:
    base = report_base_dir(root, report_name)
    if not base.exists():
        return []
    return base.rglob(pattern)
