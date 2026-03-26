from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
import time
from collections import defaultdict, deque
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

# ── Rate limiting ──────────────────────────────────────────────────────────────
RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", 1000))  # per window
RATE_LIMIT_WINDOW   = int(os.environ.get("RATE_LIMIT_WINDOW",   60))    # seconds
RATE_LIMITED_IPS_PATH = LOG_DIR / "rate_limited_ips.txt"

# in-memory store: ip -> deque of request timestamps
_rate_store: dict[str, deque] = defaultdict(deque)


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


def _ensure_location_column(conn: sqlite3.Connection) -> None:
    cols = [r[1] for r in conn.execute("PRAGMA table_info(items);").fetchall()]
    if "location" not in cols:
        conn.execute("ALTER TABLE items ADD COLUMN location TEXT;")
        if "neighborhood" in cols:
            conn.execute(
                "UPDATE items SET location = neighborhood "
                "WHERE location IS NULL OR TRIM(location) = '';"
            )


def _field_type_map(schema) -> dict[str, str]:
    return {f.name: f.type for f in schema.fields}


def _validate_field(schema, field: str) -> None:
    if field not in schema.field_names():
        raise ValueError(f"Unknown field: {field}")


def _coerce_value(field_type: str, value: Any) -> Any:
    if value is None:
        return None
    if field_type == "INTEGER":
        if isinstance(value, bool):
            raise TypeError("Expected INTEGER")
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            text = value.strip()
            if text.lstrip("-").isdigit():
                return int(text)
        raise TypeError("Expected INTEGER")
    if field_type == "REAL":
        if isinstance(value, bool):
            raise TypeError("Expected REAL")
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            text = value.strip()
            try:
                return float(text)
            except Exception:
                pass
        raise TypeError("Expected REAL")
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


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.min
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue
    return datetime.min


def _normalize_str_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        items = [x.strip() for x in value.split(",")]
        return [x for x in items if x]
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return []


def _build_jobs_where(
    keyword: str,
    country: str,
    state: str,
    cities: list[str],
    text_fields: list[str],
    city_field: str = "city",
    state_field: str = "state",
    country_field: str = "country",
) -> tuple[str, list]:
    clauses = []
    params: list[Any] = []

    if country:
        clauses.append(f"{country_field} = ?")
        params.append(country)
    if state:
        clauses.append(f"{state_field} = ?")
        params.append(state)
    if cities:
        placeholders = ", ".join(["?"] * len(cities))
        clauses.append(f"{city_field} IN ({placeholders})")
        params.extend(cities)
    if keyword:
        like = f"%{keyword.lower()}%"
        text_clause = " OR ".join([f"LOWER({f}) LIKE ?" for f in text_fields])
        clauses.append(f"({text_clause})")
        params.extend([like] * len(text_fields))

    if not clauses:
        return "", []
    return " WHERE " + " AND ".join(clauses), params


def _merge_where(
    where_a: str,
    params_a: list[Any],
    where_b: str,
    params_b: list[Any],
) -> tuple[str, list[Any]]:
    clauses = []
    if where_a:
        clauses.append(where_a.replace(" WHERE ", "", 1))
    if where_b:
        clauses.append(where_b.replace(" WHERE ", "", 1))
    if not clauses:
        return "", []
    return " WHERE " + " AND ".join(clauses), params_a + params_b


def _has_missing_fields(schema, where: list[dict]) -> bool:
    if not where:
        return False
    schema_fields = set(schema.field_names())
    for w in where:
        field = w.get("field")
        if field and field not in schema_fields:
            return True
    return False


def _query_rows(
    db_path: Path,
    schema_name: str,
    sql: str,
    params: list[Any],
    ensure_location: bool = False,
) -> list[dict]:
    schema = _load_schema(schema_name)
    conn = sqlite3.connect(str(db_path))
    conn.execute(schema.create_table_sql())
    for stmt in schema.create_indexes_sql():
        conn.execute(stmt)
    if ensure_location:
        _ensure_location_column(conn)
    cur = conn.execute(sql, params)
    rows_data = cur.fetchall()
    col_names = [d[0] for d in cur.description] if cur.description else []
    conn.close()
    return [dict(zip(col_names, r)) for r in rows_data]


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


def _client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _log_rate_limited_ip(ip: str) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with RATE_LIMITED_IPS_PATH.open("a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now().isoformat(timespec='seconds')} {ip}\n")
    except Exception:
        pass


def _check_rate_limit() -> Response | None:
    ip = _client_ip()
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    q = _rate_store[ip]
    # Drop timestamps outside the window
    while q and q[0] < window_start:
        q.popleft()
    if len(q) >= RATE_LIMIT_REQUESTS:
        _log_rate_limited_ip(ip)
        return jsonify({"error": "Rate limit exceeded", "code": 429}), 429
    q.append(now)
    return None


@app.before_request
def _log_incoming_request():
    rate_limit_response = _check_rate_limit()
    if rate_limit_response is not None:
        return rate_limit_response
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
    template_path = ROOT_DIR / "templates" / f"{crawler_name}.html"
    if not template_path.exists():
        return jsonify({"error": "Unknown crawler demo", "code": 404}), 404
    return render_template(f"{crawler_name}.html")


@app.get("/analysis/jobs")
def analysis_jobs():
    field_sets: list[set[str]] = []
    for mod in ("_craigslist_jobs", "_canadian_jobbank", "_workbc_jobs", "_saskjobs", "_eluta_jobs", "_charityvillage_jobs"):
        try:
            field_sets.append(set(_load_schema(mod).field_names()))
        except ModuleNotFoundError:
            continue
    field_options = sorted(set().union(*field_sets)) if field_sets else []
    return render_template("analysis/jobs.html", field_options=field_options)


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
        _ensure_location_column(conn)

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


@app.post("/analysis/jobs/search")
def analysis_jobs_search():
    try:
        payload = request.get_json(force=True) or {}

        keyword = str(payload.get("keyword", "")).strip()
        country = str(payload.get("country", "")).strip()
        state = str(payload.get("state", "")).strip()
        cities = _normalize_str_list(payload.get("cities"))
        where = payload.get("where") or []

        sources_raw = _normalize_str_list(payload.get("sources")) or ["craigslist", "jobbank"]
        sources = {s.lower() for s in sources_raw}

        order_dir = str(payload.get("order_dir", "desc")).lower()
        if order_dir not in {"asc", "desc"}:
            raise ValueError("order_dir must be 'asc' or 'desc'")

        limit = int(payload.get("limit", 200))
        offset = int(payload.get("offset", 0))
        if limit < 1:
            raise ValueError("limit must be >= 1")
        if offset < 0:
            raise ValueError("offset must be >= 0")
        limit = min(limit, 2000)
        per_source_limit = min(limit + offset, 5000)

        results: list[dict] = []
        source_counts: dict[str, int] = {}

        if "craigslist" in sources:
            schema = _load_schema("_craigslist_jobs")
            if _has_missing_fields(schema, where):
                source_counts["craigslist"] = 0
            else:
                where_sql, params = _build_jobs_where(
                    keyword=keyword,
                    country=country,
                    state=state,
                    cities=cities,
                    text_fields=["title", "company", "location"],
                )
                extra_where_sql, extra_params = _build_where(schema, where)
                where_sql, params = _merge_where(where_sql, params, extra_where_sql, extra_params)
                sql = (
                    "SELECT id, title, company, location AS location, posted_date, pay, url, "
                    "city, state, country, NULL AS work_mode, NULL AS is_lmia, NULL AS is_direct_apply "
                    f"FROM items{where_sql} ORDER BY posted_date {order_dir.upper()} LIMIT ?;"
                )
                params = params + [per_source_limit]
                rows = _query_rows(
                    db_path=ROOT_DIR / "src" / "_craigslist_jobs" / "database.sqlite",
                    schema_name="_craigslist_jobs",
                    sql=sql,
                    params=params,
                    ensure_location=True,
                )
                for r in rows:
                    r["source"] = "Craigslist Jobs"
                    r["collection"] = "_craigslist_jobs"
                    results.append(r)
                source_counts["craigslist"] = len(rows)

        if "jobbank" in sources or "canadian_jobbank" in sources:
            schema = _load_schema("_canadian_jobbank")
            if _has_missing_fields(schema, where):
                source_counts["jobbank"] = 0
            else:
                where_sql, params = _build_jobs_where(
                    keyword=keyword,
                    country=country,
                    state=state,
                    cities=cities,
                    text_fields=["title", "company", "location_raw"],
                )
                extra_where_sql, extra_params = _build_where(schema, where)
                where_sql, params = _merge_where(where_sql, params, extra_where_sql, extra_params)
                sql = (
                    "SELECT id, title, company, location_raw AS location, posted_date, pay, url, "
                    "city, state, country, work_mode, is_lmia, is_direct_apply "
                    f"FROM items{where_sql} ORDER BY posted_date {order_dir.upper()} LIMIT ?;"
                )
                params = params + [per_source_limit]
                rows = _query_rows(
                    db_path=ROOT_DIR / "src" / "_canadian_jobbank" / "database.sqlite",
                    schema_name="_canadian_jobbank",
                    sql=sql,
                    params=params,
                )
                for r in rows:
                    r["source"] = "Canadian Job Bank"
                    r["collection"] = "_canadian_jobbank"
                    results.append(r)
                source_counts["jobbank"] = len(rows)

        if "workbc" in sources or "workbc_jobs" in sources:
            try:
                schema = _load_schema("_workbc_jobs")
            except ModuleNotFoundError:
                source_counts["workbc"] = 0
                schema = None
            if schema is None:
                pass
            elif _has_missing_fields(schema, where):
                source_counts["workbc"] = 0
            else:
                where_sql, params = _build_jobs_where(
                    keyword=keyword,
                    country=country,
                    state=state,
                    cities=cities,
                    text_fields=["title", "company", "location_raw"],
                    state_field="province",
                )
                extra_where_sql, extra_params = _build_where(schema, where)
                where_sql, params = _merge_where(where_sql, params, extra_where_sql, extra_params)
                sql = (
                    "SELECT id, title, company, location_raw AS location, posted_date, NULL AS pay, url, "
                    "city, province AS state, country, work_mode, NULL AS is_lmia, NULL AS is_direct_apply "
                    f"FROM items{where_sql} ORDER BY posted_date {order_dir.upper()} LIMIT ?;"
                )
                params = params + [per_source_limit]
                rows = _query_rows(
                    db_path=ROOT_DIR / "src" / "_workbc_jobs" / "database.sqlite",
                    schema_name="_workbc_jobs",
                    sql=sql,
                    params=params,
                )
                for r in rows:
                    r["source"] = "WorkBC"
                    r["collection"] = "_workbc_jobs"
                    results.append(r)
                source_counts["workbc"] = len(rows)

        if "saskjobs" in sources:
            try:
                schema = _load_schema("_saskjobs")
            except ModuleNotFoundError:
                source_counts["saskjobs"] = 0
                schema = None
            if schema is None:
                pass
            elif _has_missing_fields(schema, where):
                source_counts["saskjobs"] = 0
            else:
                where_sql, params = _build_jobs_where(
                    keyword=keyword,
                    country=country,
                    state=state,
                    cities=cities,
                    text_fields=["title", "company", "location_raw"],
                    state_field="province",
                )
                extra_where_sql, extra_params = _build_where(schema, where)
                where_sql, params = _merge_where(where_sql, params, extra_where_sql, extra_params)
                sql = (
                    "SELECT id, title, company, location_raw AS location, posted_date, NULL AS pay, url, "
                    "city, province AS state, country, NULL AS work_mode, NULL AS is_lmia, NULL AS is_direct_apply "
                    f"FROM items{where_sql} ORDER BY posted_date {order_dir.upper()} LIMIT ?;"
                )
                params = params + [per_source_limit]
                rows = _query_rows(
                    db_path=ROOT_DIR / "src" / "_saskjobs" / "database.sqlite",
                    schema_name="_saskjobs",
                    sql=sql,
                    params=params,
                )
                for r in rows:
                    r["source"] = "SaskJobs"
                    r["collection"] = "_saskjobs"
                    results.append(r)
                source_counts["saskjobs"] = len(rows)

        if "eluta" in sources or "eluta_jobs" in sources:
            try:
                schema = _load_schema("_eluta_jobs")
            except ModuleNotFoundError:
                source_counts["eluta"] = 0
                schema = None
            if schema is None:
                pass
            elif _has_missing_fields(schema, where):
                source_counts["eluta"] = 0
            else:
                where_sql, params = _build_jobs_where(
                    keyword=keyword,
                    country=country,
                    state=state,
                    cities=cities,
                    text_fields=["title", "company", "location_raw"],
                    state_field="province",
                )
                extra_where_sql, extra_params = _build_where(schema, where)
                where_sql, params = _merge_where(where_sql, params, extra_where_sql, extra_params)
                sql = (
                    "SELECT id, title, company, location_raw AS location, posted_relative AS posted_date, "
                    "NULL AS pay, url, city, province AS state, country, work_mode, "
                    "NULL AS is_lmia, NULL AS is_direct_apply "
                    f"FROM items{where_sql} ORDER BY posted_relative {order_dir.upper()} LIMIT ?;"
                )
                params = params + [per_source_limit]
                rows = _query_rows(
                    db_path=ROOT_DIR / "src" / "_eluta_jobs" / "database.sqlite",
                    schema_name="_eluta_jobs",
                    sql=sql,
                    params=params,
                )
                for r in rows:
                    r["source"] = "Eluta"
                    r["collection"] = "_eluta_jobs"
                    results.append(r)
                source_counts["eluta"] = len(rows)

        if "charityvillage" in sources or "charityvillage_jobs" in sources:
            try:
                schema = _load_schema("_charityvillage_jobs")
            except ModuleNotFoundError:
                source_counts["charityvillage"] = 0
                schema = None
            if schema is None:
                pass
            elif _has_missing_fields(schema, where):
                source_counts["charityvillage"] = 0
            else:
                where_sql, params = _build_jobs_where(
                    keyword=keyword,
                    country=country,
                    state=state,
                    cities=cities,
                    text_fields=["title", "company", "location_raw"],
                    state_field="province",
                )
                extra_where_sql, extra_params = _build_where(schema, where)
                where_sql, params = _merge_where(where_sql, params, extra_where_sql, extra_params)
                sql = (
                    "SELECT id, title, company, location_raw AS location, posted_date, NULL AS pay, url, "
                    "city, province AS state, country, work_mode, NULL AS is_lmia, NULL AS is_direct_apply "
                    f"FROM items{where_sql} ORDER BY posted_date {order_dir.upper()} LIMIT ?;"
                )
                params = params + [per_source_limit]
                rows = _query_rows(
                    db_path=ROOT_DIR / "src" / "_charityvillage_jobs" / "database.sqlite",
                    schema_name="_charityvillage_jobs",
                    sql=sql,
                    params=params,
                )
                for r in rows:
                    r["source"] = "CharityVillage"
                    r["collection"] = "_charityvillage_jobs"
                    results.append(r)
                source_counts["charityvillage"] = len(rows)

        results.sort(
            key=lambda r: _parse_dt(str(r.get("posted_date") or "")),
            reverse=(order_dir == "desc"),
        )

        total = len(results)
        page = results[offset: offset + limit]

        return jsonify({
            "data": page,
            "metadata": {
                "count": total,
                "returned": len(page),
                "limit": limit,
                "offset": offset,
                "sources": source_counts,
            },
        })
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({"error": str(exc), "code": 400}), 400
    except sqlite3.OperationalError as exc:
        return jsonify({"error": str(exc), "code": 500}), 500
    except Exception as exc:
        return jsonify({"error": "Internal server error", "details": str(exc), "code": 500}), 500


@app.get("/v1/collections/<name>/freshness")
def collection_freshness(name: str):
    try:
        resources = _load_resources()
        collection = resources.get("collections", {}).get(name)
        if not collection:
            return jsonify({"error": "Resource not found", "code": 404}), 404

        db_path = ROOT_DIR / collection["db_path"]
        schema_name = collection["schema"]
        schema = _load_schema(schema_name)

        conn = sqlite3.connect(str(db_path))
        conn.execute(schema.create_table_sql())
        for stmt in schema.create_indexes_sql():
            conn.execute(stmt)
        _ensure_location_column(conn)

        row = conn.execute("""
            SELECT
                COUNT(CASE WHEN date(crawled_at) = date('now') THEN 1 END)                    AS today,
                COUNT(CASE WHEN crawled_at >= datetime('now', '-7 days') THEN 1 END)           AS this_week,
                COUNT(CASE WHEN crawled_at >= datetime('now', 'start of month') THEN 1 END)    AS this_month,
                COUNT(CASE WHEN crawled_at >= datetime('now', 'start of year') THEN 1 END)     AS this_year,
                COUNT(*)                                                                        AS total
            FROM items;
        """).fetchone()
        conn.close()

        return jsonify({
            "data": {
                "today":      row[0],
                "this_week":  row[1],
                "this_month": row[2],
                "this_year":  row[3],
                "total":      row[4],
            }
        })
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
