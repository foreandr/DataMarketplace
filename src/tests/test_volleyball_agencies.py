from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AGENCIES_PATH = ROOT / "actions" / "volleyball" / "agencies.txt"
SCRIPT_PATH = ROOT / "actions" / "volleyball" / "print_agencies.py"


def test_agencies_file_is_clean_and_script_prints_each_agency() -> None:
    raw_lines = AGENCIES_PATH.read_text(encoding="utf-8").splitlines()
    non_empty_lines = [line for line in raw_lines if line.strip()]

    assert non_empty_lines
    assert all('"' not in line for line in non_empty_lines)
    assert all(not line.strip().endswith(",") for line in non_empty_lines)

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )

    printed_lines = [line for line in result.stdout.splitlines() if line.strip()]

    assert printed_lines == non_empty_lines
