from __future__ import annotations

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from utils.config import load_json_config, get_data_path
from db.sqlite import connect, init_db, ensure_source_table


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


class _C:
    RESET = "\x1b[0m"
    DIM = "\x1b[2m"
    BOLD = "\x1b[1m"
    CYAN = "\x1b[36m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    RED = "\x1b[31m"
    MAGENTA = "\x1b[35m"


def _rule(label: str) -> str:
    return f"{_C.DIM}={'=' * 18}{_C.RESET} {_C.BOLD}{label}{_C.RESET} {_C.DIM}{'=' * 26}{_C.RESET}"


def _section(label: str) -> None:
    logging.info("")
    logging.info(_rule(label))
    logging.info("")


def _print_db_metadata(conn) -> None:
    cursor = conn.cursor()
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    ).fetchall()
    table_names = [row[0] for row in tables]

    logging.info("%sTables:%s %s", _C.CYAN, _C.RESET, table_names if table_names else "None")
    for table in table_names:
        cols = cursor.execute(f"PRAGMA table_info({table});").fetchall()
        col_names = [c[1] for c in cols]
        count = cursor.execute(f"SELECT COUNT(*) FROM {table};").fetchone()[0]
        logging.info(
            "%sTable:%s %s | %sColumns:%s %s | %sRows:%s %s",
            _C.MAGENTA,
            _C.RESET,
            table,
            _C.YELLOW,
            _C.RESET,
            col_names,
            _C.GREEN,
            _C.RESET,
            count,
        )


def main() -> None:
    load_dotenv()
    app_cfg = load_json_config("app.json")
    _setup_logging(app_cfg["app"]["log_level"])
    sources_cfg = load_json_config("sources.json")

    db_path = get_data_path(app_cfg["database"]["path"])
    conn = connect(db_path)
    init_db(conn)
    for source in sources_cfg.get("sources", []):
        name = source.get("name")
        if not name:
            continue
        ensure_source_table(conn, name)
    _section("Init DB")
    logging.info("%sInitialized database at%s %s", _C.GREEN, _C.RESET, db_path)
    _section("Metadata")
    _print_db_metadata(conn)
    conn.close()


if __name__ == "__main__":
    main()
