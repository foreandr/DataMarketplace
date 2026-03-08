"""SQLite storage with JSON payloads."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from crawlers.base import CrawlItem


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(db_path))


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            item_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            fetched_at TEXT NOT NULL
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_items_source ON items(source);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_items_type ON items(item_type);")
    conn.commit()


def insert_items(conn: sqlite3.Connection, items: Iterable[CrawlItem]) -> int:
    rows = [
        (
            item.source,
            item.item_type,
            json.dumps(item.payload, ensure_ascii=False),
            _utc_now_iso(),
        )
        for item in items
    ]
    if not rows:
        return 0
    conn.executemany(
        "INSERT INTO items (source, item_type, payload_json, fetched_at) VALUES (?, ?, ?, ?);",
        rows,
    )
    conn.commit()
    return len(rows)


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
