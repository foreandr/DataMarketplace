from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from report.report_paths import write_report_json

ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"
LOG_DIR = ROOT_DIR / "logs" / "report"
REPORT_NAME = "db_report"


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


def _fetched_at_metrics(conn: sqlite3.Connection, table: str) -> dict | None:
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
        return {
            "rows_last_1h": last_1h,
            "rows_last_24h": last_24h,
            "ts_col": ts_col,
        }
    except Exception:
        return None


def _report_db(path: Path) -> dict:
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
        return {
            "db_name": path.name,
            "path": str(path),
            "size_bytes": size,
            "modified_at": mtime,
            "tables": [],
        }

    tables_payload = []
    for table in table_names:
        cols = _table_columns(conn, table)
        count = _table_row_count(conn, table)
        metrics = _fetched_at_metrics(conn, table)
        print(f"{C.MAGENTA}Table:{C.RESET} {table}")
        print(f"  {C.YELLOW}Columns:{C.RESET} {cols}")
        print(f"  {C.GREEN}Rows:{C.RESET} {count}")
        if metrics:
            print(
                f"  {C.CYAN}Rates:{C.RESET} "
                f"rows_last_1h={metrics['rows_last_1h']} | "
                f"rows_last_24h={metrics['rows_last_24h']} | "
                f"ts_col={metrics['ts_col']}"
            )
        tables_payload.append(
            {
                "name": table,
                "columns": cols,
                "rows": count,
                "rates": metrics,
            }
        )
    conn.close()
    print(f"{C.DIM}{'-' * 70}{C.RESET}")
    return {
        "db_name": path.name,
        "path": str(path),
        "size_bytes": size,
        "modified_at": mtime,
        "tables": tables_payload,
    }


def main() -> None:
    print("")
    print(_rule("DB Report"))
    print("")

    dbs = sorted(SRC_DIR.glob("_*/database.sqlite"))
    if not dbs:
        print(f"{C.YELLOW}No database.sqlite files found in:{C.RESET} {SRC_DIR}")
        return

    payload = []
    for db in dbs:
        payload.append(_report_db(db))

    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_path = write_report_json(
        LOG_DIR,
        REPORT_NAME,
        "db_report",
        {"generated_at": stamp, "data": payload},
    )
    print(f"{C.GREEN}Saved report:{C.RESET} {out_path}")


if __name__ == "__main__":
    main()
