#!/usr/bin/env python3
"""
bootstrap.py
============
First-time setup for a fresh clone of this repository.

  git clone <repo-url>
  cd DataMarketplace
  python bootstrap.py

Works on Windows and Linux/macOS.

What it does
------------
1.  Verifies / installs Git LFS.
2.  Runs `git lfs install` to register hooks.
3.  Pulls all LFS objects (the actual database files).
4.  Creates a Python virtual environment (venv/).
5.  Installs all dependencies from req.txt.
6.  Copies .env.example → .env if no .env exists.
"""

import subprocess
import sys
import shutil
import os
import venv
from pathlib import Path


# ── helpers ───────────────────────────────────────────────────────────────────

def run(cmd: list[str], check: bool = False, **kwargs) -> subprocess.CompletedProcess:
    pretty = " ".join(str(c) for c in cmd)
    print(f"    $ {pretty}")
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.stdout.strip():
        for line in result.stdout.strip().splitlines():
            print(f"      {line}")
    if result.stderr.strip():
        for line in result.stderr.strip().splitlines():
            print(f"      (stderr) {line}")
    if check and result.returncode != 0:
        print(f"\n  ERROR: command failed (exit {result.returncode})")
        sys.exit(1)
    return result


def step(n: int, msg: str) -> None:
    print(f"\n[{n}] {msg}")


def is_windows() -> bool:
    return sys.platform == "win32"


# ── git lfs ───────────────────────────────────────────────────────────────────

def ensure_git_lfs() -> None:
    step(1, "Checking Git LFS installation...")
    result = subprocess.run(["git", "lfs", "version"], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"    OK — {result.stdout.strip()}")
        return

    print("    Git LFS not found on PATH.")

    if is_windows():
        print()
        print("    *** Windows: install Git LFS manually ***")
        print("    Option A (winget):  winget install GitHub.GitLFS")
        print("    Option B:           https://git-lfs.com")
        print()
        print("    After installing, re-run:  python bootstrap.py")
        sys.exit(1)

    # Linux / macOS
    print("    Attempting automatic install...")
    managers = {
        "apt-get": ["sudo", "apt-get", "install", "-y", "git-lfs"],
        "yum":     ["sudo", "yum",     "install", "-y", "git-lfs"],
        "dnf":     ["sudo", "dnf",     "install", "-y", "git-lfs"],
        "brew":    ["brew", "install",             "git-lfs"],
        "pacman":  ["sudo", "pacman",  "-S", "--noconfirm", "git-lfs"],
    }
    for mgr, cmd in managers.items():
        if shutil.which(mgr):
            print(f"    Using {mgr}...")
            subprocess.run(cmd)
            break
    else:
        print("    ERROR: No supported package manager found.")
        print("    Please install Git LFS manually: https://git-lfs.com")
        sys.exit(1)

    result = subprocess.run(["git", "lfs", "version"], capture_output=True, text=True)
    if result.returncode != 0:
        print("    ERROR: Git LFS install failed.")
        sys.exit(1)
    print(f"    Installed — {result.stdout.strip()}")


def setup_lfs(repo_root: Path) -> None:
    step(2, "Registering Git LFS hooks in this repo...")
    run(["git", "lfs", "install"], check=True)

    # If .gitattributes is missing (very old clone), create it
    attrs = repo_root / ".gitattributes"
    if not attrs.exists():
        print("    .gitattributes missing — creating it now...")
        run(["git", "lfs", "track", "*.sqlite"])
        run(["git", "lfs", "track", "*.db"])

    step(3, "Pulling LFS objects (downloading database files)...")
    result = run(["git", "lfs", "pull"])
    if result.returncode != 0:
        print("    WARNING: `git lfs pull` had issues — you may need to run it manually.")


# ── python venv + deps ────────────────────────────────────────────────────────

def setup_venv(repo_root: Path) -> Path:
    step(4, "Setting up Python virtual environment...")
    venv_dir = repo_root / "venv"

    if venv_dir.exists():
        print("    venv/ already exists — skipping creation.")
    else:
        print(f"    Creating venv at {venv_dir} ...")
        venv.create(str(venv_dir), with_pip=True)
        print("    Done.")

    # Resolve the pip / python inside the venv
    if is_windows():
        pip_path    = venv_dir / "Scripts" / "pip.exe"
        python_path = venv_dir / "Scripts" / "python.exe"
    else:
        pip_path    = venv_dir / "bin" / "pip"
        python_path = venv_dir / "bin" / "python"

    return pip_path, python_path


def install_deps(pip_path: Path, repo_root: Path) -> None:
    step(5, "Installing Python dependencies...")

    # Upgrade pip first
    run([str(pip_path), "install", "--upgrade", "pip"])

    # We have both req.txt (full) and requirements.txt (subset) — use req.txt
    req_file = repo_root / "req.txt"
    if not req_file.exists():
        req_file = repo_root / "requirements.txt"

    if not req_file.exists():
        print("    WARNING: No req.txt or requirements.txt found — skipping pip install.")
        return

    print(f"    Installing from {req_file.name} ...")
    # Strip comment lines and blank lines before passing to pip
    lines = [
        l.strip() for l in req_file.read_text().splitlines()
        if l.strip() and not l.strip().startswith("#")
    ]
    for pkg in lines:
        run([str(pip_path), "install", pkg])


# ── .env ──────────────────────────────────────────────────────────────────────

def setup_env(repo_root: Path) -> None:
    step(6, "Checking .env file...")
    env_file     = repo_root / ".env"
    env_example  = repo_root / ".env.example"

    if env_file.exists():
        print("    .env already exists — skipping.")
        return

    if env_example.exists():
        shutil.copy(env_example, env_file)
        print("    Copied .env.example → .env")
        print("    *** Edit .env and fill in your secrets before running the app. ***")
    else:
        print("    No .env or .env.example found — skipping.")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    repo_root = Path(__file__).parent.resolve()
    os.chdir(repo_root)

    print("=" * 60)
    print("  DataMarketplace Bootstrap")
    print("=" * 60)
    print(f"  Repo root : {repo_root}")
    print(f"  Platform  : {sys.platform}")
    print(f"  Python    : {sys.version.split()[0]}")

    ensure_git_lfs()
    setup_lfs(repo_root)
    pip_path, python_path = setup_venv(repo_root)
    install_deps(pip_path, repo_root)
    setup_env(repo_root)

    print()
    print("=" * 60)
    print("  BOOTSTRAP COMPLETE")
    print("=" * 60)
    print()
    if is_windows():
        activate = r"venv\Scripts\activate"
    else:
        activate = "source venv/bin/activate"
    print(f"  Activate venv :  {activate}")
    print(f"  Run app       :  python app.py")
    print()


if __name__ == "__main__":
    main()
