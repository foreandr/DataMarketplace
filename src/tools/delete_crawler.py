from __future__ import annotations

import json
import logging
import shutil
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
    # Covers: __init__.py, crawler.py, schema.py, jsonify.py,
    #         demo_data.py, publish.py, database.sqlite
    folder = SRC_DIR / module_name
    if not folder.exists():
        return False
    shutil.rmtree(folder)
    return True


def _delete_html_template(module_name: str) -> bool:
    path = TEMPLATES_DIR / f"{module_name}.html"
    if not path.exists():
        return False
    path.unlink()
    return True


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


def main(source_name: str) -> None:
    load_dotenv()
    _setup_logging()

    resources_path = ROOT_DIR / "config" / "resources.json"
    module_name    = _derive_module_name(source_name)

    removed_collection = _remove_collection(resources_path, module_name)
    deleted_folder     = _delete_crawler_folder(module_name)
    deleted_template   = _delete_html_template(module_name)
    removed_card       = _remove_index_card(module_name)

    logging.info("Removed collection entry:    %s", removed_collection)
    logging.info("Deleted src/%s/:             %s", module_name, deleted_folder)
    logging.info("Deleted templates/%s.html:   %s", module_name, deleted_template)
    logging.info("Removed card from index.html: %s", removed_card)


if __name__ == "__main__":
    # =========================
    # CONFIG (edit these)
    # =========================
    SOURCE_NAME = "_craigslist_cars2"
    # =========================

    main(SOURCE_NAME)
