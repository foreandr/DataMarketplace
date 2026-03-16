from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, Response, render_template
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))
load_dotenv()
LOG_DIR = ROOT_DIR / "logs"
FOREVER_LOG_DIR = LOG_DIR / "forever"
REQUEST_LOG_PATH = LOG_DIR / "api_requests.log"
SERVER_LOG_PATH = FOREVER_LOG_DIR / "server.log"
ERROR_LOG_PATH = FOREVER_LOG_DIR / "errors.log"

app = Flask(__name__)


def _setup_server_logging() -> None:
    FOREVER_LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("datamarketplace")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

        server_handler = logging.FileHandler(SERVER_LOG_PATH, encoding="utf-8")
        server_handler.setLevel(logging.INFO)
        server_handler.setFormatter(formatter)

        error_handler = logging.FileHandler(ERROR_LOG_PATH, encoding="utf-8")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)

        logger.addHandler(server_handler)
        logger.addHandler(error_handler)


def _logger() -> logging.Logger:
    return logging.getLogger("datamarketplace")


def _query_limit() -> int:
    """Server-side limit only — never taken from user input."""
    return int(os.environ.get("MID_LIMIT", 250))


def _load_schema(schema_module: str):
    mod = import_module(f"{schema_module}.schema")
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


def _load_resources() -> dict:
    path = ROOT_DIR / "config" / "resources.json"
    if not path.exists():
        raise FileNotFoundError(f"Resource config not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _build_where_from_filter(schema, flt: dict) -> tuple[str, list]:
    if not flt:
        return "", []
    field_types = _field_type_map(schema)
    clauses = []
    params = []
    for field, spec in flt.items():
        _validate_field(schema, field)
        if isinstance(spec, dict):
            for op, value in spec.items():
                if op not in {"$eq", "$ne", "$lt", "$lte", "$gt", "$gte", "$like", "$in"}:
                    raise ValueError(f"Unsupported operator: {op}")
                sql_op = {
                    "$eq": "=",
                    "$ne": "!=",
                    "$lt": "<",
                    "$lte": "<=",
                    "$gt": ">",
                    "$gte": ">=",
                    "$like": "LIKE",
                    "$in": "IN",
                }[op]
                if op == "$in":
                    if not isinstance(value, list) or not value:
                        raise TypeError("IN expects a non-empty list")
                    coerced = [_coerce_value(field_types[field], v) for v in value]
                    placeholders = ", ".join(["?"] * len(coerced))
                    clauses.append(f"{field} IN ({placeholders})")
                    params.extend(coerced)
                else:
                    coerced = _coerce_value(field_types[field], value)
                    clauses.append(f"{field} {sql_op} ?")
                    params.append(coerced)
        else:
            coerced = _coerce_value(field_types[field], spec)
            clauses.append(f"{field} = ?")
            params.append(coerced)
    return " WHERE " + " AND ".join(clauses), params


def _request_body_snapshot() -> dict | None:
    try:
        json_body = request.get_json(silent=True)
    except Exception:
        json_body = None
    if json_body is not None:
        return {"type": "json", "value": json_body}

    data = request.get_data(cache=True, as_text=True)
    if not data:
        return None
    max_len = 4000
    if len(data) > max_len:
        data = data[:max_len] + "...<truncated>"
    return {"type": "text", "value": data}


def _log_request() -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "method": request.method,
            "path": request.path,
            "url": request.url,
            "query": request.args.to_dict(flat=False),
            "remote_addr": request.remote_addr,
            "x_forwarded_for": request.headers.get("X-Forwarded-For"),
            "user_agent": str(request.user_agent),
            "content_type": request.content_type,
            "content_length": request.content_length,
            "referrer": request.referrer,
            "origin": request.headers.get("Origin"),
            "headers": dict(request.headers),
            "body": _request_body_snapshot(),
        }
        with REQUEST_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # Never fail a request because logging failed.
        pass


@app.before_request
def _log_incoming_request():
    _log_request()


@app.after_request
def _log_response(response):
    _logger().info("%s %s -> %s", request.method, request.path, response.status_code)
    return response


@app.errorhandler(404)
def _handle_not_found(error):
    _logger().warning("404 Not Found: %s %s", request.method, request.path)
    return jsonify({"error": "Not found", "code": 404}), 404


@app.errorhandler(Exception)
def _handle_exception(error):
    _logger().exception("Unhandled error: %s %s", request.method, request.path)
    return jsonify({"error": "Internal server error", "code": 500}), 500


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/demo/<crawler_name>")
def quick_query(crawler_name: str):
    resources = _load_resources()
    valid = set(resources.get("collections", {}).keys())
    if crawler_name not in valid:
        return jsonify({"error": "Unknown crawler demo", "code": 404}), 404
    return render_template(f"{crawler_name}.html")


@app.get("/schemas")
def list_schemas():
    schema_files = sorted((ROOT_DIR / "src").glob("_*/schema.py"))
    names = [p.parent.name for p in schema_files]
    return jsonify({"data": names, "metadata": {"count": len(names)}})


@app.get("/v1/collections")
def list_collections():
    resources = _load_resources()
    collections = sorted(resources.get("collections", {}).keys())
    return jsonify({"data": collections, "metadata": {"count": len(collections)}})


@app.post("/v1/collections/<name>/search")
def search_collection(name: str):
    try:
        payload = request.get_json(force=True) or {}
        resources = _load_resources()
        collection = resources.get("collections", {}).get(name)
        if not collection:
            return jsonify({"error": "Resource not found", "code": 404}), 404

        db_path = ROOT_DIR / collection["db_path"]
        schema_name = collection["schema"]
        select_fields = payload.get("select", ["*"])
        flt = payload.get("filter", {})
        order_by = payload.get("order_by", [])
        limit = _query_limit()
        offset = int(payload.get("offset", 0))
        if offset < 0:
            raise ValueError("offset must be >= 0")

        schema = _load_schema(schema_name)
        if select_fields != ["*"]:
            for f in select_fields:
                _validate_field(schema, f)
            select_sql = ", ".join(select_fields)
        else:
            select_sql = ", ".join(schema.field_names())

        page_number = int(payload.get("page_number", 1))
        if page_number < 1:
            raise ValueError("page_number must be >= 1")
        limit = 5
        offset = (page_number - 1) * limit

        where_sql, params = _build_where_from_filter(schema, flt)
        order_sql = _build_order_by(schema, order_by)

        sql = (
            f"SELECT {select_sql} FROM {schema.table}{where_sql}{order_sql} "
            f"LIMIT {limit} OFFSET {offset};"
        )

        conn = sqlite3.connect(str(db_path))
        conn.execute(schema.create_table_sql())
        for stmt in schema.create_indexes_sql():
            conn.execute(stmt)

        cur = conn.execute(sql, params)
        rows_data = cur.fetchall()
        col_names = [d[0] for d in cur.description] if cur.description else []
        conn.close()

        def normalize(row: dict) -> dict:
            if "crawled_at" in row and (row["crawled_at"] is None or str(row["crawled_at"]).strip().lower() in {"", "null", "none"}):
                row["crawled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return row

        return jsonify(
            {
                "data": [normalize(dict(zip(col_names, r))) for r in rows_data],
                "metadata": {
                    "count": len(rows_data),
                    "limit": limit,
                    "offset": offset,
                },
            }
        )
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({"error": str(exc), "code": 400}), 400
    except sqlite3.OperationalError as exc:
        return jsonify({"error": str(exc), "code": 500}), 500
    except Exception as exc:
        return jsonify({"error": "Internal server error", "details": str(exc), "code": 500}), 500


if __name__ == "__main__":
    _setup_server_logging()
    host = os.environ["API_HOST"]
    port = int(os.environ["API_PORT"])
    debug = os.environ["API_DEBUG"].lower() in {"1", "true", "yes", "on"}
    app.run(host=host, port=port, debug=debug)
