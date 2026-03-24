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

# ---- Crash-backoff settings ----
FAST_CRASH_SEC = 60    # a process that dies within this many seconds is a "fast crash"
BACKOFF_AFTER  = 3     # consecutive fast crashes before backing off
BACKOFF_SEC    = 300   # 5-minute cooling-off period after repeated fast crashes


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


def _ensure_lfs_active() -> None:
    """Verify git-lfs is installed and hooked into this repo before anything runs.
    If either check fails, runs init.py to fix it automatically."""
    lfs_installed = subprocess.run(
        ["git", "lfs", "version"], capture_output=True
    ).returncode == 0

    lfs_hooked = False
    if lfs_installed:
        r = subprocess.run(
            ["git", "config", "--local", "filter.lfs.process"],
            capture_output=True, text=True, cwd=ROOT_DIR,
        )
        lfs_hooked = r.returncode == 0 and "git-lfs" in r.stdout

    if lfs_installed and lfs_hooked:
        print("[LFS] git-lfs active and hooked — OK")
        return

    if not lfs_installed:
        print("[LFS] git-lfs not installed — running init.py to fix...")
    else:
        print("[LFS] git-lfs hooks not registered in this repo — running init.py to fix...")

    result = subprocess.run(
        [sys.executable, str(ROOT_DIR / "init.py")],
        cwd=ROOT_DIR,
    )
    if result.returncode != 0:
        print("[LFS] FATAL: init.py failed — please run it manually before starting crawlers.")
        sys.exit(1)

    # Re-verify after init
    lfs_installed = subprocess.run(
        ["git", "lfs", "version"], capture_output=True
    ).returncode == 0
    r = subprocess.run(
        ["git", "config", "--local", "filter.lfs.process"],
        capture_output=True, text=True, cwd=ROOT_DIR,
    )
    lfs_hooked = r.returncode == 0 and "git-lfs" in r.stdout

    if not (lfs_installed and lfs_hooked):
        print("[LFS] FATAL: git-lfs still not active after init.py — cannot continue.")
        sys.exit(1)

    print("[LFS] git-lfs is now active — continuing.")


def _wait_for_ram(context: str) -> None:
    """Block until RAM is below the cap."""
    while _ram_usage_percent() >= RAM_CAP_PERCENT:
        print(f"[RAM] {_ram_usage_percent():.1f}% >= {RAM_CAP_PERCENT:.1f}% | waiting before {context}...")
        time.sleep(CHECK_INTERVAL_SEC)


def main() -> None:
    _ensure_lfs_active()
    crawlers = _discover_crawlers()
    procs:        dict[str, subprocess.Popen] = {}
    start_times:  dict[str, float]            = {}
    fast_crashes: dict[str, int]              = {}

    def spawn_tracked(module: str) -> subprocess.Popen:
        start_times[module] = time.time()
        fast_crashes.setdefault(module, 0)
        return _spawn(module)

    def restart(module: str) -> None:
        elapsed = time.time() - start_times.get(module, 0)
        if elapsed < FAST_CRASH_SEC:
            fast_crashes[module] = fast_crashes.get(module, 0) + 1
        else:
            fast_crashes[module] = 0

        n = fast_crashes[module]
        if n >= BACKOFF_AFTER:
            print(f"[BACKOFF] {module} crashed {n}x in <{FAST_CRASH_SEC}s – "
                  f"waiting {BACKOFF_SEC}s before retrying")
            time.sleep(BACKOFF_SEC)
            fast_crashes[module] = 0

        _wait_for_ram(f"restarting {module}")
        procs[module] = spawn_tracked(module)

    # ── Launch phase: stagger each crawler 15 minutes apart ───────────────────
    for i, module in enumerate(crawlers):
        _wait_for_ram(f"starting {module}")
        procs[module] = spawn_tracked(module)

        # Between launches, wait the stagger window while babysitting already-
        # running crawlers so they get restarted if they crash early.
        if i < len(crawlers) - 1:
            deadline = time.time() + STAGGER_SECONDS
            while time.time() < deadline:
                for m, p in list(procs.items()):
                    if p.poll() is not None:
                        print(f"[DEAD] {m} (code={p.returncode}) – restarting")
                        restart(m)
                time.sleep(CHECK_INTERVAL_SEC)

    # ── Babysit phase: all crawlers are up, restart any that die ──────────────
    print(f"[ALL RUNNING] {list(procs.keys())}")
    while True:
        for module, proc in list(procs.items()):
            if proc.poll() is not None:
                print(f"[DEAD] {module} (code={proc.returncode}) – restarting")
                restart(module)
        time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    main()
