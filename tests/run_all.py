from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    tests = [
        "test_resources.py",
        "test_schemas.py",
        "test_db_report.py",
        "app_test.py",
    ]

    failed = 0
    for t in tests:
        path = root / t
        print(f"\n=== RUN {t} ===")
        result = subprocess.run([sys.executable, str(path)], check=False)
        if result.returncode != 0:
            failed += 1

    print(f"\nCompleted. Failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
