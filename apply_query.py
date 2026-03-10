from __future__ import annotations

import json
import logging
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Any

import sqlite3


ROOT_DIR = Path(__file__).resolve().parent
LOG_DIR = ROOT_DIR / "logs" / "queries"
DEFAULT_LIMIT = 100


def _setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"queries_{datetime.now().strftime('%Y-%m-%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
    )


def _load_query(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_schema(schema_module: str):
    mod = import_module(f"schemas.{schema_module}")
    return mod.SCHEMA


def _field_type_map(schema) -> dict[str, str]:
    return {f.name: f.type for f in schema.fields}


def _validate_field(schema, field: str) -> None:
    if field not in schema.field_names():
        raise ValueError(f"Unknown field: {field}")


def _coerce_value(field_type: str, value: Any) -> Any:
    if value is None:
        return None
    if field_type == "INTEGER":
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("Expected INTEGER")
        return value
    if field_type == "REAL":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("Expected REAL")
        return float(value)
    # TEXT / BLOB fallthrough
    if not isinstance(value, str):
        raise TypeError("Expected TEXT")
    return value


def _build_where(schema, where: list[dict]) -> tuple[str, list]:
    if not where:
        return "", []
    field_types = _field_type_map(schema)
    clauses = []
    params = []
    for w in where:
        field = w.get("field")
        op = str(w.get("op", "")).lower()
        value = w.get("value")
        _validate_field(schema, field)
        if op not in {"=", "!=", "<", "<=", ">", ">=", "like", "in"}:
            raise ValueError(f"Unsupported operator: {op}")
        if op == "in":
            if not isinstance(value, list) or not value:
                raise TypeError("IN expects a non-empty list")
            coerced = [_coerce_value(field_types[field], v) for v in value]
            placeholders = ", ".join(["?"] * len(coerced))
            clauses.append(f"{field} IN ({placeholders})")
            params.extend(coerced)
        else:
            coerced = _coerce_value(field_types[field], value)
            clauses.append(f"{field} {op.upper()} ?")
            params.append(coerced)
    return " WHERE " + " AND ".join(clauses), params


def _build_order_by(schema, order_by: list[dict]) -> str:
    if not order_by:
        return ""
    parts = []
    for ob in order_by:
        field = ob.get("field")
        direction = str(ob.get("direction", "asc")).lower()
        _validate_field(schema, field)
        if direction not in {"asc", "desc"}:
            raise ValueError("direction must be asc or desc")
        parts.append(f"{field} {direction.upper()}")
    return " ORDER BY " + ", ".join(parts)


def main() -> None:
    _setup_logging()
    query_path = ROOT_DIR / "config" / "query.json"
    if not query_path.exists():
        raise FileNotFoundError(f"Query config not found: {query_path}")

    cfg = _load_query(query_path)
    db_path = Path(cfg["db_path"])
    schema_name = cfg["schema"]
    select_fields = cfg.get("select", ["*"])
    where = cfg.get("where", [])
    order_by = cfg.get("order_by", [])

    schema = _load_schema(schema_name)
    field_types = _field_type_map(schema)

    if select_fields != ["*"]:
        for f in select_fields:
            _validate_field(schema, f)
        select_sql = ", ".join(select_fields)
    else:
        select_sql = ", ".join(schema.field_names())

    where_sql, params = _build_where(schema, where)
    order_sql = _build_order_by(schema, order_by)

    sql = f"SELECT {select_sql} FROM {schema.table}{where_sql}{order_sql} LIMIT {DEFAULT_LIMIT};"
    logging.info("DB: %s", db_path)
    logging.info("SQL: %s", sql)
    logging.info("Params: %s", params)

    conn = sqlite3.connect(str(db_path))
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    conn.close()

    logging.info("Rows returned: %s", len(rows))
    for row in rows[:10]:
        logging.info("Row: %s", row)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, TypeError) as exc:
        print(f"Query error: {exc}")
