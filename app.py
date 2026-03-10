from __future__ import annotations

import json
import os
import sqlite3
import sys
from importlib import import_module
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))
load_dotenv()
DATA_DIR = ROOT_DIR / "data"
DEFAULT_LIMIT = 100

app = Flask(__name__)


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


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/schemas")
def list_schemas():
    schema_files = sorted((ROOT_DIR / "src" / "schemas").glob("*.py"))
    names = [p.stem for p in schema_files if p.stem != "__init__"]
    return jsonify({"schemas": names})


@app.post("/query")
def query():
    try:
        payload = request.get_json(force=True)
        db_path = Path(payload["db_path"])
        schema_name = payload["schema"]
        select_fields = payload.get("select", ["*"])
        where = payload.get("where", [])
        order_by = payload.get("order_by", [])

        schema = _load_schema(schema_name)
        if select_fields != ["*"]:
            for f in select_fields:
                _validate_field(schema, f)
            select_sql = ", ".join(select_fields)
        else:
            select_sql = ", ".join(schema.field_names())

        where_sql, params = _build_where(schema, where)
        order_sql = _build_order_by(schema, order_by)

        sql = f"SELECT {select_sql} FROM {schema.table}{where_sql}{order_sql} LIMIT {DEFAULT_LIMIT};"

        conn = sqlite3.connect(str(db_path))
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        col_names = [d[0] for d in cur.description] if cur.description else []
        conn.close()

        return jsonify(
            {
                "sql": sql,
                "params": params,
                "rows": [dict(zip(col_names, r)) for r in rows],
                "row_count": len(rows),
                "limit": DEFAULT_LIMIT,
            }
        )
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400


if __name__ == "__main__":
    host = os.environ["API_HOST"]
    port = int(os.environ["API_PORT"])
    debug = os.environ["API_DEBUG"].lower() in {"1", "true", "yes", "on"}
    app.run(host=host, port=port, debug=debug)
