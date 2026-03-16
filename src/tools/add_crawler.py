from __future__ import annotations

import json
import logging
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"
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
    """Return the full ordered field list: id, title, [extra], city, state, country, crawled_at."""
    base_leading: list[dict] = [
        {"name": "id",    "type": "TEXT", "primary": True,  "description": "Unique listing identifier"},
        {"name": "title", "type": "TEXT",                   "description": "Listing headline"},
    ]
    base_trailing: list[dict] = [
        {"name": "city",       "type": "TEXT", "indexed": True, "location": True, "description": "City where listing was crawled"},
        {"name": "state",      "type": "TEXT", "indexed": True, "location": True, "description": "State or province"},
        {"name": "country",    "type": "TEXT", "indexed": True, "location": True, "description": "Country of origin"},
        {"name": "crawled_at", "type": "TEXT", "indexed": True, "default_sql": "CURRENT_TIMESTAMP", "description": "Timestamp when row was ingested"},
    ]
    return base_leading + list(extra_fields) + base_trailing


def _field_to_python(f: dict) -> str:
    """Return a Field(...) constructor line for schema.py."""
    name = f["name"]
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
    fields = _all_fields(extra_fields)
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
        "            if f.unique: col += \" UNIQUE\"\n"
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
        "        # loc_city    = (location or {}).get('city', '')\n"
        "        # loc_state   = (location or {}).get('state', '')\n"
        "        # loc_country = (location or {}).get('country', '')\n"
        "        return data if isinstance(data, list) else []\n",
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


def _write_publish_stub(module_name: str) -> None:
    path = _crawler_dir(module_name) / "publish.py"
    if path.exists():
        raise FileExistsError(f"Already exists: {path}")
    path.write_text(
        f'"""Publish logic for {module_name}."""\n'
        "from __future__ import annotations\n\n"
        "# TODO: implement publishing to RapidAPI, Zyla, etc.\n",
        encoding="utf-8",
    )


def _schema_table_rows(fields: list[dict]) -> str:
    """Generate HTML <tr> rows for the schema table."""
    rows = []
    for f in fields:
        name = f["name"]
        ftype = f["type"]
        desc = f.get("description", name.replace("_", " ").capitalize())
        tags = []
        if f.get("primary"):
            tags.append('<span class="ftag ftag-pk">PK</span>')
        if f.get("unique"):
            tags.append('<span class="ftag ftag-uniq">unique</span>')
        if f.get("location"):
            tags.append('<span class="ftag ftag-loc">location</span>')
        if f.get("indexed"):
            tags.append('<span class="ftag ftag-idx">indexed</span>')
        inner = "".join(tags)
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


def _write_html_template(module_name: str, extra_fields: list[dict]) -> None:
    """Generate templates/{module_name}.html styled like _craigslist_cars.html."""
    path = TEMPLATES_DIR / f"{module_name}.html"
    if path.exists():
        raise FileExistsError(f"Already exists: {path}")

    fields = _all_fields(extra_fields)
    schema_rows = _schema_table_rows(fields)

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
    L.append(f"    Data scraped by <strong>{module_name}</strong>. Each record includes")
    L.append("    title, geo-location (city, state, country), and a crawl timestamp.")
    L.append("  </p>")
    L.append('  <div class="collection-meta">')
    L.append('    <span class="badge badge-green">● Live</span>')
    L.append('    <span class="badge badge-blue">SQLite</span>')
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
    L.append('      <td><span class="field-type">{"price": {"$gte": 5000}}</span></td>')
    L.append("    </tr>")
    L.append("    <tr>")
    L.append('      <td><span class="field-name">$lte</span></td>')
    L.append('      <td class="field-desc">Less than or equal to</td>')
    L.append('      <td><span class="field-type">{"price": {"$lte": 20000}}</span></td>')
    L.append("    </tr>")
    L.append("    <tr>")
    L.append('      <td><span class="field-name">$gt</span></td>')
    L.append('      <td class="field-desc">Strictly greater than</td>')
    L.append('      <td><span class="field-type">{"year": {"$gt": 2010}}</span></td>')
    L.append("    </tr>")
    L.append("    <tr>")
    L.append('      <td><span class="field-name">$lt</span></td>')
    L.append('      <td class="field-desc">Strictly less than</td>')
    L.append('      <td><span class="field-type">{"mileage": {"$lt": 100000}}</span></td>')
    L.append("    </tr>")
    L.append("    <tr>")
    L.append('      <td><span class="field-name">$eq</span></td>')
    L.append('      <td class="field-desc">Exact match (shorthand: pass the value directly)</td>')
    L.append('      <td><span class="field-type">{"country": "United States"}</span></td>')
    L.append("    </tr>")
    L.append("    <tr>")
    L.append('      <td><span class="field-name">$ne</span></td>')
    L.append('      <td class="field-desc">Not equal to</td>')
    L.append('      <td><span class="field-type">{"country": {"$ne": "Canada"}}</span></td>')
    L.append("    </tr>")
    L.append("    <tr>")
    L.append('      <td><span class="field-name">$like</span></td>')
    L.append('      <td class="field-desc">SQL LIKE pattern match — use % as wildcard</td>')
    L.append('      <td><span class="field-type">{"title": {"$like": "%keyword%"}}</span></td>')
    L.append("    </tr>")
    L.append("    <tr>")
    L.append('      <td><span class="field-name">$in</span></td>')
    L.append('      <td class="field-desc">Value must be in the provided list</td>')
    L.append('      <td><span class="field-type">{"state": {"$in": ["Texas", "California"]}}</span></td>')
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
    # <pre> content must start on same line as the tag — no leading newline inside the block
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
    L.append('        <span class="ckey">"country"</span><span class="cop">:</span>  <span class="cs">"United States"</span>,')
    L.append("    },")
    L.append('    <span class="ckey">"order_by"</span><span class="cop">:</span>    [],')
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


def _init_crawler_db(module_name: str, extra_fields: list[dict]) -> None:
    """Create the SQLite database with the full schema."""
    fields = _all_fields(extra_fields)
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


def main(source_name: str, extra_fields: list[dict] | None = None) -> None:
    load_dotenv()
    _setup_logging()

    extra_fields = extra_fields or []
    resources_path = ROOT_DIR / "config" / "resources.json"
    module_name = _derive_module_name(source_name)
    class_name = _derive_class_name(module_name)
    jsonify_class_name = _derive_jsonify_class_name(module_name)

    _crawler_dir(module_name).mkdir(parents=True, exist_ok=True)
    _write_init(module_name)
    _write_crawler_stub(module_name, class_name)
    _write_schema_stub(module_name, extra_fields)
    _write_jsonify_stub(module_name, jsonify_class_name)
    _write_demo_data_stub(module_name)
    _write_publish_stub(module_name)
    _write_html_template(module_name, extra_fields)
    _init_crawler_db(module_name, extra_fields)

    _ensure_collection(
        resources_path,
        module_name,
        module_name,
        f"src/{module_name}/database.sqlite",
    )

    logging.info("Added crawler: %s -> src/%s/", module_name, module_name)
    logging.info("Generated template: templates/%s.html", module_name)


if __name__ == "__main__":
    # =========================
    # CONFIG (edit these)
    # =========================
    SOURCE_NAME = "my_new_crawler"  # will become _my_new_crawler

    # Add custom fields beyond the base set (id, title, city, state, country, crawled_at).
    # These are inserted between title and the location fields.
    # Valid keys: name (str), type ("TEXT"|"INTEGER"|"REAL"), indexed (bool),
    #             unique (bool), description (str)
    EXTRA_FIELDS: list[dict] = [
        # {"name": "price",    "type": "INTEGER", "indexed": True,  "description": "Asking price in USD"},
        # {"name": "mileage",  "type": "INTEGER",                   "description": "Odometer reading in miles"},
        # {"name": "year",     "type": "INTEGER", "indexed": True,  "description": "Model year"},
        # {"name": "url",      "type": "TEXT",    "unique": True, "indexed": True, "description": "Direct link to listing"},
        # {"name": "image_url","type": "TEXT",                      "description": "Primary listing image"},
    ]
    # =========================

    main(SOURCE_NAME, EXTRA_FIELDS)
