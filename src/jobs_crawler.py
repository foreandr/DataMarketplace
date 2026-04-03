"""Jobs-only crawler runner — launches only job-related crawlers."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

# Explicit allowlist so we never start cars/realestate.
JOB_MODULES = [
    "_canadian_jobbank",
    "_charityvillage_jobs",
    "_craigslist_jobs",
    "_eluta_jobs",
    "_goodwork_jobs",
    # "_indeed_jobs",
    "_saskjobs",
    "_workbc_jobs",
]

STAGGER_SECONDS = 10  # seconds between launches


def _spawn(module: str) -> subprocess.Popen:
    cmd = [sys.executable, "-m", f"{module}.crawler"]
    env = {**os.environ, "PYTHONPATH": str(SRC_DIR)}
    proc = subprocess.Popen(cmd, cwd=ROOT_DIR, env=env)
    print(f"[START] {module} (pid={proc.pid})")
    return proc


def main() -> None:
    procs: dict[str, subprocess.Popen] = {}
    for i, module in enumerate(JOB_MODULES):
        if not (SRC_DIR / module / "crawler.py").exists():
            print(f"[SKIP] {module} missing crawler.py")
            continue
        procs[module] = _spawn(module)
        if i < len(JOB_MODULES) - 1:
            time.sleep(STAGGER_SECONDS)

    print(f"[ALL RUNNING] {list(procs.keys())}")
    # Keep alive and restart any that exit
    while True:
        for module, proc in list(procs.items()):
            if proc.poll() is not None:
                print(f"[DEAD] {module} (code={proc.returncode}) — restarting")
                procs[module] = _spawn(module)
        time.sleep(5)


if __name__ == "__main__":
    main()
