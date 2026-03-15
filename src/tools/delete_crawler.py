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


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
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


def _remove_collection(resources_path: Path, module_name: str) -> bool:
    data = _load_json(resources_path)
    collections = data.get("collections", {})
    if module_name not in collections:
        return False
    collections.pop(module_name)
    data["collections"] = collections
    _write_json(resources_path, data)
    return True


def _delete_crawler_folder(module_name: str) -> bool:
    folder = SRC_DIR / module_name
    if not folder.exists():
        return False
    shutil.rmtree(folder)
    return True


def main(source_name: str) -> None:
    load_dotenv()
    _setup_logging()

    resources_path = ROOT_DIR / "config" / "resources.json"
    module_name = _derive_module_name(source_name)

    removed_collection = _remove_collection(resources_path, module_name)
    deleted_folder = _delete_crawler_folder(module_name)

    logging.info("Removed collection: %s", removed_collection)
    logging.info("Deleted src/%s/: %s", module_name, deleted_folder)


if __name__ == "__main__":
    # =========================
    # CONFIG (edit these)
    # =========================
    SOURCE_NAME = "_my_crawler_name"
    # =========================

    main(SOURCE_NAME)
