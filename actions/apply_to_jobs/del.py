import sqlite3
from pathlib import Path
from datetime import datetime

# Import SOURCES to get the path to the actual WorkBC job database
# Ensure this script is in the same directory as main.py
try:
    from main import SOURCES, DB as TRACKER_DB_PATH
except ImportError:
    # Fallback paths if import fails
    ROOT = Path(__file__).resolve().parents[2]
    SOURCES = {"workbc": ROOT / "src/_workbc_jobs/database.sqlite"}
    TRACKER_DB_PATH = Path(__file__).resolve().parent / "database.sqlite"

def manage_databases(target_source="workbc"):
    # --- PART 1: SOURCE DB INSPECTION (READ ONLY) ---
    workbc_path = SOURCES.get("workbc")
    if workbc_path and workbc_path.exists():
        src_conn = sqlite3.connect(workbc_path)
        try:
            total = src_conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
            print(f"\n[SOURCE CHECK] Total jobs in WorkBC database: {total}")
        except sqlite3.Error as e:
            print(f"[SOURCE CHECK] Could not read WorkBC DB: {e}")
        finally:
            src_conn.close()
    else:
        print("\n[SOURCE CHECK] WorkBC source database not found.")

    # --- PART 2: TRACKER DB CLEANUP ---
    conn = sqlite3.connect(TRACKER_DB_PATH)
    cursor = conn.cursor()

    def print_tracker(label):
        print(f"\n--- TRACKER: {label} ---")
        cursor.execute("SELECT id, title, source, applied_at FROM applied_jobs")
        rows = cursor.fetchall()
        if not rows:
            print("Tracker is empty.")
        for row in rows:
            print(row)

    # 1. Show state before
    print_tracker("DATA BEFORE DELETION")

    # 2. Delete by source
    print(f"\nDeleting from tracker where source = '{target_source}'...")
    cursor.execute("DELETE FROM applied_jobs WHERE source = ?", (target_source,))
    
    # 3. Delete where timestamp is less than 5 minutes ago
    # (i.e., delete entries newer than 'now - 5 minutes')
    print("Deleting from tracker where applied_at is newer than 5 minutes ago...")
    cursor.execute(
        "DELETE FROM applied_jobs WHERE applied_at > datetime('now', '-5 minutes')"
    )
    
    conn.commit()

    # 4. Show state after
    print_tracker("DATA AFTER DELETION")
    
    conn.close()

if __name__ == "__main__":
    manage_databases("workbc")