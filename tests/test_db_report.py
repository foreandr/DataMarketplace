from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    try:
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root))
        import db_report

        db_report.main()
        print("PASS: db_report ran")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
