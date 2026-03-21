#!/usr/bin/env python3
"""
init_lfs.py
===========
One-time migration of all .sqlite database files to Git LFS.

Run this ONCE on any machine that has the repo already cloned
and wants to enable LFS going forward.

  python init_lfs.py

Works on Windows and Linux/macOS.

What it does
------------
1.  Verifies Git LFS is installed (gives clear instructions if not).
2.  Runs `git lfs install` to register the hooks in this repo.
3.  Creates / updates .gitattributes so *.sqlite is LFS-tracked.
4.  Removes every *.sqlite that is currently stored in plain git from
    the index (the files stay on disk — only the git tracking changes).
5.  Re-adds those same files so they go in as LFS pointers.
6.  Commits the migration.
7.  Tells you exactly what to run next.
"""

import subprocess
import sys
import shutil
import os
from pathlib import Path


# ── helpers ───────────────────────────────────────────────────────────────────

def run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess:
    pretty = " ".join(str(c) for c in cmd)
    print(f"    $ {pretty}")
    result = subprocess.run(cmd, capture_output=True, text=True)
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


# ── git lfs install check ─────────────────────────────────────────────────────

def ensure_git_lfs() -> None:
    step(1, "Checking Git LFS installation...")
    result = subprocess.run(["git", "lfs", "version"], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"    OK — {result.stdout.strip()}")
        return

    print("    Git LFS not found on PATH.")

    if sys.platform == "win32":
        print()
        print("    *** Windows: install Git LFS manually ***")
        print("    1. Download from https://git-lfs.com  (or via winget: winget install GitHub.GitLFS)")
        print("    2. Run the installer.")
        print("    3. Re-run this script.")
        sys.exit(1)

    # Linux / macOS — try common package managers
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
            result = subprocess.run(cmd)
            if result.returncode == 0:
                break
    else:
        print("    ERROR: Could not auto-install Git LFS.")
        print("    Please install it manually: https://git-lfs.com")
        sys.exit(1)

    # Verify
    result = subprocess.run(["git", "lfs", "version"], capture_output=True, text=True)
    if result.returncode != 0:
        print("    ERROR: Git LFS still not found after install attempt.")
        sys.exit(1)
    print(f"    Installed — {result.stdout.strip()}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # Make sure we are in the repo root
    repo_root = Path(__file__).parent.resolve()
    os.chdir(repo_root)

    print("=" * 60)
    print("  Git LFS Migration")
    print("=" * 60)

    ensure_git_lfs()

    # ── 2. lfs install (registers smudge/clean filters in .git/config) ────────
    step(2, "Running `git lfs install` (registers hooks in this repo)...")
    run(["git", "lfs", "install"], check=True)

    # ── 3. .gitattributes ─────────────────────────────────────────────────────
    step(3, "Configuring .gitattributes for *.sqlite...")
    run(["git", "lfs", "track", "*.sqlite"])
    # *.db might already be in .gitignore but track it too just in case
    run(["git", "lfs", "track", "*.db"])
    print("    .gitattributes updated.")

    # ── 4. Find *.sqlite files currently in plain-git index ──────────────────
    step(4, "Scanning git index for .sqlite files tracked without LFS...")
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True, text=True, check=True
    )
    sqlite_in_index = [
        f for f in result.stdout.splitlines()
        if f.lower().endswith(".sqlite")
    ]

    if not sqlite_in_index:
        print("    No plain-git .sqlite files found — nothing to migrate.")
    else:
        print(f"    Found {len(sqlite_in_index)} file(s) to migrate:")
        for f in sqlite_in_index:
            size_bytes = Path(f).stat().st_size if Path(f).exists() else 0
            size_mb = size_bytes / (1024 * 1024)
            print(f"      {f}  ({size_mb:.1f} MB)")

        # ── 5. Remove from regular git index (files stay on disk) ─────────
        step(5, "Removing from regular git index (files stay on disk)...")
        for f in sqlite_in_index:
            run(["git", "rm", "--cached", f])

        # ── 6. Re-add through LFS filter ──────────────────────────────────
        step(6, "Re-adding via LFS...")
        run(["git", "add", ".gitattributes"] + sqlite_in_index)

    # Always stage .gitattributes even if nothing migrated
    run(["git", "add", ".gitattributes"])

    # ── 7. Commit ─────────────────────────────────────────────────────────────
    step(7, "Committing migration...")
    commit = run([
        "git", "commit",
        "-m", "chore: migrate *.sqlite databases to Git LFS\n\n"
              "- Added .gitattributes tracking *.sqlite via git-lfs\n"
              "- Re-indexed existing sqlite files as LFS pointers\n"
              "- Future database files will be stored in LFS automatically"
    ])

    if commit.returncode != 0:
        out = commit.stdout + commit.stderr
        if "nothing to commit" in out:
            print("    Nothing new to commit — LFS already configured.")
        else:
            print(f"    Commit failed (exit {commit.returncode}). See output above.")
            sys.exit(1)

    # ── Done ──────────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  DONE")
    print("=" * 60)
    print()
    print("Next steps:")
    print()
    print("  1.  Push (this uploads the LFS objects to your remote):")
    print("        git push")
    print()
    print("  2.  On any OTHER machine (fresh clone):")
    print("        git clone <your-repo-url>")
    print("        python bootstrap.py")
    print()
    print("  3.  On any OTHER machine (already cloned, no LFS yet):")
    print("        git pull")
    print("        python init_lfs.py")
    print()


if __name__ == "__main__":
    main()
