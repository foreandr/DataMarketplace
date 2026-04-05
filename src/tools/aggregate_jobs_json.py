"""Aggregate all job databases into one large JSON file.

Usage:
  python src/tools/aggregate_jobs_json.py
  python src/tools/aggregate_jobs_json.py --output files/all_jobs.json
  python src/tools/aggregate_jobs_json.py --no-raw
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))


def _discover_job_sources() -> list[str]:
    sources: list[str] = []
    for entry in SRC_DIR.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name
        if "job" not in name:
            continue
        if not (entry / "database.sqlite").exists():
            continue
        if not (entry / "schema.py").exists():
            continue
        sources.append(name)
    return sorted(sources)


def _iter_rows(db_path: Path) -> Iterable[dict[str, Any]]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute("SELECT * FROM items;")
        while True:
            batch = cur.fetchmany(1000)
            if not batch:
                break
            for row in batch:
                yield dict(row)
    finally:
        conn.close()


def _build_location(row: dict[str, Any]) -> str | None:
    if row.get("location_raw"):
        return str(row.get("location_raw")).strip() or None
    if row.get("location"):
        return str(row.get("location")).strip() or None
    parts = [
        row.get("city"),
        row.get("province") or row.get("state"),
        row.get("country"),
    ]
    parts = [str(p).strip() for p in parts if p]
    if not parts:
        return None
    return ", ".join(parts)


def _normalize_row(source: str, row: dict[str, Any], include_raw: bool) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "source": source,
        "id": row.get("id"),
        "title": row.get("title"),
        "company": row.get("company"),
        "location_raw": row.get("location_raw") or row.get("location"),
        "location": _build_location(row),
        "city": row.get("city"),
        "region": row.get("province") or row.get("state"),
        "country": row.get("country"),
        "posted_date": row.get("posted_date"),
        "updated_date": row.get("updated_date"),
        "expires_date": row.get("expires_date"),
        "crawled_at": row.get("crawled_at"),
        "url": row.get("url"),
        "pay": row.get("pay"),
        "pay_min": row.get("pay_min"),
        "pay_max": row.get("pay_max"),
        "pay_period": row.get("pay_period"),
        "pay_raw": row.get("pay_raw") or row.get("salary_raw"),
        "work_mode": row.get("work_mode"),
        "job_type": row.get("job_type"),
        "schedule": row.get("schedule"),
        "benefits": row.get("benefits"),
        "summary": row.get("summary"),
        "description": row.get("description"),
        "category": row.get("category"),
        "image_url": row.get("image_url"),
        "job_number": row.get("job_number"),
        "noc_code": row.get("noc_code"),
        "views": row.get("views"),
        "source_site": row.get("source"),
        "flags": {
            "is_lmia": row.get("is_lmia"),
            "is_direct_apply": row.get("is_direct_apply"),
            "is_quick_apply": row.get("is_quick_apply"),
            "is_easy_apply": row.get("is_easy_apply"),
            "is_sponsored": row.get("is_sponsored"),
            "is_new": row.get("is_new"),
        },
    }
    if include_raw:
        normalized["raw"] = row
    return normalized


def _write_json(
    output_path: Path,
    sources: list[str],
    include_raw: bool,
) -> dict[str, int]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    total = 0
    first = True
    with output_path.open("w", encoding="utf-8") as f:
        f.write("[\n")
        for source in sources:
            db_path = SRC_DIR / source / "database.sqlite"
            source_count = 0
            for row in _iter_rows(db_path):
                normalized = _normalize_row(source, row, include_raw)
                if not first:
                    f.write(",\n")
                f.write(json.dumps(normalized, ensure_ascii=True))
                first = False
                source_count += 1
                total += 1
            counts[source] = source_count
        f.write("\n]\n")
    counts["__total__"] = total
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate all job databases into a single JSON file."
    )
    parser.add_argument(
        "--output",
        default=str(ROOT_DIR / "files" / "aggregated_jobs.json"),
        help="Output JSON path.",
    )
    parser.add_argument(
        "--no-raw",
        action="store_true",
        help="Omit the raw per-source row payloads.",
    )
    args = parser.parse_args()

    sources = _discover_job_sources()
    if not sources:
        print("No job databases found under src/.")
        return 1

    counts = _write_json(
        output_path=Path(args.output),
        sources=sources,
        include_raw=not args.no_raw,
    )
    print("Wrote JSON:", args.output)
    for name in sources:
        print(f"  {name}: {counts.get(name, 0)}")
    print(f"  total: {counts.get('__total__', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
