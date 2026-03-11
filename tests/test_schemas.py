from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    try:
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root / "src"))
        from schemas.craigslist_cars import SCHEMA as cars_schema

        if not cars_schema.field_names():
            print("FAIL: craigslist_cars schema has no fields")
            return 1
        print("PASS: schemas import and fields present")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
