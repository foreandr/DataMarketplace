from __future__ import annotations

import json
import logging
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from utils.config import load_json_config


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
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


def _add_source_entry(sources_path: Path, entry: dict) -> None:
    data = _load_json(sources_path)
    sources = data.get("sources", [])
    if any(s.get("name") == entry["name"] for s in sources):
        raise ValueError(f"Source already exists: {entry['name']}")
    sources.append(entry)
    data["sources"] = sources
    _write_json(sources_path, data)


def _ensure_collection(resources_path: Path, collection: str, schema: str, db_path: str) -> None:
    data = _load_json(resources_path)
    collections = data.get("collections", {})
    if collection not in collections:
        collections[collection] = {"db_path": db_path, "schema": schema}
        data["collections"] = collections
        _write_json(resources_path, data)


def _ensure_api_entry(app_path: Path, entry: dict) -> None:
    data = _load_json(app_path)
    apis = data.get("apis", [])
    if not any(a.get("slug") == entry.get("slug") for a in apis):
        apis.append(entry)
        data["apis"] = apis
        _write_json(app_path, data)


def _write_init(module_name: str) -> None:
    path = _crawler_dir(module_name) / "__init__.py"
    if not path.exists():
        path.write_text("", encoding="utf-8")


def _write_crawler_stub(module_name: str, class_name: str) -> None:
    path = _crawler_dir(module_name) / "crawler.py"
    if path.exists():
        raise FileExistsError(f"Already exists: {path}")
    path.write_text(
        f'"""Crawler stub for {module_name}."""\n'
        "from __future__ import annotations\n\n"
        "from typing import Iterable\n\n"
        "try:\n"
        "    from crawlers.base import BaseCrawler, CrawlItem\n"
        "except ModuleNotFoundError:\n"
        "    import sys\n"
        "    from pathlib import Path\n"
        "    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / \"src\"))\n"
        "    from crawlers.base import BaseCrawler, CrawlItem\n\n\n"
        f"class {class_name}(BaseCrawler):\n"
        "    def run(self) -> Iterable[CrawlItem]:\n"
        "        return self.stub_run()\n\n\n"
        'if __name__ == "__main__":\n'
        f'    {class_name}(name="{module_name}").run()\n',
        encoding="utf-8",
    )


def _write_schema_stub(module_name: str) -> None:
    path = _crawler_dir(module_name) / "schema.py"
    if path.exists():
        raise FileExistsError(f"Already exists: {path}")
    path.write_text(
        f'"""Schema stub for {module_name}."""\n'
        "from __future__ import annotations\n\n"
        "from schemas.base import Field, Schema\n\n\n"
        "SCHEMA = Schema(\n"
        '    table="items",\n'
        "    fields=[\n"
        '        Field("id", "TEXT", primary=True),\n'
        '        Field("crawled_at", "TEXT", indexed=True, default_sql="CURRENT_TIMESTAMP"),\n'
        "    ],\n"
        ")\n",
        encoding="utf-8",
    )


def _write_jsonify_stub(module_name: str, class_name: str) -> None:
    path = _crawler_dir(module_name) / "jsonify.py"
    if path.exists():
        raise FileExistsError(f"Already exists: {path}")
    path.write_text(
        f'"""Jsonify stub for {module_name}."""\n'
        "from __future__ import annotations\n\n"
        "from typing import Any, List\n\n"
        "from jsonify_logic.base import Jsonify\n\n\n"
        f"class {class_name}(Jsonify):\n"
        "    def to_json(self, data: Any) -> List[dict]:\n"
        "        # TODO: convert scraped rows into dicts\n"
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


def _init_crawler_db(module_name: str) -> None:
    path = SRC_DIR / module_name / "database.sqlite"
    conn = sqlite3.connect(str(path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS items ("
        "id TEXT PRIMARY KEY, "
        "crawled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);"
    )
    conn.commit()
    conn.close()


def main(source_name: str, enabled: bool = True) -> None:
    load_dotenv()
    app_cfg = load_json_config("app.json")
    _setup_logging(app_cfg["app"]["log_level"])

    sources_path = ROOT_DIR / "config" / "sources.json"
    resources_path = ROOT_DIR / "config" / "resources.json"
    app_path = ROOT_DIR / "config" / "app.json"
    module_name = _derive_module_name(source_name)
    class_name = _derive_class_name(module_name)
    jsonify_class_name = _derive_jsonify_class_name(module_name)

    _crawler_dir(module_name).mkdir(parents=True, exist_ok=True)
    _write_init(module_name)
    _write_crawler_stub(module_name, class_name)
    _write_schema_stub(module_name)
    _write_jsonify_stub(module_name, jsonify_class_name)
    _write_demo_data_stub(module_name)
    _write_publish_stub(module_name)
    _init_crawler_db(module_name)

    _add_source_entry(sources_path, {
        "name": module_name,
        "enabled": enabled,
        "crawler": f"{module_name}.crawler.{class_name}",
        "notes": "Auto-generated by add_crawler.py",
    })
    _ensure_collection(resources_path, module_name, module_name,
                       f"src/{module_name}/database.sqlite")
    _ensure_api_entry(app_path, {
        "name": f"{module_name.lstrip('_').replace('_', ' ').title()} API",
        "slug": module_name,
        "collection": module_name,
        "schema": module_name,
        "version": "1.0.0",
        "description": f"API for {module_name.lstrip('_').replace('_', ' ')}.",
        "tags": [module_name],
        "visibility": "PUBLIC",
    })

    logging.info("Added crawler: %s -> src/%s/", module_name, module_name)


if __name__ == "__main__":
    # =========================
    # CONFIG (edit these)
    # =========================
    SOURCE_NAME = "my_new_crawler"   # will become _my_new_crawler
    ENABLED = True
    # =========================

    main(SOURCE_NAME, ENABLED)
