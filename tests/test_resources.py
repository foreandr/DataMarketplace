from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    try:
        path = Path(__file__).resolve().parents[1] / "config" / "resources.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        collections = data.get("collections", {})
        if not collections:
            print("FAIL: No collections defined")
            return 1
        print("PASS: resources.json loaded")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
