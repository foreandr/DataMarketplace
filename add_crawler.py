from __future__ import annotations

import json
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


def _derive_module_name(source_name: str) -> str:
    return source_name.replace("-", "_").lower()


def _derive_class_name(source_name: str) -> str:
    parts = source_name.replace("-", "_").split("_")
    return "".join(p.capitalize() for p in parts) + "Crawler"


def _crawler_file_path(module_name: str) -> Path:
    return SRC_DIR / "crawlers" / f"{module_name}.py"


def _jsonify_file_path(module_name: str) -> Path:
    return SRC_DIR / "jsonify_logic" / f"{module_name}.py"


def _demo_data_file_path(module_name: str) -> Path:
    return SRC_DIR / "demo_data" / f"{module_name}.py"


def _crawler_dotted_path(module_name: str, class_name: str) -> str:
    return f"crawlers.{module_name}.{class_name}"


def _jsonify_class_name(source_name: str) -> str:
    parts = source_name.replace("-", "_").split("_")
    return "".join(p.capitalize() for p in parts) + "Jsonify"


def _load_sources(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_sources(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _add_source_entry(sources_path: Path, entry: dict) -> None:
    data = _load_sources(sources_path)
    sources = data.get("sources", [])
    if any(s.get("name") == entry["name"] for s in sources):
        raise ValueError(f"Source already exists: {entry['name']}")
    sources.append(entry)
    data["sources"] = sources
    _write_sources(sources_path, data)


def _write_crawler_stub(source_name: str, module_name: str, class_name: str) -> None:
    path = _crawler_file_path(module_name)
    if path.exists():
        raise FileExistsError(f"Crawler file already exists: {path}")
    path.write_text(
        (
            '"""Crawler stub."""\n'
            "from __future__ import annotations\n\n"
            "from typing import Iterable\n\n"
            "try:\n"
            "    from crawlers.base import BaseCrawler, CrawlItem\n"
            "except ModuleNotFoundError:  # allow running directly from this folder\n"
            "    import sys\n"
            "    from pathlib import Path\n\n"
            "    ROOT_DIR = Path(__file__).resolve().parents[2]\n"
            "    sys.path.insert(0, str(ROOT_DIR / \"src\"))\n"
            "    from crawlers.base import BaseCrawler, CrawlItem\n\n\n"
            f"class {class_name}(BaseCrawler):\n"
            "    def run(self) -> Iterable[CrawlItem]:\n"
            "        # Base template: each source owns its crawler file.\n"
            "        return self.stub_run()\n"
            "\n\n"
            "if __name__ == \"__main__\":\n"
            f"    {class_name}(name=\"{source_name}\").run()\n"
        ),
        encoding="utf-8",
    )


def _write_jsonify_stub(source_name: str, module_name: str, class_name: str) -> None:
    path = _jsonify_file_path(module_name)
    if path.exists():
        raise FileExistsError(f"Jsonify file already exists: {path}")
    path.write_text(
        (
            f'"""Jsonify stub for {source_name}.\"\"\"\n'
            "from __future__ import annotations\n\n"
            "from typing import Any, List\n\n"
            "from jsonify_logic.base import Jsonify\n\n\n"
            f"class {class_name}(Jsonify):\n"
            "    def to_json(self, data: Any) -> List[dict]:\n"
            "        # TODO: convert list-of-lists into list of dicts.\n"
            "        return data if isinstance(data, list) else []\n"
        ),
        encoding="utf-8",
    )


def _write_demo_data_stub(source_name: str, module_name: str) -> None:
    path = _demo_data_file_path(module_name)
    if path.exists():
        raise FileExistsError(f"Demo data file already exists: {path}")
    path.write_text(
        (
            f'"""Demo data for {source_name}.\"\"\"\n\n'
            "DEMO_DATA = [\n"
            "    # [\"example\", 123],\n"
            "]\n"
        ),
        encoding="utf-8",
    )


def main(source_name: str, enabled: bool) -> None:
    load_dotenv()
    app_cfg = load_json_config("app.json")
    _setup_logging(app_cfg["app"]["log_level"])

    sources_path = ROOT_DIR / "config" / "sources.json"
    module_name = _derive_module_name(source_name)
    class_name = _derive_class_name(source_name)
    jsonify_class_name = _jsonify_class_name(source_name)

    _write_crawler_stub(source_name, module_name, class_name)
    _write_jsonify_stub(source_name, module_name, jsonify_class_name)
    _write_demo_data_stub(source_name, module_name)
    entry = {
        "name": source_name,
        "enabled": enabled,
        "crawler": _crawler_dotted_path(module_name, class_name),
        "notes": "Auto-generated by add_crawler.py",
    }
    _add_source_entry(sources_path, entry)

    db_path = get_data_path(app_cfg["database"]["path"])
    conn = connect(db_path)
    init_db(conn)
    ensure_source_table(conn, source_name)
    conn.close()

    logging.info("Added crawler: %s", source_name)
    logging.info("Module: %s | Class: %s", module_name, class_name)
    logging.info("Updated: %s", sources_path)


if __name__ == "__main__":
    # =========================
    # CONFIG (edit these)
    # =========================
    SOURCE_NAME = "imdb_movies"
    ENABLED = True
    # =========================

    main(SOURCE_NAME, ENABLED)

    # =========================
    SOURCE_NAME = "craigslist_cars"
    ENABLED = True
    # =========================

    main(SOURCE_NAME, ENABLED)

    # =========================
    SOURCE_NAME = "craigslist_realestate"
    ENABLED = True
    # =========================

    main(SOURCE_NAME, ENABLED)
