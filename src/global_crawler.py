"""Global crawler runner – launches all crawlers in parallel, keeps them running forever."""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

# ---- Runtime settings ----
RAM_CAP_PERCENT    = 97.0
STAGGER_SECONDS    = 15 * 60  # wait between launching successive crawlers
CHECK_INTERVAL_SEC = 5


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength",                ctypes.c_ulong),
        ("dwMemoryLoad",            ctypes.c_ulong),
        ("ullTotalPhys",            ctypes.c_ulonglong),
        ("ullAvailPhys",            ctypes.c_ulonglong),
        ("ullTotalPageFile",        ctypes.c_ulonglong),
        ("ullAvailPageFile",        ctypes.c_ulonglong),
        ("ullTotalVirtual",         ctypes.c_ulonglong),
        ("ullAvailVirtual",         ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def _ram_usage_percent() -> float:
    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
    used = stat.ullTotalPhys - stat.ullAvailPhys
    return (used / stat.ullTotalPhys) * 100.0 if stat.ullTotalPhys else 0.0


def _discover_crawlers() -> list[str]:
    modules = []
    for p in sorted(SRC_DIR.iterdir()):
        if p.is_dir() and p.name.startswith("_") and (p / "crawler.py").exists():
            modules.append(p.name)
    return modules


def _spawn(module: str) -> subprocess.Popen:
    cmd = [sys.executable, "-m", f"{module}.crawler"]
    env = {**os.environ, "PYTHONPATH": str(SRC_DIR)}
    proc = subprocess.Popen(cmd, cwd=ROOT_DIR, env=env)
    print(f"[START] {module} (pid={proc.pid})")
    return proc


def _wait_for_ram(context: str) -> None:
    """Block until RAM is below the cap."""
    while _ram_usage_percent() >= RAM_CAP_PERCENT:
        print(f"[RAM] {_ram_usage_percent():.1f}% >= {RAM_CAP_PERCENT:.1f}% | waiting before {context}...")
        time.sleep(CHECK_INTERVAL_SEC)


def main() -> None:
    crawlers = _discover_crawlers()
    procs: dict[str, subprocess.Popen] = {}

    # ── Launch phase: stagger each crawler 15 minutes apart ───────────────────
    for i, module in enumerate(crawlers):
        _wait_for_ram(f"starting {module}")
        procs[module] = _spawn(module)

        # Between launches, wait the stagger window while babysitting already-
        # running crawlers so they get restarted if they crash early.
        if i < len(crawlers) - 1:
            deadline = time.time() + STAGGER_SECONDS
            while time.time() < deadline:
                for m, p in list(procs.items()):
                    if p.poll() is not None:
                        print(f"[DEAD] {m} (code={p.returncode}) – restarting")
                        procs[m] = _spawn(m)
                time.sleep(CHECK_INTERVAL_SEC)

    # ── Babysit phase: all crawlers are up, restart any that die ──────────────
    print(f"[ALL RUNNING] {list(procs.keys())}")
    while True:
        for module, proc in list(procs.items()):
            if proc.poll() is not None:
                print(f"[DEAD] {module} (code={proc.returncode}) – restarting")
                _wait_for_ram(f"restarting {module}")
                procs[module] = _spawn(module)
        time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    main()
