"""Global crawler runner (sequential, RAM-capped, time-boxed)."""
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
RAM_CAP_PERCENT = 95.0
RUN_MINUTES = 15
CHECK_INTERVAL_SEC = 5


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
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


def _run_one(module: str) -> None:
    cmd = [sys.executable, "-m", f"{module}.crawler"]
    env = dict(**dict(**dict(os.environ)))
    env["PYTHONPATH"] = str(SRC_DIR)
    proc = subprocess.Popen(cmd, cwd=ROOT_DIR, env=env)
    start = time.time()
    timeout = RUN_MINUTES * 60

    while True:
        if proc.poll() is not None:
            return
        if time.time() - start >= timeout:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
            return
        time.sleep(CHECK_INTERVAL_SEC)


def main() -> None:
    crawlers = _discover_crawlers()
    for module in crawlers:
        _run_one(module)

        # Gate the next crawler on RAM usage.
        while _ram_usage_percent() >= RAM_CAP_PERCENT:
            print(f"[RAM] { _ram_usage_percent():.1f}% >= {RAM_CAP_PERCENT:.1f}% | waiting...")
            time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    main()
