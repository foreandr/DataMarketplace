"""
actions/apply_to_jobs/utils.py

Utility helpers for inspecting the job source databases.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SOURCES = {
    "canadian_jobbank": ROOT / "src/_canadian_jobbank/database.sqlite",
    "charityvillage":   ROOT / "src/_charityvillage_jobs/database.sqlite",
    "craigslist":       ROOT / "src/_craigslist_jobs/database.sqlite",
    "goodwork":         ROOT / "src/_goodwork_jobs/database.sqlite",
    "indeed":           ROOT / "src/_indeed_jobs/database.sqlite",
    "saskjobs":         ROOT / "src/_saskjobs/database.sqlite",
    "workbc":           ROOT / "src/_workbc_jobs/database.sqlite",
}


def print_work_modes() -> None:
    """Print all distinct work_mode values from every source that has the column."""
    for source_name, db_path in SOURCES.items():
        if not db_path.exists():
            print(f"[{source_name}] database not found, skipping.")
            continue

        conn = sqlite3.connect(db_path)
        try:
            # Check if work_mode column exists
            cols = [r[1] for r in conn.execute("PRAGMA table_info(items)").fetchall()]
            if "work_mode" not in cols:
                print(f"[{source_name}] no work_mode column")
                continue

            rows = conn.execute(
                "SELECT DISTINCT work_mode, COUNT(*) as cnt FROM items GROUP BY work_mode ORDER BY cnt DESC"
            ).fetchall()
            values = [(r[0], r[1]) for r in rows]
            print(f"[{source_name}]")
            for val, cnt in values:
                print(f"  {repr(val):45s} ({cnt} rows)")
        except sqlite3.Error as e:
            print(f"[{source_name}] error: {e}")
        finally:
            conn.close()


if __name__ == "__main__":
    print("Available work_mode values across all job databases:\n")
    print_work_modes()
