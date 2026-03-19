from __future__ import annotations

import json
import logging
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR      = Path(__file__).resolve().parents[2]
SRC_DIR       = ROOT_DIR / "src"
TEMPLATES_DIR = ROOT_DIR / "templates"
sys.path.insert(0, str(SRC_DIR))


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def _derive_module_name(source_name: str) -> str:
    """Ensure module name starts with _ and uses underscores."""
    name = source_name.replace("-", "_").lower()
    return name if name.startswith("_") else f"_{name}"


def _derive_class_name(module_name: str) -> str:
    parts = [p for p in module_name.lstrip("_").split("_") if p]
    return "".join(p.capitalize() for p in parts) + "Crawler"


def _derive_jsonify_class_name(module_name: str) -> str:
    parts = [p for p in module_name.lstrip("_").split("_") if p]
    return "".join(p.capitalize() for p in parts) + "Jsonify"


def _crawler_dir(module_name: str) -> Path:
    return SRC_DIR / module_name


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _ensure_collection(
    resources_path: Path, collection: str, schema: str, db_path: str
) -> None:
    data = _load_json(resources_path)
    collections = data.get("collections", {})
    if collection not in collections:
        collections[collection] = {"db_path": db_path, "schema": schema}
        data["collections"] = collections
        _write_json(resources_path, data)


# ── Field helpers ──────────────────────────────────────────────────────────────

def _all_fields(extra_fields: list[dict]) -> list[dict]:
    """Return the full ordered field list: id, [extra_fields], crawled_at.
    Only id and crawled_at are always included — everything else must be passed in."""
    base_leading: list[dict] = [
        {"name": "id", "type": "TEXT", "primary": True, "description": "Unique listing identifier"},
    ]
    base_trailing: list[dict] = [
        {"name": "crawled_at", "type": "TEXT", "indexed": True, "default_sql": "CURRENT_TIMESTAMP", "description": "Timestamp when row was ingested"},
    ]
    return base_leading + list(extra_fields) + base_trailing


def _field_to_python(f: dict) -> str:
    """Return a Field(...) constructor line for schema.py."""
    name  = f["name"]
    ftype = f["type"]
    kwargs: list[str] = []
    if f.get("primary"):
        kwargs.append("primary=True")
    if f.get("unique"):
        kwargs.append("unique=True")
    if f.get("indexed"):
        kwargs.append("indexed=True")
    if f.get("default_sql"):
        kwargs.append(f'default_sql="{f["default_sql"]}"')
    kw = ", ".join(kwargs)
    return f'        Field("{name}", "{ftype}"{", " + kw if kw else ""}),'


def _pick_example_fields(extra_fields: list[dict]) -> dict:
    """Pick representative fields from the schema for HTML examples."""
    int_field  = next((f for f in extra_fields if f["type"] == "INTEGER"), None)
    text_field = next((f for f in extra_fields if f["type"] == "TEXT"),    None)
    loc_field  = next((f for f in extra_fields if f.get("location")),      text_field)
    idx_field  = next((f for f in extra_fields if f.get("indexed")),       extra_fields[0] if extra_fields else None)
    return {"int": int_field, "text": text_field, "loc": loc_field, "idx": idx_field}


def _make_filter_lines(extra_fields: list[dict]) -> list[str]:
    """Build a rich multi-operator filter block for the HTML code example."""
    def _kv(key, val):
        return f'        <span class="ckey">"{key}"</span><span class="cop">:</span> {val},'
    def _cs(s):
        return f'<span class="cs">"{s}"</span>'
    def _cn(n):
        return f'<span class="cn">{n}</span>'
    def _op(o):
        return f'<span class="cs">"{o}"</span><span class="cop">:</span>'
    def _range(lo, hi):
        return f'{{{_op("$gte")} {_cn(lo)}, {_op("$lte")} {_cn(hi)}}}'
    def _gte(v):
        return f'{{{_op("$gte")} {_cn(v)}}}'
    def _lt(v):
        return f'{{{_op("$lt")} {_cn(v)}}}'
    def _like(s):
        return f'{{{_op("$like")} {_cs(s)}}}'
    def _in(*vals):
        return f'{{{_op("$in")} [{", ".join(_cs(v) for v in vals)}]}}'

    int_fields  = [f for f in extra_fields if f["type"] == "INTEGER"]
    text_nonloc = [f for f in extra_fields if f["type"] == "TEXT"
                   and not f.get("location") and not f.get("unique") and f["name"] != "id"]
    loc_fields  = [f for f in extra_fields if f.get("location")]

    lines: list[str] = []

    # Country as simple equality
    country_f = next((f for f in loc_fields if "country" in f["name"]), None)
    if country_f:
        lines.append(_kv(country_f["name"], _cs("United States")))

    # Integer fields — first gets a range, second gets single-bound, third gets $lt
    for i, f in enumerate(int_fields[:3]):
        n  = f["name"]
        nl = n.lower()
        if i == 0:
            if any(k in nl for k in ("price", "cost", "amount", "wage", "salary")):
                lines.append(_kv(n, _range(1000, 15000)))
            elif any(k in nl for k in ("year", "date")):
                lines.append(_kv(n, _range(2010, 2024)))
            else:
                lines.append(_kv(n, _range(0, 100)))
        elif i == 1:
            if any(k in nl for k in ("mile", "odo", "dist")):
                lines.append(_kv(n, _lt(150000)))
            elif any(k in nl for k in ("year",)):
                lines.append(_kv(n, _gte(2010)))
            else:
                lines.append(_kv(n, _gte(0)))
        else:
            lines.append(_kv(n, _lt(100)))

    # Non-location, non-unique text field → $like
    if text_nonloc:
        n  = text_nonloc[0]["name"]
        nl = n.lower()
        kw = "keyword"
        lines.append(_kv(n, _like(f"%{kw}%")))

    # State/province as $in
    state_f = next(
        (f for f in loc_fields if f is not country_f
         and any(k in f["name"] for k in ("state", "province", "region"))),
        None,
    )
    city_f = next(
        (f for f in loc_fields if f is not country_f and "city" in f["name"]),
        None,
    )
    if state_f:
        lines.append(_kv(state_f["name"], _in("Texas", "California")))
    elif city_f:
        lines.append(_kv(city_f["name"], _in("New York", "Los Angeles")))

    if not lines:
        lines.append('        <span class="cc"># add filters here</span>')

    return lines


# ── File writers ───────────────────────────────────────────────────────────────

def _write_init(module_name: str) -> None:
    path = _crawler_dir(module_name) / "__init__.py"
    if not path.exists():
        path.write_text("", encoding="utf-8")


def _write_crawler_stub(module_name: str, class_name: str) -> None:
    path = _crawler_dir(module_name) / "crawler.py"
    if path.exists():
        raise FileExistsError(f"Already exists: {path}")
    path.write_text(
        f'"""Crawler for {module_name}."""\n'
        "from __future__ import annotations\n\n\n"
        f"class {class_name}:\n"
        f'    def __init__(self, name: str = "{module_name}"):\n'
        "        self.name = name\n\n"
        "    def run(self) -> None:\n"
        "        # TODO: implement\n"
        f'        print(f"[{{self.name}}] stub_run")\n\n\n'
        'if __name__ == "__main__":\n'
        f'    {class_name}().run()\n',
        encoding="utf-8",
    )


def _write_schema_stub(module_name: str, extra_fields: list[dict]) -> None:
    path = _crawler_dir(module_name) / "schema.py"
    if path.exists():
        raise FileExistsError(f"Already exists: {path}")
    fields      = _all_fields(extra_fields)
    field_lines = "\n".join(_field_to_python(f) for f in fields)
    path.write_text(
        f'"""Schema for {module_name}."""\n'
        "from __future__ import annotations\n\n"
        "from dataclasses import dataclass\n"
        "from typing import List\n\n\n"
        "@dataclass(frozen=True)\n"
        "class Field:\n"
        "    name: str\n"
        "    type: str\n"
        "    primary: bool = False\n"
        "    indexed: bool = False\n"
        "    unique: bool = False\n"
        "    default_sql: str | None = None\n\n\n"
        "class Schema:\n"
        "    def __init__(self, table: str, fields: List[Field]):\n"
        "        self.table = table\n"
        "        self.fields = fields\n\n"
        "    def create_table_sql(self) -> str:\n"
        "        cols = []\n"
        "        for f in self.fields:\n"
        '            col = f"{f.name} {f.type}"\n'
        "            if f.primary: col += \" PRIMARY KEY\"\n"
        "            if f.unique:  col += \" UNIQUE\"\n"
        '            if f.default_sql: col += f" DEFAULT {f.default_sql}"\n'
        "            cols.append(col)\n"
        '        return f"CREATE TABLE IF NOT EXISTS {self.table} ({\', \'.join(cols)});"\n\n'
        "    def create_indexes_sql(self) -> List[str]:\n"
        "        return [\n"
        '            f"CREATE INDEX IF NOT EXISTS idx_{self.table}_{f.name} ON {self.table}({f.name});"\n'
        "            for f in self.fields if f.indexed and not f.primary\n"
        "        ]\n\n"
        "    def field_names(self) -> List[str]:\n"
        "        return [f.name for f in self.fields]\n\n\n"
        "SCHEMA = Schema(\n"
        '    table="items",\n'
        "    fields=[\n"
        f"{field_lines}\n"
        "    ],\n"
        ")\n",
        encoding="utf-8",
    )


def _write_jsonify_stub(module_name: str, class_name: str) -> None:
    path = _crawler_dir(module_name) / "jsonify.py"
    if path.exists():
        raise FileExistsError(f"Already exists: {path}")
    path.write_text(
        f'"""Jsonify for {module_name}."""\n'
        "from __future__ import annotations\n\n"
        "from typing import Any, List\n\n\n"
        f"class {class_name}:\n"
        f'    def __init__(self, source_name: str = "{module_name}"):\n'
        "        self.source_name = source_name\n\n"
        "    def to_json(self, data: Any, location: dict | None = None) -> List[dict]:\n"
        "        # TODO: convert scraped rows into dicts.\n"
        "        # Stamp each record with location data if provided:\n"
        "        loc_city    = (location or {}).get('city', '')\n"
        "        loc_state   = (location or {}).get('state', '')\n"
        "        loc_country = (location or {}).get('country', '')\n"
        "        return data if isinstance(data, list) else []\n",
        encoding="utf-8",
    )


def _build_json_schema(extra_fields: list[dict]) -> dict:
    """Build a RapidAPI-ready JSON Schema dict from extra_fields."""
    type_map = {"INTEGER": "integer", "REAL": "number", "TEXT": "string"}
    all_fields = _all_fields(extra_fields)
    filter_props = {}
    for f in all_fields:
        if f.get("primary"):
            continue
        filter_props[f["name"]] = {
            "type": type_map.get(f["type"], "string"),
            "description": f.get("description", f["name"].replace("_", " ").capitalize()),
        }
    return {
        "type": "object",
        "properties": {
            "select": {
                "type": "array",
                "items": {"type": "string"},
                "description": 'Fields to return. Use ["*"] for all fields.',
            },
            "filter": {
                "type": "object",
                "description": "Field filters. Supported operators: $gte, $lte, $gt, $lt, $eq, $ne, $like, $in.",
                "properties": filter_props,
            },
            "order_by": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field":     {"type": "string"},
                        "direction": {"type": "string", "enum": ["asc", "desc"]},
                    },
                },
            },
            "page_number": {"type": "integer", "description": "1-based page number."},
            "offset":      {"type": "integer", "description": "Row offset, alternative to page_number."},
        },
    }


def _build_example_body(extra_fields: list[dict]) -> dict:
    """Build a realistic example POST body from extra_fields."""
    int_fields = [f for f in extra_fields if f["type"] == "INTEGER"]
    loc_fields = [f for f in extra_fields if f.get("location")]
    state_f = next((f for f in loc_fields if any(k in f["name"] for k in ("state", "province", "region"))), None)

    filter_ex: dict = {}
    for i, f in enumerate(int_fields[:3]):
        nl = f["name"].lower()
        if i == 0:
            if any(k in nl for k in ("price", "cost", "amount", "wage", "salary")):
                filter_ex[f["name"]] = {"$gte": 1000, "$lte": 15000}
            elif any(k in nl for k in ("year", "date")):
                filter_ex[f["name"]] = {"$gte": 2010, "$lte": 2024}
            else:
                filter_ex[f["name"]] = {"$gte": 0, "$lte": 100}
        elif i == 1:
            if any(k in nl for k in ("mile", "odo", "dist")):
                filter_ex[f["name"]] = {"$lt": 150000}
            elif any(k in nl for k in ("year",)):
                filter_ex[f["name"]] = {"$gte": 2010}
            else:
                filter_ex[f["name"]] = {"$gte": 0}

    if state_f:
        filter_ex[state_f["name"]] = {"$in": ["TX", "CA"]}

    idx_f = next((f for f in extra_fields if f.get("indexed")), extra_fields[0] if extra_fields else None)
    order_field = idx_f["name"] if idx_f else "id"

    return {
        "select": ["*"],
        "filter": filter_ex,
        "order_by": [{"field": order_field, "direction": "asc"}],
        "page_number": 1,
    }


def _write_listing(
    module_name:  str,
    short_desc:   str,
    long_desc:    str,
    extra_fields: list[dict],
) -> None:
    """Write LISTING.md — title, descriptions, RapidAPI schema, and example body."""
    path = _crawler_dir(module_name) / "LISTING.md"
    if path.exists():
        return  # don't overwrite manual edits

    display_name = module_name.lstrip("_").replace("_", " ").title()
    schema_json  = json.dumps(_build_json_schema(extra_fields), indent=2)
    example_json = json.dumps(_build_example_body(extra_fields), indent=2)

    content = f"""\
# RapidAPI Listing Info — {display_name}

## API Name (short title)
```
{display_name}
```

## Short Description (one-liner shown in search results)
```
{short_desc}
```

## Long Description (shown on the API page)
```
{long_desc}
```

## Category (RapidAPI)
```
Data
```

---

## RapidAPI Body Schema (paste into Schema tab)
```json
{schema_json}
```

## RapidAPI Example Body (paste into Body tab)
```json
{example_json}
```
"""
    path.write_text(content, encoding="utf-8")


def _write_publish_stub(
    module_name: str,
    short_desc:  str = "",
    long_desc:   str = "",
) -> None:
    """Write publish.py — hyperSel-based RapidAPI publishing automation."""
    path = _crawler_dir(module_name) / "publish.py"
    if path.exists():
        return  # don't overwrite manual edits

    display_name = module_name.lstrip("_").replace("_", " ").title()
    collection_path = f"/v1/collections/{module_name}/search"

    path.write_text(
        f'"""RapidAPI publishing automation for {module_name}."""\n'
        "from __future__ import annotations\n\n"
        "import os\n"
        "from dotenv import load_dotenv\n"
        "from hyperSel import instance, log\n\n"
        "load_dotenv()\n\n"
        "# ── Crawler metadata ─────────────────────────────────────────────────────────\n"
        f'DISPLAY_NAME     = "{display_name}"\n'
        f'SHORT_DESC       = "{short_desc}"\n'
        f'LONG_DESC        = """{long_desc}"""\n'
        f'COLLECTION_PATH  = "{collection_path}"\n\n'
        "# ── Credentials (set in .env) ─────────────────────────────────────────────────\n"
        'RAPID_API_EMAIL = os.getenv("RAPID_API_EMAIL")\n'
        'RAPID_API_PASSW = os.getenv("RAPID_API_PASSW")\n\n\n"'
        "def sign_in_process(browser) -> None:\n"
        '    browser.go_to_site("https://rapidapi.com/auth/login")\n'
        '    browser.clear_and_enter_text(by_type="xpath", value=\'/html/body/div[2]/main/div[1]/section/section/form/div[1]/div/input\', content_to_enter=RAPID_API_EMAIL)\n'
        '    browser.clear_and_enter_text(by_type="xpath", value=\'/html/body/div[2]/main/div[1]/section/section/form/div[2]/div/div/input\', content_to_enter=RAPID_API_PASSW)\n'
        '    browser.click_element(by_type="xpath", value=\'/html/body/div[2]/main/div[1]/section/section/button\')\n'
        "    # accept cookies popup\n"
        '    browser.click_element(by_type="xpath", value=\'/html/body/div[4]/div[2]/div/div/div[2]/div/div/button[2]\')\n'
        '    print("SIGN IN SUCCESSFUL")\n\n\n'
        "def uploading_new_process(browser) -> None:\n"
        "    def creation_process():\n"
        "        # TODO: click Workspace\n"
        "        # TODO: click Create New Project\n"
        "        # TODO: enter DISPLAY_NAME\n"
        "        # TODO: enter SHORT_DESC\n"
        "        # TODO: select category = Data\n"
        "        # TODO: click Add API Project\n"
        "        pass\n\n"
        "    def general_process():\n"
        "        # TODO: upload logo (logo.png lives next to this file)\n"
        "        # TODO: add LONG_DESC\n"
        "        # TODO: add website link\n"
        "        # TODO: tick 'I confirm I own or have rights'\n"
        "        # TODO: add base URL  http://<your-server>:5000/\n"
        "        pass\n\n"
        "    def create_rest_endpoint():\n"
        "        # TODO: click Create REST Endpoint\n"
        "        # TODO: set name = DISPLAY_NAME\n"
        "        # TODO: set description (payload desc)\n"
        "        # TODO: set method = POST\n"
        f"        # TODO: set path = {collection_path}\n"
        "        # TODO: set payload name = body\n"
        "        # TODO: paste example body from LISTING.md\n"
        "        # TODO: paste schema JSON from LISTING.md\n"
        "        # TODO: click Save\n"
        "        pass\n\n"
        "    creation_process()\n"
        "    general_process()\n"
        "    create_rest_endpoint()\n\n\n"
        "def main() -> None:\n"
        "    browser = instance.Browser(headless=False, zoom_level=100)\n"
        "    browser.init_browser()\n"
        "    sign_in_process(browser)\n"
        "    uploading_new_process(browser)\n"
        '    input("Paused — press Enter to close browser")\n\n\n'
        'if __name__ == "__main__":\n'
        "    main()\n",
        encoding="utf-8",
    )


def _write_demo_data_stub(module_name: str) -> None:
    path = _crawler_dir(module_name) / "demo_data.py"
    if path.exists():
        raise FileExistsError(f"Already exists: {path}")
    path.write_text(
        f'"""Demo data for {module_name}."""\n\n'
        "DEMO_DATA = []\n",
        encoding="utf-8",
    )



def _schema_table_rows(fields: list[dict]) -> str:
    """Generate HTML <tr> rows for the schema table."""
    rows = []
    for f in fields:
        name = f["name"]
        ftype = f["type"]
        desc  = f.get("description", name.replace("_", " ").capitalize())
        tags  = []
        if f.get("primary"):
            tags.append('<span class="ftag ftag-pk">PK</span>')
        if f.get("unique"):
            tags.append('<span class="ftag ftag-uniq">unique</span>')
        if f.get("location"):
            tags.append('<span class="ftag ftag-loc">location</span>')
        if f.get("indexed"):
            tags.append('<span class="ftag ftag-idx">indexed</span>')
        inner       = "".join(tags)
        constraints = f'<div class="field-tags">{inner}</div>' if tags else ""
        rows.append(
            f"    <tr>\n"
            f'      <td><span class="field-name">{name}</span></td>\n'
            f'      <td><span class="field-type">{ftype}</span></td>\n'
            f'      <td class="field-desc">{desc}</td>\n'
            f"      <td>{constraints}</td>\n"
            f"    </tr>"
        )
    return "\n".join(rows)


def _write_html_template(
    module_name:  str,
    extra_fields: list[dict],
    long_desc:    str = "",
) -> None:
    """Generate templates/{module_name}.html styled like _craigslist_cars.html."""
    path = TEMPLATES_DIR / f"{module_name}.html"
    if path.exists():
        raise FileExistsError(f"Already exists: {path}")

    fields      = _all_fields(extra_fields)
    schema_rows = _schema_table_rows(fields)
    ex          = _pick_example_fields(extra_fields)

    hero_desc    = long_desc if long_desc else f"Data scraped by <strong>{module_name}</strong>."
    has_location = any(f.get("location") for f in extra_fields)

    # Representative field names for examples — fall back to safe placeholders
    int_name  = ex["int"]["name"]  if ex["int"]  else "value"
    text_name = ex["text"]["name"] if ex["text"] else "field"
    loc_name  = ex["loc"]["name"]  if ex["loc"]  else text_name
    idx_name  = ex["idx"]["name"]  if ex["idx"]  else (extra_fields[0]["name"] if extra_fields else "field")

    filter_lines = _make_filter_lines(extra_fields)

    L: list[str] = []

    # ── Block header ───────────────────────────────────────────────────────────
    L.append("{% extends 'base.html' %}")
    L.append("{% block content %}")
    L.append("")

    # ── Hero ───────────────────────────────────────────────────────────────────
    L.append("<!-- ── HERO ──────────────────────────────────────────────── -->")
    L.append('<div class="collection-hero">')
    L.append('  <div class="collection-eyebrow">')
    L.append('    <span class="eyebrow-dot"></span>')
    L.append("    Collection · Live")
    L.append("  </div>")
    L.append(f'  <div class="collection-title">{module_name}</div>')
    L.append('  <p class="collection-desc">')
    L.append(f"    {hero_desc}")
    L.append("  </p>")
    L.append('  <div class="collection-meta">')
    L.append('    <span class="badge badge-green">● Live</span>')
    L.append('    <span class="badge badge-blue">SQLite</span>')
    if has_location:
        L.append('    <span class="badge badge-purple">geo-tagged</span>')
    L.append('    <span class="badge badge-muted">REST · POST /search</span>')
    L.append("  </div>")
    L.append("</div>")
    L.append("")

    # ── Schema ─────────────────────────────────────────────────────────────────
    L.append("<!-- ── SCHEMA ────────────────────────────────────────────── -->")
    L.append('<div class="section-label">Schema</div>')
    L.append('<table class="schema-table">')
    L.append("  <thead>")
    L.append("    <tr>")
    L.append("      <th>Field</th>")
    L.append("      <th>Type</th>")
    L.append("      <th>Description</th>")
    L.append("      <th>Constraints</th>")
    L.append("    </tr>")
    L.append("  </thead>")
    L.append("  <tbody>")
    L.append(schema_rows)
    L.append("  </tbody>")
    L.append("</table>")
    L.append("")

    # ── Filter Operators ───────────────────────────────────────────────────────
    L.append("<!-- ── FILTER OPERATORS ───────────────────────────────────── -->")
    L.append('<div class="section-label">Filter Operators</div>')
    L.append('<table class="schema-table" style="margin-bottom:44px">')
    L.append("  <thead>")
    L.append("    <tr>")
    L.append("      <th>Operator</th>")
    L.append("      <th>Meaning</th>")
    L.append("      <th>Example</th>")
    L.append("    </tr>")
    L.append("  </thead>")
    L.append("  <tbody>")
    L.append("    <tr>")
    L.append('      <td><span class="field-name">$gte</span></td>')
    L.append('      <td class="field-desc">Greater than or equal to</td>')
    L.append(f'      <td><span class="field-type">{{"{int_name}": {{"$gte": 0}}}}</span></td>')
    L.append("    </tr>")
    L.append("    <tr>")
    L.append('      <td><span class="field-name">$lte</span></td>')
    L.append('      <td class="field-desc">Less than or equal to</td>')
    L.append(f'      <td><span class="field-type">{{"{int_name}": {{"$lte": 100}}}}</span></td>')
    L.append("    </tr>")
    L.append("    <tr>")
    L.append('      <td><span class="field-name">$gt</span></td>')
    L.append('      <td class="field-desc">Strictly greater than</td>')
    L.append(f'      <td><span class="field-type">{{"{int_name}": {{"$gt": 0}}}}</span></td>')
    L.append("    </tr>")
    L.append("    <tr>")
    L.append('      <td><span class="field-name">$lt</span></td>')
    L.append('      <td class="field-desc">Strictly less than</td>')
    L.append(f'      <td><span class="field-type">{{"{int_name}": {{"$lt": 100}}}}</span></td>')
    L.append("    </tr>")
    L.append("    <tr>")
    L.append('      <td><span class="field-name">$eq</span></td>')
    L.append('      <td class="field-desc">Exact match (shorthand: pass the value directly)</td>')
    L.append(f'      <td><span class="field-type">{{"{text_name}": "example"}}</span></td>')
    L.append("    </tr>")
    L.append("    <tr>")
    L.append('      <td><span class="field-name">$ne</span></td>')
    L.append('      <td class="field-desc">Not equal to</td>')
    L.append(f'      <td><span class="field-type">{{"{text_name}": {{"$ne": "example"}}}}</span></td>')
    L.append("    </tr>")
    L.append("    <tr>")
    L.append('      <td><span class="field-name">$like</span></td>')
    L.append('      <td class="field-desc">SQL LIKE pattern match — use % as wildcard</td>')
    L.append(f'      <td><span class="field-type">{{"{text_name}": {{"$like": "%keyword%"}}}}</span></td>')
    L.append("    </tr>")
    L.append("    <tr>")
    L.append('      <td><span class="field-name">$in</span></td>')
    L.append('      <td class="field-desc">Value must be in the provided list</td>')
    L.append(f'      <td><span class="field-type">{{"{loc_name}": {{"$in": ["a", "b"]}}}}</span></td>')
    L.append("    </tr>")
    L.append("  </tbody>")
    L.append("</table>")
    L.append("")

    # ── Code Example ───────────────────────────────────────────────────────────
    L.append("<!-- ── CODE EXAMPLE ──────────────────────────────────────── -->")
    L.append('<div class="section-label">Example Request</div>')
    L.append('<div class="code-block">')
    L.append('  <div class="code-header">')
    L.append('    <div class="code-traffic">')
    L.append('      <span class="code-dot code-dot-r"></span>')
    L.append('      <span class="code-dot code-dot-y"></span>')
    L.append('      <span class="code-dot code-dot-g"></span>')
    L.append('      <span class="code-label">Python · requests</span>')
    L.append("    </div>")
    L.append('    <button class="code-copy" id="copySample">Copy</button>')
    L.append("  </div>")
    # <pre> must open on the same line — no leading newline inside the block
    L.append('  <pre class="code-body" id="sampleCode"><span class="ck">import</span> requests')
    L.append("")
    L.append('<span class="cc"># Replace these with the credentials provided by your API platform</span>')
    L.append('<span class="cc"># (e.g. RapidAPI, your own deployment, etc.)</span>')
    L.append('API_BASE_URL <span class="cop">=</span> <span class="cs">"https://&lt;your-api-host&gt;"</span>')
    L.append('API_KEY      <span class="cop">=</span> <span class="cs">"&lt;your-api-key&gt;"</span>')
    L.append("")
    L.append(
        f'url <span class="cop">=</span> '
        f'<span class="cs">f"'
        f'<span class="cop">{{</span>API_BASE_URL<span class="cop">}}</span>'
        f'/v1/collections/{module_name}/search"</span>'
    )
    L.append("")
    L.append('headers <span class="cop">=</span> {')
    L.append('    <span class="ckey">"Content-Type"</span><span class="cop">:</span>  <span class="cs">"application/json"</span>,')
    L.append('    <span class="ckey">"X-Api-Key"</span><span class="cop">:</span>     API_KEY,  <span class="cc"># header name may vary by platform</span>')
    L.append("}")
    L.append("")
    L.append('<span class="cc"># Structure the POST body however you need — all fields are optional.</span>')
    L.append('<span class="cc"># Use &quot;filter&quot; to narrow results, &quot;order_by&quot; to sort, &quot;page_number&quot; to paginate.</span>')
    L.append('payload <span class="cop">=</span> {')
    L.append('    <span class="ckey">"select"</span><span class="cop">:</span>      [<span class="cs">"*"</span>],')
    L.append('    <span class="ckey">"filter"</span><span class="cop">:</span>      {')
    for fl in filter_lines:
        L.append(fl)
    L.append("    },")
    L.append(
        f'    <span class="ckey">"order_by"</span><span class="cop">:</span>    '
        f'[{{<span class="cs">"field"</span><span class="cop">:</span> '
        f'<span class="cs">"{idx_name}"</span>, '
        f'<span class="cs">"direction"</span><span class="cop">:</span> '
        f'<span class="cs">"asc"</span>}}],'
    )
    L.append('    <span class="ckey">"page_number"</span><span class="cop">:</span> <span class="cn">1</span>,')
    L.append("}")
    L.append("")
    L.append('resp <span class="cop">=</span> requests.<span class="cf">post</span>(url, json<span class="cop">=</span>payload, headers<span class="cop">=</span>headers)')
    L.append('<span class="cf">print</span>(resp.status_code)')
    L.append('<span class="cf">print</span>(resp.<span class="cf">json</span>())</pre>')
    L.append("</div>")
    L.append("")

    # ── Live Query Tool ────────────────────────────────────────────────────────
    L.append("<!-- ── LIVE QUERY TOOL ────────────────────────────────────── -->")
    L.append('<div class="section-label">Live Query</div>')
    L.append('<div class="query-card">')
    L.append('  <div class="query-card-header">')
    L.append(f'    <span class="query-card-title">POST /v1/collections/{module_name}/search</span>')
    L.append('    <span class="badge badge-blue">Demo · 5 rows max</span>')
    L.append("  </div>")
    L.append('  <div class="query-card-body">')
    L.append('    <div class="tool-row">')
    L.append('      <button id="runQuery">&#9654; Run Query</button>')
    L.append('      <button id="clearQuery" class="secondary">Clear</button>')
    L.append("    </div>")
    L.append('    <div id="status" class="status">Idle</div>')
    L.append('    <div id="result" class="result">// Results will appear here</div>')
    L.append("  </div>")
    L.append("</div>")
    L.append("")

    # ── Inline JS ──────────────────────────────────────────────────────────────
    L.append("<script>")
    L.append("  window.quickQueryConfig = {")
    L.append(f"    collection: '{module_name}',")
    L.append("    filter: {},")
    L.append("    order_by: [],")
    L.append("  };")
    L.append("")
    L.append("  document.getElementById('copySample').addEventListener('click', function () {")
    L.append("    const raw = document.getElementById('sampleCode').innerText;")
    L.append("    navigator.clipboard.writeText(raw).then(() => {")
    L.append("      this.textContent = '\u2713 Copied';")
    L.append("      setTimeout(() => (this.textContent = 'Copy'), 1600);")
    L.append("    });")
    L.append("  });")
    L.append("</script>")
    L.append("{% endblock %}")
    L.append("")

    path.write_text("\n".join(L), encoding="utf-8")


def _insert_index_card(module_name: str, short_desc: str) -> None:
    """Insert a new <a class="card"> into templates/index.html offerings block."""
    index_path = TEMPLATES_DIR / "index.html"
    content    = index_path.read_text(encoding="utf-8")

    # Idempotency — don't double-insert
    if f"crawler_name='{module_name}'" in content:
        logging.info("Card for %s already present in index.html", module_name)
        return

    display_name = module_name.lstrip("_").replace("_", " ").title()
    href = "{{ url_for('quick_query', crawler_name='" + module_name + "') }}"
    card = (
        f'  <a class="card" href="{href}">\n'
        f'    <h3>{display_name}</h3>\n'
        f'    <p>{short_desc}</p>\n'
        f'    <div class="card-footer">\n'
        f'      <span class="card-link">View docs \u2192</span>\n'
        f'      <span class="badge badge-green">\u25cf Live</span>\n'
        f'    </div>\n'
        f'  </a>\n'
    )

    # Insert before the closing </div> of the offerings block
    marker = "</div>\n{% endblock %}"
    if marker not in content:
        raise ValueError("Could not find offerings </div> insertion point in index.html")

    content = content.replace(marker, card + marker, 1)
    index_path.write_text(content, encoding="utf-8")


def _remove_index_card(module_name: str) -> bool:
    """Remove the <a class="card"> block for module_name from index.html."""
    index_path = TEMPLATES_DIR / "index.html"
    if not index_path.exists():
        return False
    content = index_path.read_text(encoding="utf-8")
    anchor  = f"crawler_name='{module_name}'"
    if anchor not in content:
        return False
    idx   = content.index(anchor)
    start = content.rindex("  <a ", 0, idx)
    end   = content.index("  </a>", idx) + len("  </a>") + 1  # +1 eats the trailing \n
    content = content[:start] + content[end:]
    index_path.write_text(content, encoding="utf-8")
    return True


def _init_crawler_db(module_name: str, extra_fields: list[dict]) -> None:
    """Create the SQLite database with the full schema."""
    fields   = _all_fields(extra_fields)
    col_defs: list[str] = []
    for f in fields:
        col = f"{f['name']} {f['type']}"
        if f.get("primary"):
            col += " PRIMARY KEY"
        if f.get("unique"):
            col += " UNIQUE"
        if f.get("default_sql"):
            col += f" DEFAULT {f['default_sql']}"
        col_defs.append(col)
    create_sql = f"CREATE TABLE IF NOT EXISTS items ({', '.join(col_defs)});"
    path = SRC_DIR / module_name / "database.sqlite"
    conn = sqlite3.connect(str(path))
    conn.execute(create_sql)
    for f in fields:
        if f.get("indexed") and not f.get("primary"):
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_items_{f['name']} ON items({f['name']});"
            )
    conn.commit()
    conn.close()


def dedup_database(db_path: Path) -> int:
    """Delete duplicate rows sharing the same URL, keeping the oldest (lowest rowid).

    This is safe to run at any time — rows without a URL are left untouched.
    Returns the number of rows deleted.
    """
    if not db_path.exists():
        logging.warning("dedup_database: DB not found at %s", db_path)
        return 0

    conn = sqlite3.connect(str(db_path))
    before = conn.execute("SELECT COUNT(*) FROM items;").fetchone()[0]
    # Only dedup rows where url is non-null
    conn.execute("""
        DELETE FROM items
        WHERE url IS NOT NULL
          AND rowid NOT IN (
              SELECT MIN(rowid) FROM items WHERE url IS NOT NULL GROUP BY url
          );
    """)
    conn.commit()
    after = conn.execute("SELECT COUNT(*) FROM items;").fetchone()[0]
    conn.close()
    deleted = before - after
    logging.info("dedup_database: removed %d duplicate URL rows (%d → %d)", deleted, before, after)
    return deleted


def _insert_example_row(module_name: str, extra_fields: list[dict]) -> None:
    """Insert one clearly-synthetic row so the live-query tool returns data immediately."""
    fields = _all_fields(extra_fields)
    row: dict = {}
    for f in fields:
        name  = f["name"]
        ftype = f["type"]
        nl    = name.lower()
        if f.get("primary"):
            row[name] = "__SYNTHETIC_EXAMPLE__"
        elif ftype == "INTEGER":
            row[name] = 0
        elif ftype == "REAL":
            row[name] = 0.0
        elif "image" in nl and "url" in nl:
            row[name] = "https://example.com/image/synthetic.jpg"
        elif "url" in nl:
            row[name] = "https://example.com/synthetic"
        elif "country" in nl:
            row[name] = "United States"
        elif any(k in nl for k in ("state", "province", "region")):
            row[name] = "EX"
        elif "city" in nl:
            row[name] = "Example City"
        elif f.get("location"):
            row[name] = "Example"
        elif name == "crawled_at":
            row[name] = "2000-01-01 00:00:00"
        else:
            row[name] = f"[SYNTHETIC — {name} — for testing only]"

    cols         = ", ".join(row.keys())
    placeholders = ", ".join(["?"] * len(row))
    db_path      = SRC_DIR / module_name / "database.sqlite"
    conn         = sqlite3.connect(str(db_path))
    conn.execute(f"INSERT OR IGNORE INTO items ({cols}) VALUES ({placeholders});", list(row.values()))
    conn.commit()
    conn.close()


# ── Orchestrator ───────────────────────────────────────────────────────────────

def main(
    source_name:  str,
    extra_fields: list[dict] | None = None,
    short_desc:   str = "",
    long_desc:    str = "",
) -> None:
    load_dotenv()
    _setup_logging()

    extra_fields       = extra_fields or []
    resources_path     = ROOT_DIR / "config" / "resources.json"
    module_name        = _derive_module_name(source_name)
    class_name         = _derive_class_name(module_name)
    jsonify_class_name = _derive_jsonify_class_name(module_name)

    _crawler_dir(module_name).mkdir(parents=True, exist_ok=True)

    # ── STEP 1: __init__.py ───────────────────────────────────────────────────
    print("\n[STEP 1] Writing __init__.py ...")
    _write_init(module_name)
    print("  OK")

    # ── STEP 2: crawler.py ────────────────────────────────────────────────────
    print("\n[STEP 2] Writing crawler.py ...")
    _write_crawler_stub(module_name, class_name)
    print("  OK")

    # ── STEP 3: schema.py ─────────────────────────────────────────────────────
    print("\n[STEP 3] Writing schema.py ...")
    _write_schema_stub(module_name, extra_fields)
    print("  OK")

    # ── STEP 4: jsonify.py ────────────────────────────────────────────────────
    print("\n[STEP 4] Writing jsonify.py ...")
    _write_jsonify_stub(module_name, jsonify_class_name)
    print("  OK")

    # ── STEP 5: demo_data.py ──────────────────────────────────────────────────
    print("\n[STEP 5] Writing demo_data.py ...")
    _write_demo_data_stub(module_name)
    print("  OK")

    # ── STEP 5d: publish.py ───────────────────────────────────────────────────
    print("\n[STEP 5d] Writing publish.py ...")
    _write_publish_stub(module_name, short_desc, long_desc)
    print("  OK")

    # ── STEP 5c: LISTING.md ───────────────────────────────────────────────────
    print("\n[STEP 5c] Writing LISTING.md ...")
    _write_listing(module_name, short_desc, long_desc, extra_fields)
    print("  OK")

    # ── STEP 5b: logo ─────────────────────────────────────────────────────────
    print("\n[STEP 5b] Generating logo ...")
    try:
        from utils.gen_logo import gen_logo
        logo_path = _crawler_dir(module_name) / "logo.png"
        gen_logo(module_name, out_path=logo_path)
        print(f"  OK  → {logo_path}")
    except Exception as exc:
        print(f"  SKIP  (logo generation failed: {exc})")

    # ── STEP 6: HTML template ─────────────────────────────────────────────────
    print("\n[STEP 6] Writing HTML template ...")
    _write_html_template(module_name, extra_fields, long_desc)
    print("  OK")

    # ── STEP 8: index.html card ───────────────────────────────────────────────
    print("\n[STEP 8] Inserting card into index.html ...")
    _insert_index_card(module_name, short_desc)
    print("  OK")

    # ── STEP 9: SQLite database ───────────────────────────────────────────────
    print("\n[STEP 9] Initializing SQLite database ...")
    _init_crawler_db(module_name, extra_fields)
    print("  OK")

    # ── STEP 9b: synthetic example row ────────────────────────────────────────
    print("\n[STEP 9b] Inserting synthetic example row ...")
    _insert_example_row(module_name, extra_fields)
    print("  OK  (row id='__SYNTHETIC_EXAMPLE__' — for testing only)")

    # ── STEP 9c: dedup (no-op on fresh DB, safety net on existing) ────────────
    print("\n[STEP 9c] Deduplicating database (url uniqueness) ...")
    db_path = SRC_DIR / module_name / "database.sqlite"
    removed = dedup_database(db_path)
    print(f"  OK  ({removed} duplicate URL rows removed)")

    # ── STEP 10: resources.json ───────────────────────────────────────────────
    print("\n[STEP 10] Registering collection in resources.json ...")
    _ensure_collection(resources_path, module_name, module_name, f"src/{module_name}/database.sqlite")
    print("  OK")

    print("\nDone.")


def delete_crawler(source_name: str) -> None:
    """Remove everything created by main() for this crawler."""
    import shutil

    load_dotenv()
    _setup_logging()

    module_name    = _derive_module_name(source_name)
    crawler_dir    = _crawler_dir(module_name)
    template_path  = TEMPLATES_DIR / f"{module_name}.html"
    resources_path = ROOT_DIR / "config" / "resources.json"

    # src/{module_name}/ — covers __init__, crawler, schema, jsonify,
    #                       demo_data, database.sqlite
    if crawler_dir.exists():
        shutil.rmtree(crawler_dir)
        print(f"  Deleted: {crawler_dir}")
    else:
        print(f"  Not found: {crawler_dir}")

    # templates/{module_name}.html
    if template_path.exists():
        template_path.unlink()
        print(f"  Deleted: {template_path}")
    else:
        print(f"  Not found: {template_path}")

    # config/resources.json entry
    data = _load_json(resources_path)
    collections = data.get("collections", {})
    if module_name in collections:
        del collections[module_name]
        data["collections"] = collections
        _write_json(resources_path, data)
        print(f"  Removed '{module_name}' from resources.json")
    else:
        print(f"  '{module_name}' not in resources.json")

    # templates/index.html card
    if _remove_index_card(module_name):
        print(f"  Removed card for '{module_name}' from index.html")
    else:
        print(f"  No card for '{module_name}' in index.html")

    print("\nClean.")


if __name__ == "__main__":
    # ── CONFIG ───────────────────────────────────────────────────────────────────
    SOURCE_NAME = "craigslist_cars2"
    SHORT_DESC  = "Used vehicle listings across US & Canadian cities."
    LONG_DESC   = """\
Used vehicle listings scraped across US and Canadian cities. Each record includes \
pricing, mileage, year, URL, and full geo-location data tagged at crawl time."""
    # Only id and crawled_at are always included automatically.
    # Every other field you want must be listed here — including title, city,
    # state, country if relevant (e.g. classified ads). For something like stock
    # tickers those location fields wouldn't apply, so don't add them.
    # Valid keys: name, type ("TEXT"|"INTEGER"|"REAL"), indexed, unique,
    #             location, primary, default_sql, description
    EXTRA_FIELDS: list[dict] = [
        {"name": "title",     "type": "TEXT",                                       "description": "Listing headline"},
        {"name": "price",     "type": "INTEGER", "indexed": True,                   "description": "Asking price in USD"},
        {"name": "mileage",   "type": "INTEGER",                                    "description": "Odometer reading in miles"},
        {"name": "year",      "type": "INTEGER", "indexed": True,                   "description": "Model year"},
        {"name": "url",       "type": "TEXT",    "unique": True,  "indexed": True,  "description": "Direct link to listing"},
        {"name": "image_url", "type": "TEXT",                                       "description": "Primary listing image"},
        {"name": "city",      "type": "TEXT",    "indexed": True, "location": True, "description": "City where listing was crawled"},
        {"name": "state",     "type": "TEXT",    "indexed": True, "location": True, "description": "State or province"},
        {"name": "country",   "type": "TEXT",    "indexed": True, "location": True, "description": "Country of origin"},
    ]
    # ─────────────────────────────────────────────────────────────────────────────

    main(SOURCE_NAME, EXTRA_FIELDS, SHORT_DESC, LONG_DESC)
    # delete_crawler(SOURCE_NAME)
