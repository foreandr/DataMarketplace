from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"


class C:
    RESET = "\x1b[0m"
    DIM = "\x1b[2m"
    BOLD = "\x1b[1m"
    CYAN = "\x1b[36m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    RED = "\x1b[31m"
    MAGENTA = "\x1b[35m"


def _rule(label: str) -> str:
    return f"{C.DIM}={'=' * 16}{C.RESET} {C.BOLD}{label}{C.RESET} {C.DIM}{'=' * 34}{C.RESET}"


def _fmt_bytes(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
    return [r[1] for r in rows]


def _table_row_count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table};").fetchone()[0]


def _fetched_at_metrics(conn: sqlite3.Connection, table: str) -> str | None:
    cols = _table_columns(conn, table)
    ts_col = None
    if "crawled_at" in cols:
        ts_col = "crawled_at"
    elif "fetched_at" in cols:
        ts_col = "fetched_at"
    if not ts_col:
        return None

    now = datetime.now()
    one_hour = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    one_day = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

    try:
        last_1h = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {ts_col} >= ?;",
            (one_hour,),
        ).fetchone()[0]
        last_24h = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {ts_col} >= ?;",
            (one_day,),
        ).fetchone()[0]
        return f"rows_last_1h={last_1h} | rows_last_24h={last_24h} | ts_col={ts_col}"
    except Exception:
        return None


def _report_db(path: Path) -> None:
    size = path.stat().st_size
    mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    print(_rule(path.name))
    print(f"{C.CYAN}Path:{C.RESET} {path}")
    print(f"{C.CYAN}Size:{C.RESET} {_fmt_bytes(size)}")
    print(f"{C.CYAN}Modified:{C.RESET} {mtime}")

    conn = sqlite3.connect(str(path))
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    ).fetchall()
    table_names = [t[0] for t in tables]

    if not table_names:
        print(f"{C.YELLOW}No tables found.{C.RESET}")
        conn.close()
        return

    for table in table_names:
        cols = _table_columns(conn, table)
        count = _table_row_count(conn, table)
        metrics = _fetched_at_metrics(conn, table)
        print(f"{C.MAGENTA}Table:{C.RESET} {table}")
        print(f"  {C.YELLOW}Columns:{C.RESET} {cols}")
        print(f"  {C.GREEN}Rows:{C.RESET} {count}")
        if metrics:
            print(f"  {C.CYAN}Rates:{C.RESET} {metrics}")
    conn.close()
    print(f"{C.DIM}{'-' * 70}{C.RESET}")


def main() -> None:
    print("")
    print(_rule("DB Report"))
    print("")

    if not DATA_DIR.exists():
        print(f"{C.RED}Data directory not found:{C.RESET} {DATA_DIR}")
        return

    dbs = sorted(DATA_DIR.glob("*.sqlite"))
    if not dbs:
        print(f"{C.YELLOW}No .sqlite files found in:{C.RESET} {DATA_DIR}")
        return

    for db in dbs:
        _report_db(db)


if __name__ == "__main__":
    main()
