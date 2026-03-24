#!/usr/bin/env python3
"""
init.py  —  run this once after every clone, or any time you're unsure.

    python init.py

Detects the current state of the repo and does exactly what's needed:
  - Git LFS not installed?        → installs it
  - LFS not hooked into this repo? → runs git lfs install
  - .sqlite files not LFS-tracked? → migrates them
  - LFS objects missing on disk?   → git lfs pull
  - No venv?                       → creates one
  - Deps not installed?            → pip installs from req.txt
  - No .env?                       → copies .env.example if it exists

Safe to re-run at any time — every step checks before acting.
Works on Windows and Linux/macOS.
"""

import os
import re
import shutil
import subprocess
import sys
import venv
from pathlib import Path


REPO_ROOT = Path(__file__).parent.resolve()


# ── small helpers ─────────────────────────────────────────────────────────────

def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    pretty = " ".join(str(c) for c in cmd)
    print(f"    $ {pretty}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    for line in r.stdout.strip().splitlines():
        print(f"      {line}")
    for line in r.stderr.strip().splitlines():
        print(f"      (stderr) {line}")
    return r


def _ok(msg: str)   -> None: print(f"    [OK]   {msg}")
def _skip(msg: str) -> None: print(f"    [--]   {msg}")
def _warn(msg: str) -> None: print(f"    [WARN] {msg}")
def _step(msg: str) -> None: print(f"\n>>  {msg}")


# ── git lfs ───────────────────────────────────────────────────────────────────

def _lfs_installed() -> bool:
    r = subprocess.run(["git", "lfs", "version"], capture_output=True, text=True)
    return r.returncode == 0


def _ensure_lfs_installed() -> None:
    _step("Git LFS — checking installation")
    if _lfs_installed():
        v = subprocess.run(["git", "lfs", "version"],
                           capture_output=True, text=True).stdout.strip()
        _ok(v)
        return

    _warn("Git LFS not found — attempting install...")

    if sys.platform == "win32":
        print()
        print("    Install Git LFS on Windows:")
        print("      Option A (winget):  winget install GitHub.GitLFS")
        print("      Option B:           https://git-lfs.com")
        print()
        print("    After installing, re-run:  python init.py")
        sys.exit(1)

    managers = {
        "apt-get": ["sudo", "apt-get", "install", "-y", "git-lfs"],
        "yum":     ["sudo", "yum",     "install", "-y", "git-lfs"],
        "dnf":     ["sudo", "dnf",     "install", "-y", "git-lfs"],
        "brew":    ["brew", "install",             "git-lfs"],
        "pacman":  ["sudo", "pacman",  "-S", "--noconfirm", "git-lfs"],
    }
    for mgr, cmd in managers.items():
        if shutil.which(mgr):
            subprocess.run(cmd)
            break
    else:
        print("    ERROR: no supported package manager found.")
        print("    Please install manually: https://git-lfs.com")
        sys.exit(1)

    if not _lfs_installed():
        print("    ERROR: install failed — please install Git LFS manually.")
        sys.exit(1)
    _ok("installed successfully")


def _lfs_hooked() -> bool:
    """True if git lfs install has been run for this repo."""
    cfg = subprocess.run(
        ["git", "config", "--local", "filter.lfs.process"],
        capture_output=True, text=True
    )
    return cfg.returncode == 0 and "git-lfs" in cfg.stdout


def _ensure_lfs_hooked() -> None:
    _step("Git LFS — registering hooks in this repo")
    if _lfs_hooked():
        _skip("already registered")
        return
    _run(["git", "lfs", "install", "--local"])
    _ok("hooks registered")


def _attrs_track_sqlite() -> bool:
    """True if .gitattributes already declares *.sqlite as LFS."""
    attrs = REPO_ROOT / ".gitattributes"
    if not attrs.exists():
        return False
    return "*.sqlite" in attrs.read_text()


def _ensure_gitattributes() -> None:
    _step("Git LFS — verifying .gitattributes")
    if _attrs_track_sqlite():
        _skip(".gitattributes already tracks *.sqlite")
        return
    _run(["git", "lfs", "track", "*.sqlite"])
    _run(["git", "lfs", "track", "*.db"])
    _ok(".gitattributes updated")


def _sqlite_files_in_plain_git() -> list[str]:
    """Return paths of *.sqlite that are indexed in regular git (not LFS)."""
    tracked = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True
    ).stdout.splitlines()

    plain = []
    for path in tracked:
        if not path.lower().endswith(".sqlite"):
            continue
        # Check if it's already an LFS pointer
        r = subprocess.run(
            ["git", "cat-file", "blob", f"HEAD:{path}"],
            capture_output=True, text=True
        )
        if "oid sha256:" not in r.stdout:   # not an LFS pointer yet
            plain.append(path)
    return plain


def _migrate_sqlite_to_lfs() -> None:
    _step("Git LFS — migrating existing .sqlite files")
    plain = _sqlite_files_in_plain_git()
    if not plain:
        _skip("all .sqlite files already use LFS (or none exist yet)")
        return

    print(f"    Found {len(plain)} plain-git .sqlite file(s):")
    for p in plain:
        mb = Path(p).stat().st_size / 1024 / 1024 if Path(p).exists() else 0
        print(f"      {p}  ({mb:.1f} MB)")

    for p in plain:
        _run(["git", "rm", "--cached", p])

    _run(["git", "add", ".gitattributes"] + plain)

    r = _run([
        "git", "commit",
        "-m", "chore: migrate *.sqlite databases to Git LFS"
    ])
    if r.returncode == 0:
        _ok("migration committed — run `git push` to upload LFS objects")
    elif "nothing to commit" in r.stdout + r.stderr:
        _skip("nothing new to commit")
    else:
        _warn("commit step had issues (see above)")


def _ensure_lfs_objects_present() -> None:
    _step("Git LFS — pulling LFS objects (actual DB files)")
    attrs = REPO_ROOT / ".gitattributes"
    if not attrs.exists():
        _skip("no .gitattributes yet — skipping lfs pull")
        return
    r = _run(["git", "lfs", "pull"])
    if r.returncode == 0:
        _ok("LFS objects up to date")
    else:
        _warn("git lfs pull had issues — you may need to run it manually")


# ── python environment ────────────────────────────────────────────────────────

def _ensure_venv() -> tuple[Path, Path]:
    _step("Python — virtual environment")
    venv_dir    = REPO_ROOT / "venv"
    win         = sys.platform == "win32"
    pip_path    = venv_dir / ("Scripts" if win else "bin") / ("pip.exe" if win else "pip")
    python_path = venv_dir / ("Scripts" if win else "bin") / ("python.exe" if win else "python")

    if venv_dir.exists() and pip_path.exists():
        _skip("venv/ already exists")
    else:
        print(f"    Creating venv at {venv_dir} ...")
        venv.create(str(venv_dir), with_pip=True)
        _ok("venv created")

    return pip_path, python_path


def _ensure_deps(pip_path: Path) -> None:
    _step("Python — installing dependencies")
    req = REPO_ROOT / "req.txt"
    if not req.exists():
        req = REPO_ROOT / "requirements.txt"
    if not req.exists():
        _warn("no req.txt or requirements.txt found — skipping")
        return

    # Upgrade pip silently
    subprocess.run([str(pip_path), "install", "--upgrade", "pip", "-q"],
                   capture_output=True)

    packages = [
        l.strip() for l in req.read_text().splitlines()
        if l.strip() and not l.strip().startswith("#")
    ]
    print(f"    Installing {len(packages)} package(s) from {req.name} ...")
    for pkg in packages:
        r = subprocess.run(
            [str(pip_path), "install", pkg, "-q"],
            capture_output=True, text=True
        )
        status = "OK" if r.returncode == 0 else "FAIL"
        print(f"      {status}  {pkg}")
    _ok("dependencies installed")


# ── .env ──────────────────────────────────────────────────────────────────────

def _ensure_env() -> None:
    _step(".env file")
    env = REPO_ROOT / ".env"
    if env.exists():
        _skip(".env already present")
        return
    example = REPO_ROOT / ".env.example"
    if example.exists():
        shutil.copy(example, env)
        _ok("copied .env.example → .env  (fill in your secrets)")
    else:
        _skip("no .env.example found — skipping")


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    os.chdir(REPO_ROOT)

    print("=" * 58)
    print("  DataMarketplace - init.py")
    print("=" * 58)

    # LFS setup
    _ensure_lfs_installed()
    _ensure_lfs_hooked()
    _ensure_gitattributes()
    _migrate_sqlite_to_lfs()
    _ensure_lfs_objects_present()

    # Python setup
    pip_path, _ = _ensure_venv()
    _ensure_deps(pip_path)

    # Env
    _ensure_env()

    win = sys.platform == "win32"
    activate = r"venv\Scripts\activate" if win else "source venv/bin/activate"

    print()
    print("=" * 58)
    print("  ALL DONE")
    print("=" * 58)
    print(f"  Activate venv:  {activate}")
    print(f"  Run app:        python app.py")
    print()


if __name__ == "__main__":
    main()
