"""SQLite storage with JSON payloads."""
from __future__ import annotations

import json
import sqlite3
import re
from pathlib import Path
from typing import Iterable, Dict, List, Optional, Tuple

from crawlers.base import CrawlItem


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(db_path))


def init_db(conn: sqlite3.Connection) -> None:
    # Registry table for tracking source metadata.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_registry (
            source_name TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            last_crawled_at TEXT,
            last_row_count INTEGER,
            total_rows INTEGER NOT NULL DEFAULT 0,
            last_crawl_status TEXT,
            last_crawl_message TEXT
        );
        """
    )
    conn.commit()


def ensure_source_table(conn: sqlite3.Connection, table_name: str) -> None:
    safe_name = _sanitize_table_name(table_name)
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS "{safe_name}" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payload_json TEXT NOT NULL,
            fetched_at TEXT NOT NULL
        );
        """
    )
    _ensure_registry_row(conn, safe_name)
    conn.commit()


def insert_items(conn: sqlite3.Connection, items: Iterable[CrawlItem]) -> int:
    grouped: Dict[str, List[CrawlItem]] = {}
    for item in items:
        grouped.setdefault(item.source, []).append(item)

    total = 0
    for source, batch in grouped.items():
        ensure_source_table(conn, source)
        rows = [
            (json.dumps(item.payload, ensure_ascii=False), _utc_now_iso())
            for item in batch
        ]
        if not rows:
            continue
        conn.executemany(
            f'INSERT INTO "{_sanitize_table_name(source)}" (payload_json, fetched_at) VALUES (?, ?);',
            rows,
        )
        _update_registry_after_crawl(
            conn,
            source_name=source,
            inserted_count=len(rows),
            status="success",
            message=None,
        )
        total += len(rows)
    conn.commit()
    return total


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _sanitize_table_name(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+", name or ""):
        raise ValueError(
            f"Invalid table name '{name}'. Use only letters, numbers, and underscore."
        )
    return name


def _ensure_registry_row(conn: sqlite3.Connection, source_name: str) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO source_registry (source_name, created_at, total_rows)
        VALUES (?, ?, 0);
        """,
        (source_name, _utc_now_iso()),
    )


def _update_registry_after_crawl(
    conn: sqlite3.Connection,
    source_name: str,
    inserted_count: int,
    status: str,
    message: Optional[str],
) -> None:
    conn.execute(
        """
        UPDATE source_registry
        SET last_crawled_at = ?,
            last_row_count = ?,
            total_rows = total_rows + ?,
            last_crawl_status = ?,
            last_crawl_message = ?
        WHERE source_name = ?;
        """,
        (
            _utc_now_iso(),
            inserted_count,
            inserted_count,
            status,
            message,
            source_name,
        ),
    )


def record_crawl_failure(conn: sqlite3.Connection, source_name: str, message: str) -> None:
    _ensure_registry_row(conn, source_name)
    conn.execute(
        """
        UPDATE source_registry
        SET last_crawled_at = ?,
            last_crawl_status = ?,
            last_crawl_message = ?
        WHERE source_name = ?;
        """,
        (_utc_now_iso(), "failed", message, source_name),
    )
    conn.commit()


def record_crawl_success(
    conn: sqlite3.Connection,
    source_name: str,
    message: Optional[str] = None,
) -> None:
    _ensure_registry_row(conn, source_name)
    conn.execute(
        """
        UPDATE source_registry
        SET last_crawled_at = ?,
            last_row_count = ?,
            last_crawl_status = ?,
            last_crawl_message = ?
        WHERE source_name = ?;
        """,
        (_utc_now_iso(), 0, "success", message, source_name),
    )
    conn.commit()


def get_last_crawled_at(conn: sqlite3.Connection, source_name: str) -> Optional[str]:
    _ensure_registry_row(conn, source_name)
    row = conn.execute(
        "SELECT last_crawled_at FROM source_registry WHERE source_name = ?;",
        (source_name,),
    ).fetchone()
    return row[0] if row else None


def drop_source_table(conn: sqlite3.Connection, source_name: str) -> None:
    safe_name = _sanitize_table_name(source_name)
    conn.execute(f'DROP TABLE IF EXISTS "{safe_name}";')
    conn.commit()


def delete_registry_row(conn: sqlite3.Connection, source_name: str) -> None:
    conn.execute("DELETE FROM source_registry WHERE source_name = ?;", (source_name,))
    conn.commit()
