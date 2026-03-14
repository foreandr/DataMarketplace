from __future__ import annotations

import json
import logging
import shutil
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
    name = source_name.replace("-", "_").lower()
    return name if name.startswith("_") else f"_{name}"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _remove_source_entry(sources_path: Path, module_name: str) -> bool:
    data = _load_json(sources_path)
    sources = data.get("sources", [])
    new_sources = [s for s in sources if s.get("name") != module_name]
    if len(new_sources) == len(sources):
        return False
    data["sources"] = new_sources
    _write_json(sources_path, data)
    return True


def _remove_collection(resources_path: Path, module_name: str) -> bool:
    data = _load_json(resources_path)
    collections = data.get("collections", {})
    if module_name not in collections:
        return False
    collections.pop(module_name)
    data["collections"] = collections
    _write_json(resources_path, data)
    return True


def _remove_api_entry(app_path: Path, module_name: str) -> bool:
    data = _load_json(app_path)
    apis = data.get("apis", [])
    new_apis = [a for a in apis if a.get("slug") != module_name]
    if len(new_apis) == len(apis):
        return False
    data["apis"] = new_apis
    _write_json(app_path, data)
    return True


def _delete_crawler_folder(module_name: str) -> bool:
    folder = SRC_DIR / module_name
    if not folder.exists():
        return False
    shutil.rmtree(folder)
    return True


def main(source_name: str) -> None:
    load_dotenv()
    app_cfg = load_json_config("app.json")
    _setup_logging(app_cfg["app"]["log_level"])

    sources_path = ROOT_DIR / "config" / "sources.json"
    resources_path = ROOT_DIR / "config" / "resources.json"
    app_path = ROOT_DIR / "config" / "app.json"
    module_name = _derive_module_name(source_name)

    removed = _remove_source_entry(sources_path, module_name)
    removed_collection = _remove_collection(resources_path, module_name)
    removed_api = _remove_api_entry(app_path, module_name)
    deleted_folder = _delete_crawler_folder(module_name)

    logging.info("Removed source entry: %s", removed)
    logging.info("Removed collection: %s", removed_collection)
    logging.info("Removed API entry: %s", removed_api)
    logging.info("Deleted src/%s/: %s", module_name, deleted_folder)


if __name__ == "__main__":
    # =========================
    # CONFIG (edit these)
    # =========================
    SOURCE_NAME = "_my_crawler_name"
    # =========================

    main(SOURCE_NAME)
