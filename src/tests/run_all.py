from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    tests_dir = Path(__file__).resolve().parent
    cmd = [sys.executable, "-m", "pytest", str(tests_dir)]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
